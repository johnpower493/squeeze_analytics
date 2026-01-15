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
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, TypeVar

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
            print(f"[warn] Transient Delta conflict during {what}; retry {attempt}/{max_attempts} in {sleep_s:.1f}s")
            time.sleep(sleep_s)


# ----------------------------- Databricks helpers -----------------------------

def _host_to_base_url(host: str) -> str:
    host = host.strip()
    host = host.replace("https://", "").replace("http://", "")
    return f"https://{host}"


def discover_warehouse_http_path(*, host: str, token: str) -> str:
    """Return an http_path for a SQL Warehouse.

    Preference order:
    1) RUNNING warehouse
    2) Any warehouse

    Raises if none are available.
    """

    base_url = _host_to_base_url(host)
    url = f"{base_url}/api/2.0/sql/warehouses"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
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
    print(f"[load] {table}: {total:,} rows")

    inserted = 0
    start = time.time()
    for batch in batched(sqlite_rows(sqlite_conn, table), batch_size=batch_size):
        _with_retry(lambda: dbx_cursor.executemany(insert_sql, batch), what=f"executemany {table}")
        inserted += len(batch)
        # log each batch for better visibility on small/medium tables
        rate = inserted / max(time.time() - start, 0.001)
        print(f"  inserted {inserted:,}/{total:,} ({rate:,.0f} rows/s)")


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
    ap.add_argument("--batch-size", type=int, default=2000, help="Rows per INSERT batch")
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

    # Allow --dry-run without Databricks creds
    if not args.dry_run and (not host or not token):
        print(
            "Set env vars DATABRICKS_HOST and DATABRICKS_TOKEN first.\n"
            "Example (PowerShell):\n"
            "  $env:DATABRICKS_HOST=\"dbc-...cloud.databricks.com\"\n"
            "  $env:DATABRICKS_TOKEN=\"dapi...\"\n",
            file=sys.stderr,
        )
        return 2

    http_path = args.http_path
    if not args.dry_run:
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
                    _exec(cur, ddl)

                # Load data
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
