# squeeze_analytics

## SQLite → Databricks (Free Edition) ETL

This repo contains a local SQLite database (`ohlc.sqlite3`) and an ETL script (`etl_sqlite_to_databricks.py`) that loads the SQLite tables into your Databricks Free Edition environment via a Databricks SQL Warehouse.

### What’s in `ohlc.sqlite3`
The SQLite DB contains these tables (row counts from the current file):

| table | rows | notes |
|---|---:|---|
| `ohlc` | 57,368 | OHLC candles: exchange/symbol/interval + open/close times + OHLCV |
| `alerts` | 17,031 | alert records; includes JSON fields stored as TEXT |
| `trade_plans` | 17,031 | trading plans; includes JSON fields stored as TEXT |
| `market_cap_cache` | 237 | cached market cap responses |
| `snapshot_cache` | 2 | cached market snapshots |
| `analysis_runs` | 0 | empty in current file |
| `backtest_results` | 0 | empty in current file |
| `backtest_trades` | 0 | empty in current file |

### What the ETL script creates in Databricks
`etl_sqlite_to_databricks.py` will:

1. Discover a SQL Warehouse `http_path` via the Databricks REST API (**or** use `DBX_HTTP_PATH` if you set it).
2. Create a **catalog** + **schema** (database) if possible.
   - If Unity Catalog is **not enabled** (common in Free Edition), `CREATE CATALOG` will fail and the script automatically **falls back** to using only a schema in the default metastore.
3. Create Delta tables matching the SQLite columns.
   - SQLite type mapping:
     - `INTEGER` → `BIGINT`
     - `REAL/FLOAT/DOUBLE` → `DOUBLE`
     - `TEXT` → `STRING`
     - JSON columns remain `STRING` (you can parse them later in Spark/SQL).
4. Load data using batched `INSERT` statements.

### Prerequisites (local machine)
Install dependencies:

```bash
pip install databricks-sql-connector requests
```

### Configure credentials (PowerShell)
**Do not hard-code or commit your token.** Use environment variables.

```powershell
$env:DATABRICKS_HOST = "dbc-883f179f-7886.cloud.databricks.com"
$env:DATABRICKS_TOKEN = "<YOUR_PAT>"
```

### Recommended: Dry run first
This prints the planned DDL and row counts (no Databricks connection required):

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --dry-run
```

### Run the load (create schema/tables + load rows)

#### Option A: Truncate + reload (replace table contents)
Load all tables into the `squeeze` schema, replacing data each run:

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --truncate
```

#### Option B: Merge/upsert (idempotent)
Use `--merge` to upsert into Delta tables using `MERGE INTO`.

- By default, the script uses the SQLite **PRIMARY KEY** columns as the merge key.
- If a table has no PK, you must provide `--merge-keys`.

Example (merge all tables):

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --merge
```

Override merge keys for one or more tables (format: `table=col1,col2;table2=colA`):

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --merge --merge-keys "snapshot_cache=exchange,ts"
```

Notes:
- `--merge` loads each SQLite table into a staging table named `__stg_<table>` and then merges into the target.
- When `--merge` is used, `--truncate` is ignored.

### Optional: Specify catalog and/or warehouse http_path
Attempt to use a catalog (falls back automatically if UC isn’t enabled):

```powershell
$env:DBX_CATALOG = "workspace"
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --truncate
```

Skip warehouse discovery by setting `DBX_HTTP_PATH`:

```powershell
$env:DBX_HTTP_PATH = "/sql/1.0/warehouses/<warehouse-id>"
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --truncate
```

### Optional: Load only specific tables

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --tables ohlc,alerts,market_cap_cache --truncate
```

### Notes / limitations
- The current load strategy uses batched `INSERT` operations. This is fine for the current dataset size (tens of thousands of rows), but for millions of rows you’ll likely want a faster staged approach (e.g., write Parquet, upload to DBFS/Volumes, `COPY INTO`).
- Delta tables can occasionally throw transient concurrency errors (e.g., `[DELTA_METADATA_CHANGED]`) if another process updates table metadata during a load. The script retries these automatically.
- If you run without `--truncate`, the script **appends** to existing tables.
