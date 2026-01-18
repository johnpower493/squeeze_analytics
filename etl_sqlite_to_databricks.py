"""ETL: load tables from local SQLite (ohlc.sqlite3) into Databricks (Free Edition).

How it works
- Discovers a Databricks SQL Warehouse http_path via REST (or use DBX_HTTP_PATH).
- Connects using databricks-sql-connector.
- Creates catalog + schema (with graceful fallback if Unity Catalog is not enabled).
- Creates tables (Delta) and loads rows in batches using INSERT.

Prereqs (local machine)
  pip install databricks-sql-connector requests

Usage (PowerShell)
  $env:DATABRICKS_HOST = "dbc-...cloud.databricks.com"
  $env:DATABRICKS_TOKEN = "dapi..."   # do NOT commit tokens
  python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze

Optional
  $env:DBX_CATALOG = "workspace"       # attempt UC catalog; fallback to hive_metastore
  $env:DBX_HTTP_PATH = "/sql/1.0/warehouses/..."  # skip discovery
  python etl_sqlite_to_databricks.py --tables ohlc,alerts

Notes
- For large tables, INSERT-based loads can be slow. If your OHLC table is very large, the next step
  would be a staged load via file upload + COPY INTO.
"""

from __future__ import annotations

import argparse
import base64
import csv
import os
import sqlite3
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, TypeVar
import subprocess

import requests

dbsql = None  # imported lazily in main() so this module can be imported without the connector

T = TypeVar("T")


def _is_transient_delta_conflict(exc: BaseException) -> bool:
    msg = str(exc)
    # Common transient Delta concurrency errors
    needles = [
        "DELTA_METADATA_CHANGED",
        "MetadataChangedException",
        "Concurrent",
        "conflicting commit",
    ]
    return any(n.lower() in msg.lower() for n in needles)


def _with_retry(fn: Callable[[], T], *, what: str, max_attempts: int = 8, base_sleep_s: float = 0.5) -> T:
    """Retry wrapper for transient Delta concurrency conflicts."""
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except Exception as e:
            if attempt >= max_attempts or not _is_transient_delta_conflict(e):
                raise
            sleep_s = base_sleep_s * (2 ** (attempt - 1))
            sleep_s = min(sleep_s, 15.0)
            print(
                f"[warn] Transient Delta conflict during {what}; retry {attempt}/{max_attempts} in {sleep_s:.1f}s",
                flush=True,
            )
            time.sleep(sleep_s)


# ----------------------------- Databricks helpers -----------------------------

def _host_to_base_url(host: str) -> str:
    host = host.strip()
    host = host.replace("https://", "").replace("http://", "")
    return f"https://{host}"


def _api_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def discover_warehouse_http_path(*, host: str, token: str) -> str:
    """Return an http_path for a SQL Warehouse.

    Preference order:
    1) RUNNING warehouse
    2) Any warehouse

    Raises if none are available.
    """

    base_url = _host_to_base_url(host)
    url = f"{base_url}/api/2.0/sql/warehouses"
    resp = requests.get(url, headers=_api_headers(token), timeout=30)
    resp.raise_for_status()
    warehouses = resp.json().get("warehouses", [])
    if not warehouses:
        raise RuntimeError(
            "No Databricks SQL warehouses found. Create/start a SQL Warehouse in the Databricks UI "
            "and re-run, or set DBX_HTTP_PATH."
        )

    def score(w: dict[str, Any]) -> tuple[int, int]:
        # Prefer RUNNING and smaller size (if present)
        state = w.get("state")
        running = 0 if state == "RUNNING" else 1
        size = w.get("cluster_size") or ""
        size_score = {"2X-Small": 0, "X-Small": 1, "Small": 2, "Medium": 3, "Large": 4}.get(size, 9)
        return running, size_score

    best = sorted(warehouses, key=score)[0]
    wid = best.get("id")
    if not wid:
        raise RuntimeError("Warehouse missing id; cannot build http_path")
    return f"/sql/1.0/warehouses/{wid}"


@dataclass
class TargetNamespace:
    catalog: Optional[str]
    schema: str

    def full_table(self, table: str) -> str:
        if self.catalog:
            return f"`{self.catalog}`.`{self.schema}`.`{table}`"
        return f"`{self.schema}`.`{table}`"


def _exec(cursor: Any, stmt: str) -> None:
    _with_retry(lambda: cursor.execute(stmt), what="execute")


def ensure_namespace(cursor: Any, ns: TargetNamespace) -> TargetNamespace:
    """Create catalog/schema where possible.

    If UC isn't enabled, CREATE CATALOG will fail; we then fall back to hive_metastore behavior
    by skipping catalog usage and just creating a database (schema) in the default metastore.
    """

    if ns.catalog:
        try:
            _exec(cursor, f"CREATE CATALOG IF NOT EXISTS `{ns.catalog}`")
            _exec(cursor, f"USE CATALOG `{ns.catalog}`")
        except Exception as e:
            print(
                f"[warn] CREATE/USE CATALOG `{ns.catalog}` failed (likely Unity Catalog not enabled). "
                "Falling back to metastore schema only.\n"
                f"       Error: {e}\n",
                file=sys.stderr,
            )
            ns = TargetNamespace(catalog=None, schema=ns.schema)

    _exec(cursor, f"CREATE SCHEMA IF NOT EXISTS `{ns.schema}`")
    _exec(cursor, f"USE `{ns.schema}`")
    return ns


# ----------------------------- DBFS helpers (for COPY INTO loads) --------------

def _raise_for_status_with_context(resp: requests.Response, *, what: str) -> None:
    """Raise a helpful exception for Databricks REST errors.

    Databricks often returns additional JSON in the body; surfacing it makes debugging much faster.
    """

    try:
        resp.raise_for_status()
        return
    except requests.HTTPError as e:
        body = None
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        # Special-case common "why doesn't COPY INTO staging work" scenario.
        if resp.status_code == 403 and "/dbfs/" in resp.request.url:
            raise PermissionError(
                "Databricks returned 403 Forbidden calling the DBFS API. "
                "This usually means your workspace/user/token is not allowed to use DBFS REST endpoints in this environment.\n\n"
                "Fastest workarounds:\n"
                "  1) Re-run WITHOUT --copy-into (uses INSERT batches; likely fine for tens of thousands of rows).\n"
                "  2) If you have UI/CLI access to upload files, upload CSVs to DBFS manually and run COPY INTO in SQL.\n\n"
                "Troubleshooting:\n"
                "  - Ensure DATABRICKS_HOST is your workspace URL (dbc-...cloud.databricks.com) and the token is a workspace PAT.\n"
                "  - Some Free/locked-down workspaces restrict DBFS API; in that case COPY-into staging via DBFS won't work.\n\n"
                f"Request: {resp.request.method} {resp.request.url}\n"
                f"Response body: {body}"
            ) from e

        raise RuntimeError(
            f"Databricks REST call failed during {what}: HTTP {resp.status_code}. "
            f"Request: {resp.request.method} {resp.request.url} Body: {body}"
        ) from e


def dbfs_mkdirs(*, host: str, token: str, path: str) -> None:
    base_url = _host_to_base_url(host)
    url = f"{base_url}/api/2.0/dbfs/mkdirs"
    resp = requests.post(url, headers=_api_headers(token), json={"path": path}, timeout=60)
    _raise_for_status_with_context(resp, what=f"dbfs_mkdirs({path})")


def dbfs_create(*, host: str, token: str, path: str, overwrite: bool) -> int:
    base_url = _host_to_base_url(host)
    url = f"{base_url}/api/2.0/dbfs/create"
    resp = requests.post(
        url,
        headers=_api_headers(token),
        json={"path": path, "overwrite": overwrite},
        timeout=60,
    )
    _raise_for_status_with_context(resp, what=f"dbfs_create({path})")
    return int(resp.json()["handle"])


def dbfs_add_block(*, host: str, token: str, handle: int, data_b64: str) -> None:
    base_url = _host_to_base_url(host)
    url = f"{base_url}/api/2.0/dbfs/add-block"
    resp = requests.post(
        url,
        headers=_api_headers(token),
        json={"handle": handle, "data": data_b64},
        timeout=60,
    )
    _raise_for_status_with_context(resp, what=f"dbfs_add_block(handle={handle})")


def dbfs_close(*, host: str, token: str, handle: int) -> None:
    base_url = _host_to_base_url(host)
    url = f"{base_url}/api/2.0/dbfs/close"
    resp = requests.post(url, headers=_api_headers(token), json={"handle": handle}, timeout=60)
    _raise_for_status_with_context(resp, what=f"dbfs_close(handle={handle})")


def upload_file_to_dbfs(
    *,
    host: str,
    token: str,
    local_path: Path,
    dbfs_path: str,
    overwrite: bool = True,
    chunk_bytes: int = 1024 * 1024,
) -> None:
    """Upload a local file to DBFS using chunked upload API.

    `dbfs_path` must be a DBFS API path like `/FileStore/...` (not `dbfs:/FileStore/...`).
    """

    handle = dbfs_create(host=host, token=token, path=dbfs_path, overwrite=overwrite)
    try:
        with local_path.open("rb") as f:
            while True:
                chunk = f.read(chunk_bytes)
                if not chunk:
                    break
                data_b64 = base64.b64encode(chunk).decode("ascii")
                dbfs_add_block(host=host, token=token, handle=handle, data_b64=data_b64)
    finally:
        dbfs_close(host=host, token=token, handle=handle)


def export_sqlite_table_to_csv(
    *,
    sqlite_conn: sqlite3.Connection,
    table: str,
    out_path: Path,
    include_header: bool = True,
    delimiter: str = ",",
) -> None:
    cols = sqlite_table_info(sqlite_conn, table)
    col_names = [c["name"] for c in cols]

    cur = sqlite_conn.cursor()
    cur.execute(f"SELECT * FROM {table}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(
            f,
            delimiter=delimiter,
            quoting=csv.QUOTE_ALL,
            escapechar="\\",
            lineterminator="\n",
        )
        if include_header:
            writer.writerow(col_names)
        while True:
            rows = cur.fetchmany(10_000)
            if not rows:
                break
            # Normalize None -> empty for CSV
            for r in rows:
                writer.writerow(["" if v is None else v for v in r])


def export_tables_to_csv_dir(
    *,
    sqlite_conn: sqlite3.Connection,
    tables: list[str],
    out_dir: Path,
    include_header: bool = True,
    delimiter: str = ",",
) -> dict[str, Path]:
    """Export selected tables to CSV files under out_dir.

    Returns a mapping: table -> local CSV path.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, Path] = {}
    for t in tables:
        p = out_dir / f"{t}.csv"
        export_sqlite_table_to_csv(
            sqlite_conn=sqlite_conn,
            table=t,
            out_path=p,
            include_header=include_header,
            delimiter=delimiter,
        )
        mapping[t] = p
    return mapping


def _run_databricks_cli(args: list[str]) -> None:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Databricks CLI command failed:\n"
            f"  cmd: {' '.join(args)}\n"
            f"  exit: {proc.returncode}\n"
            f"  stdout: {proc.stdout}\n"
            f"  stderr: {proc.stderr}"
        )


def stage_files_with_databricks_cli(*, cli: str, local_paths: dict[str, Path], stage_dir: str) -> None:
    """Upload local files to a dbfs:/... target using the Databricks CLI.

    This supports dbfs:/Volumes/... as long as your CLI is configured and you have permissions.
    """

    stage_dir = stage_dir.rstrip("/")
    _run_databricks_cli([cli, "fs", "mkdirs", stage_dir])
    for table, local_path in local_paths.items():
        dst = f"{stage_dir}/{table}.csv"
        _run_databricks_cli([cli, "fs", "cp", str(local_path), dst, "--overwrite"])


def stage_files_with_dbfs_rest(*, host: str, token: str, local_paths: dict[str, Path], stage_dir: str) -> None:
    """Upload local CSVs to DBFS using the DBFS REST API.

    Note: DBFS REST requires endpoints like /FileStore/... (not dbfs:/FileStore/...).
    This method generally won't work for UC Volumes.
    """

    stage_dir = stage_dir.rstrip("/")
    mkdirs_path = stage_dir.replace("dbfs:", "")
    dbfs_mkdirs(host=host, token=token, path=mkdirs_path)
    for table, local_path in local_paths.items():
        dbfs_file = f"{stage_dir}/{table}.csv"
        upload_file_to_dbfs(
            host=host,
            token=token,
            local_path=local_path,
            dbfs_path=dbfs_file.replace("dbfs:", ""),
            overwrite=True,
        )


# ----------------------------- SQLite introspection ----------------------------

def sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def sqlite_table_info(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = cur.fetchall()
    return [
        {
            "cid": c[0],
            "name": c[1],
            "type": (c[2] or "").upper(),
            "notnull": bool(c[3]),
            "dflt": c[4],
            # SQLite exposes PK position (0 if not part of PK)
            "pk_pos": int(c[5] or 0),
        }
        for c in cols
    ]


def sqlite_pk_cols(conn: sqlite3.Connection, table: str) -> list[str]:
    cols = sqlite_table_info(conn, table)
    pk = [c for c in cols if c["pk_pos"] > 0]
    pk_sorted = sorted(pk, key=lambda c: c["pk_pos"])
    return [c["name"] for c in pk_sorted]


def sqlite_row_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])


# ----------------------------- Type mapping / DDL ------------------------------

def map_sqlite_type_to_spark(sqlite_type: str) -> str:
    t = (sqlite_type or "").upper()
    if "INT" in t:
        return "BIGINT"
    if any(x in t for x in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE"
    if any(x in t for x in ("CHAR", "CLOB", "TEXT")):
        return "STRING"
    if "BLOB" in t:
        return "BINARY"
    if t in ("", "NUMERIC", "DECIMAL"):
        return "STRING"  # safest default
    return "STRING"


def build_create_table_stmt(*, ns: TargetNamespace, table: str, cols: list[dict[str, Any]]) -> str:
    col_lines: list[str] = []
    for c in cols:
        spark_t = map_sqlite_type_to_spark(c["type"])
        nullable = "NOT NULL" if c["notnull"] else ""
        col_lines.append(f"  `{c['name']}` {spark_t} {nullable}".rstrip())

    # Constraints are informational in Databricks; omit PK/UNIQUE for compatibility.
    col_sql = ",\n".join(col_lines)
    return (
        f"CREATE TABLE IF NOT EXISTS {ns.full_table(table)} (\n{col_sql}\n) "
        "USING DELTA"
    )


# ----------------------------- Loading (INSERT batches) ------------------------

def batched(iterable: Iterable[Any], batch_size: int) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def sqlite_rows(conn: sqlite3.Connection, table: str) -> Iterable[tuple[Any, ...]]:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    while True:
        rows = cur.fetchmany(10_000)
        if not rows:
            break
        for r in rows:
            yield r


def _insert_batches(
    *,
    sqlite_conn: sqlite3.Connection,
    dbx_cursor: Any,
    full_table: str,
    table: str,
    batch_size: int,
) -> None:
    cols = sqlite_table_info(sqlite_conn, table)
    col_names = [c["name"] for c in cols]

    placeholders = ",".join(["?"] * len(col_names))
    insert_sql = (
        f"INSERT INTO {full_table} ({', '.join([f'`{c}`' for c in col_names])}) "
        f"VALUES ({placeholders})"
    )

    total = sqlite_row_count(sqlite_conn, table)
    print(f"[load] {table}: {total:,} rows", flush=True)

    inserted = 0
    start = time.time()
    last_log = start
    batch_i = 0

    for batch in batched(sqlite_rows(sqlite_conn, table), batch_size=batch_size):
        batch_i += 1
        batch_start = time.time()

        # If a single batch blocks for a while, emit a heartbeat before/after the call.
        print(
            f"  batch {batch_i}: sending {len(batch):,} rows...",
            flush=True,
        )

        _with_retry(lambda: dbx_cursor.executemany(insert_sql, batch), what=f"executemany {table}")

        inserted += len(batch)
        now = time.time()
        elapsed = now - start
        rate = inserted / max(elapsed, 0.001)
        pct = (inserted / total * 100.0) if total else 100.0
        batch_s = now - batch_start

        # Always log after each batch so it never looks stuck.
        print(
            f"  batch {batch_i}: done in {batch_s:.1f}s | {inserted:,}/{total:,} ({pct:.1f}%) | avg {rate:,.0f} rows/s | elapsed {elapsed:.1f}s",
            flush=True,
        )
        last_log = now


def load_table_append_or_truncate(
    *,
    sqlite_conn: sqlite3.Connection,
    dbx_cursor: Any,
    ns: TargetNamespace,
    table: str,
    batch_size: int,
    truncate: bool,
) -> None:
    full_table = ns.full_table(table)

    if truncate:
        _exec(dbx_cursor, f"TRUNCATE TABLE {full_table}")

    _insert_batches(
        sqlite_conn=sqlite_conn,
        dbx_cursor=dbx_cursor,
        full_table=full_table,
        table=table,
        batch_size=batch_size,
    )


def load_table_merge(
    *,
    sqlite_conn: sqlite3.Connection,
    dbx_cursor: Any,
    ns: TargetNamespace,
    table: str,
    batch_size: int,
    merge_keys: Optional[list[str]],
) -> None:
    """Upsert into target using Delta MERGE.

    Implementation:
    - Create a staging table with the same schema (`__stg_<table>`)
    - TRUNCATE staging
    - INSERT all SQLite rows into staging
    - MERGE staging into target on merge keys (defaults to SQLite PK columns)

    This makes re-runs idempotent (no duplication) as long as the merge keys are stable.
    """

    full_target = ns.full_table(table)
    stg_name = f"__stg_{table}"
    full_stg = ns.full_table(stg_name)

    cols = sqlite_table_info(sqlite_conn, table)
    col_names = [c["name"] for c in cols]

    keys = merge_keys or sqlite_pk_cols(sqlite_conn, table)
    if not keys:
        raise RuntimeError(
            f"No merge keys provided and no SQLite primary key detected for table '{table}'. "
            "Provide --merge-keys."
        )

    # Ensure staging table exists with identical schema
    ddl_stg = build_create_table_stmt(ns=ns, table=stg_name, cols=cols)
    _exec(dbx_cursor, ddl_stg)
    _exec(dbx_cursor, f"TRUNCATE TABLE {full_stg}")

    # Load into staging
    _insert_batches(
        sqlite_conn=sqlite_conn,
        dbx_cursor=dbx_cursor,
        full_table=full_stg,
        table=table,
        batch_size=batch_size,
    )

    on_clause = " AND ".join([f"t.`{k}` = s.`{k}`" for k in keys])
    set_clause = ", ".join([f"t.`{c}` = s.`{c}`" for c in col_names])
    insert_cols = ", ".join([f"`{c}`" for c in col_names])
    insert_vals = ", ".join([f"s.`{c}`" for c in col_names])

    merge_sql = f"""
MERGE INTO {full_target} t
USING {full_stg} s
ON {on_clause}
WHEN MATCHED THEN UPDATE SET {set_clause}
WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})
""".strip()

    print(f"[merge] {table} on keys: {', '.join(keys)}")
    _exec(dbx_cursor, merge_sql)


# ----------------------------- Main -------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="ohlc.sqlite3", help="Path to SQLite DB (default: ohlc.sqlite3)")
    ap.add_argument("--tables", default=None, help="Comma-separated table list; default = all")
    ap.add_argument("--schema", default=os.getenv("DBX_SCHEMA", "squeeze"), help="Target schema/database")
    ap.add_argument("--catalog", default=os.getenv("DBX_CATALOG"), help="Target catalog (optional)")
    ap.add_argument("--http-path", default=os.getenv("DBX_HTTP_PATH"), help="SQL warehouse http_path")
    ap.add_argument("--batch-size", type=int, default=2000, help="Rows per INSERT batch (INSERT/MERGE modes)")
    ap.add_argument(
        "--databricks-cli",
        default=os.getenv("DATABRICKS_CLI", "databricks"),
        help="Databricks CLI executable to use for staging when --stage-method databricks-cli (default: databricks)",
    )
    ap.add_argument(
        "--copy-into",
        action="store_true",
        help=(
            "Fast path: export tables to CSV, stage the files (DBFS/Volumes), then load using COPY INTO. "
            "If DBFS REST API is forbidden, use --stage-method databricks-cli."
        ),
    )
    ap.add_argument(
        "--stage-dir",
        default=os.getenv("DBX_STAGE_DIR", os.getenv("DBX_DBFS_DIR", "dbfs:/FileStore/squeeze_etl")),
        help=(
            "Base staging directory for COPY INTO files (dbfs:/... or dbfs:/Volumes/... ). "
            "Default: dbfs:/FileStore/squeeze_etl"
        ),
    )
    ap.add_argument(
        "--stage-method",
        choices=["dbfs-rest", "databricks-cli"],
        default=os.getenv("DBX_STAGE_METHOD", "dbfs-rest"),
        help=(
            "How to upload staged files. 'dbfs-rest' uses /api/2.0/dbfs (may be forbidden in some workspaces). "
            "'databricks-cli' shells out to `databricks fs cp` (supports Volumes if your CLI is configured)."
        ),
    )
    ap.add_argument(
        "--export-csv-dir",
        default=os.getenv("DBX_EXPORT_CSV_DIR"),
        help=(
            "If set, export CSVs to this local directory. When used with --export-only, no Databricks connection is made. "
            "If used with --copy-into, files are exported here before upload."
        ),
    )
    ap.add_argument(
        "--export-only",
        action="store_true",
        help="Export selected SQLite tables to CSV files locally and exit (no Databricks).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print planned DDL and row counts; do not connect/load",
    )
    ap.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE tables before load (otherwise append). Ignored if --merge is used.",
    )
    ap.add_argument(
        "--recreate-tables",
        action="store_true",
        help=(
            "Drop and recreate target tables before loading. Useful if tables already exist with an incompatible schema "
            "(e.g., after a previous run/notebook created a different column type)."
        ),
    )
    ap.add_argument(
        "--merge",
        action="store_true",
        help="Upsert into target tables using Delta MERGE (idempotent).",
    )
    ap.add_argument(
        "--merge-keys",
        default=None,
        help=(
            "Optional per-table merge key overrides. Format: table=col1,col2;table2=colA. "
            "If omitted, SQLite PRIMARY KEY columns are used."
        ),
    )

    args = ap.parse_args()

    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")

    # Allow --dry-run and --export-only without Databricks creds
    if (not args.dry_run) and (not args.export_only) and (not host or not token):
        print(
            "Set env vars DATABRICKS_HOST and DATABRICKS_TOKEN first.\n"
            "Example (PowerShell):\n"
            "  $env:DATABRICKS_HOST=\"dbc-...cloud.databricks.com\"\n"
            "  $env:DATABRICKS_TOKEN=\"dapi...\"\n",
            file=sys.stderr,
        )
        return 2

    http_path = args.http_path
    if (not args.dry_run) and (not args.export_only):
        if not http_path:
            print("[dbx] Discovering SQL Warehouse http_path via REST API...")
            http_path = discover_warehouse_http_path(host=host, token=token)  # type: ignore[arg-type]
            print(f"[dbx] Using http_path: {http_path}")

    ns = TargetNamespace(catalog=args.catalog, schema=args.schema)

    sqlite_conn = sqlite3.connect(args.db)
    try:
        tables = sqlite_tables(sqlite_conn)
        if args.tables:
            want = {t.strip() for t in args.tables.split(",") if t.strip()}
            missing = want - set(tables)
            if missing:
                raise SystemExit(f"Unknown tables in --tables: {sorted(missing)}")
            tables = [t for t in tables if t in want]

        print(f"[sqlite] Found {len(tables)} table(s): {', '.join(tables)}")

        # export-only is a local operation; no Databricks creds required
        if args.export_only:
            out_dir = Path(args.export_csv_dir or "export_csv")
            export_tables_to_csv_dir(sqlite_conn=sqlite_conn, tables=tables, out_dir=out_dir, include_header=True, delimiter=",")
            print(f"[export-only] Wrote CSVs to: {out_dir.resolve()}")
            return 0

        if args.dry_run:
            print("[dry-run] Planned DDL (not executed):")
            for t in tables:
                cols = sqlite_table_info(sqlite_conn, t)
                ddl = build_create_table_stmt(ns=ns, table=t, cols=cols)
                print("\n" + ddl)
                print(f"-- rows: {sqlite_row_count(sqlite_conn, t):,}")
            return 0

        global dbsql
        if dbsql is None:
            try:
                from databricks import sql as dbsql  # type: ignore
            except Exception as e:
                raise SystemExit(
                    "Missing dependency databricks-sql-connector. Install with: pip install databricks-sql-connector"
                ) from e

        # Parse merge key overrides
        merge_key_map: dict[str, list[str]] = {}
        if args.merge_keys:
            for part in args.merge_keys.split(";"):
                part = part.strip()
                if not part:
                    continue
                if "=" not in part:
                    raise SystemExit("Invalid --merge-keys format. Expected table=col1,col2;...")
                tname, cols_csv = part.split("=", 1)
                cols = [c.strip() for c in cols_csv.split(",") if c.strip()]
                if not cols:
                    raise SystemExit(f"Invalid --merge-keys entry (no cols): {part}")
                merge_key_map[tname.strip()] = cols

        with dbsql.connect(server_hostname=host, http_path=http_path, access_token=token) as conn:
            with conn.cursor() as cur:
                ns = ensure_namespace(cur, ns)

                # Create tables
                for t in tables:
                    cols = sqlite_table_info(sqlite_conn, t)
                    ddl = build_create_table_stmt(ns=ns, table=t, cols=cols)
                    print(f"[ddl] {t}")
                    if args.recreate_tables:
                        _exec(cur, f"DROP TABLE IF EXISTS {ns.full_table(t)}")
                    _exec(cur, ddl)

                # Load data
                if args.copy_into:
                    run_id = uuid.uuid4().hex[:10]
                    base_stage_dir = args.stage_dir.rstrip("/")
                    stage_dir = f"{base_stage_dir}/{run_id}"
                    print(f"[copy-into] Staging files under: {stage_dir} (method={args.stage_method})", flush=True)

                    # Decide where to export CSVs locally
                    if args.export_csv_dir:
                        export_dir = Path(args.export_csv_dir)
                        export_dir.mkdir(parents=True, exist_ok=True)
                        tmp_cm = None
                    else:
                        tmp_cm = tempfile.TemporaryDirectory(prefix="squeeze_etl_")
                        export_dir = Path(tmp_cm.name)

                    try:
                        # COPY INTO with an explicit column list is incompatible with CSV headers in Databricks SQL.
                        # Export without header and map columns explicitly.
                        #
                        # Also skip empty tables: a headerless export of an empty table produces a 0-byte file,
                        # and COPY INTO fails with NOT_ENOUGH_DATA_COLUMNS.
                        non_empty_tables = [t for t in tables if sqlite_row_count(sqlite_conn, t) > 0]
                        empty_tables = [t for t in tables if t not in non_empty_tables]
                        for t in empty_tables:
                            print(f"[copy-into] Skipping empty table (0 rows): {t}", flush=True)

                        local_paths = export_tables_to_csv_dir(
                            sqlite_conn=sqlite_conn,
                            tables=non_empty_tables,
                            out_dir=export_dir,
                            include_header=False,
                            # Use a delimiter that won't appear frequently inside JSON strings.
                            delimiter="\t",
                        )

                        # Upload/stage
                        staged = False
                        last_err: Optional[Exception] = None

                        if args.stage_method == "dbfs-rest":
                            try:
                                stage_files_with_dbfs_rest(host=host, token=token, local_paths=local_paths, stage_dir=stage_dir)
                                staged = True
                            except PermissionError as e:
                                last_err = e
                                print(
                                    "[warn] DBFS REST staging failed (likely forbidden). Falling back to databricks-cli.\n"
                                    f"       Error: {e}",
                                    file=sys.stderr,
                                )
                                # auto-fallback if CLI staging is available
                                try:
                                    stage_files_with_databricks_cli(cli=args.databricks_cli, local_paths=local_paths, stage_dir=stage_dir)
                                    staged = True
                                except Exception as e2:
                                    last_err = e2
                        else:
                            stage_files_with_databricks_cli(cli=args.databricks_cli, local_paths=local_paths, stage_dir=stage_dir)
                            staged = True

                        if not staged:
                            raise RuntimeError(f"Failed to stage CSVs for COPY INTO. Last error: {last_err}")

                        # COPY INTO
                        for t in tables:
                            if args.truncate and not args.merge:
                                _exec(cur, f"TRUNCATE TABLE {ns.full_table(t)}")

                            if sqlite_row_count(sqlite_conn, t) == 0:
                                continue

                            staged_file = f"{stage_dir}/{t}.csv"

                            # Provide an explicit column list to avoid schema inference/merge issues.
                            col_names = [c["name"] for c in sqlite_table_info(sqlite_conn, t)]
                            col_list = ", ".join([f"`{c}`" for c in col_names])

                            copy_sql = f"""
COPY INTO {ns.full_table(t)} ({col_list})
FROM '{staged_file}'
FILEFORMAT = CSV
FORMAT_OPTIONS (
  'header' = 'false',
  'quote' = '"',
  'escape' = '\\\\',
  'multiLine' = 'true',
  'delimiter' = '\t'
)
COPY_OPTIONS (
  'mergeSchema' = 'false'
)
""".strip()
                            print(f"[copy-into] Loading table {t} from {staged_file}", flush=True)
                            _exec(cur, copy_sql)
                    finally:
                        if tmp_cm is not None:
                            tmp_cm.cleanup()
                else:
                    for t in tables:
                        if args.merge:
                            load_table_merge(
                                sqlite_conn=sqlite_conn,
                                dbx_cursor=cur,
                                ns=ns,
                                table=t,
                                batch_size=args.batch_size,
                                merge_keys=merge_key_map.get(t),
                            )
                        else:
                            load_table_append_or_truncate(
                                sqlite_conn=sqlite_conn,
                                dbx_cursor=cur,
                                ns=ns,
                                table=t,
                                batch_size=args.batch_size,
                                truncate=args.truncate,
                            )

        print("[done] ETL complete")
        return 0
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
