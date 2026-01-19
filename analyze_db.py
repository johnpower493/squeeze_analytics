import argparse
import sqlite3
from typing import Iterable, Sequence

import pandas as pd


def _list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def _iter_tables(all_tables: Sequence[str], tables_arg: str | None) -> Iterable[str]:
    if not tables_arg:
        return all_tables
    wanted = [t.strip() for t in tables_arg.split(",") if t.strip()]
    wanted_set = set(wanted)
    missing = [t for t in wanted if t not in set(all_tables)]
    if missing:
        raise SystemExit(f"Unknown table(s): {missing}. Available: {all_tables}")
    return [t for t in all_tables if t in wanted_set]


def analyze_db(db_path: str, tables: str | None, sample_rows: int, numeric_stats: bool) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=" * 60)
    print("CRYPTO SQLITE DATABASE ANALYSIS")
    print("=" * 60)
    print(f"DB: {db_path}")

    all_tables = _list_tables(conn)
    print(f"\nFound {len(all_tables)} table(s): {all_tables}\n")

    for table in _iter_tables(all_tables, tables):
        print("=" * 60)
        print(f"TABLE: {table}")
        print("=" * 60)

        cur.execute(f"PRAGMA table_info({table})")
        columns = cur.fetchall()
        col_names = [c[1] for c in columns]

        print("\nColumns:")
        for col in columns:
            # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
            pk = " PK" if col[5] else ""
            print(f"  - {col[1]} ({col[2]}){pk}")

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cur.fetchone()[0]
        print(f"\nTotal rows: {row_count:,}")

        if row_count > 0 and sample_rows > 0:
            cur.execute(f"SELECT * FROM {table} LIMIT {int(sample_rows)}")
            sample_data = cur.fetchall()
            print(f"\nSample data (first {min(sample_rows, row_count)} row(s)):")
            df = pd.DataFrame(sample_data, columns=col_names)
            print(df.to_string(index=False))

        if row_count > 0 and numeric_stats:
            # SQLite types are loose; use declared types as a best-effort heuristic.
            numeric_cols = [
                c[1]
                for c in columns
                if any(k in (c[2] or "").upper() for k in ("REAL", "FLOAT", "DOUBLE", "INT"))
            ]
            if numeric_cols:
                print("\nNumeric statistics:")
                for col in numeric_cols:
                    cur.execute(f"SELECT MIN({col}), MAX({col}), AVG({col}) FROM {table}")
                    mn, mx, av = cur.fetchone()
                    print(f"  {col}:")
                    print(f"    Min: {mn}")
                    print(f"    Max: {mx}")
                    print(f"    Avg: {av}")

        print("\n")

    conn.close()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


def main() -> None:
    ap = argparse.ArgumentParser(description="Quick SQLite database inspection for crypto analytics.")
    ap.add_argument("db", nargs="?", default="ohlc.sqlite3", help="Path to SQLite DB (default: ohlc.sqlite3)")
    ap.add_argument(
        "--tables",
        default=None,
        help="Comma-separated list of tables to inspect (default: all tables)",
    )
    ap.add_argument("--sample-rows", type=int, default=5, help="Rows to print per table (default: 5)")
    ap.add_argument(
        "--no-numeric-stats",
        action="store_true",
        help="Disable MIN/MAX/AVG numeric stats",
    )
    args = ap.parse_args()

    analyze_db(args.db, args.tables, args.sample_rows, numeric_stats=not args.no_numeric_stats)


if __name__ == "__main__":
    main()
