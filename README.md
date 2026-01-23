# squeeze_analytics

## SQLite → Databricks (Free Edition) ETL

## Local analytics tools (quick sanity checks)

This repo also includes small CLI tools for inspecting the SQLite DB and validating trading-plan inputs before running Databricks backtests.

### 1) `analyze_db.py` (schema + samples + basic numeric stats)

```powershell
python analyze_db.py ohlc.sqlite3
python analyze_db.py ohlc.sqlite3 --tables trade_plans --sample-rows 3
python analyze_db.py ohlc.sqlite3 --no-numeric-stats
```

### 2) `comprehensive_analysis.py` (higher-level summaries)

```powershell
# Full report (alerts, ohlc, snapshots if present, market caps, trade plans)
python comprehensive_analysis.py ohlc.sqlite3

# Trade-plan focused (useful when trade_plans drive research/backtests)
python comprehensive_analysis.py ohlc.sqlite3 --trade-plans-only

# Tune section sizes
python comprehensive_analysis.py ohlc.sqlite3 --alerts-limit 50 --ohlc-limit 10 --snapshots-limit 2 --market-cap-limit 10
```

**Note on snapshots:** some DB versions include `snapshot_cache`, others don’t. The script will automatically skip snapshot analysis if the table is missing.

### 3) `detailed_analysis.py` (deep-dive on a single market snapshot)

This analyzes one `snapshot_cache.snapshot_json` payload (when `snapshot_cache` exists):

```powershell
python detailed_analysis.py ohlc.sqlite3 --latest
python detailed_analysis.py ohlc.sqlite3 --exchange binance --latest
```

If `snapshot_cache` is not present in the DB file, the script exits with a clear message.

### 4) `trade_plans_quality.py` (data quality gate for entry_price-based backtests)

Since your swing backtests use **`entry_price` fill logic**, the most important hygiene checks are:
- stop loss is on the correct side of entry
- take-profits are on the correct side of entry
- non-zero risk (`entry_price != stop_loss`)
- sanity checks on RR / ATR multipliers

Run the report:

```powershell
# All rows
python trade_plans_quality.py ohlc.sqlite3

# Last N plans (by ts)
python trade_plans_quality.py ohlc.sqlite3 --limit 5000

# Customize outlier thresholds
python trade_plans_quality.py ohlc.sqlite3 --max-rr 25 --max-atr-mult 20
```


This repo contains a local SQLite database (`ohlc.sqlite3`) and an ETL script (`etl_sqlite_to_databricks.py`) that loads the SQLite tables into your Databricks Free Edition environment via a Databricks SQL Warehouse.

### What’s in `ohlc.sqlite3`
The SQLite DB contains these tables (row counts from the current file; may differ between DB versions):

| table | rows | notes |
|---|---:|---|
| `ohlc` | 57,368 | OHLC candles: exchange/symbol/interval + open/close times + OHLCV |
| `alerts` | 93,123 | alert records; includes JSON fields stored as TEXT |
| `trade_plans` | 93,123 | trading plans; includes JSON fields stored as TEXT |
| `market_cap_cache` | 237 | cached market cap responses |
| `snapshot_cache` | varies | cached market snapshots (not present in all DB versions) |
| `analysis_runs` | 0 | empty in current file |
| `backtest_results` | 0 | empty in current file |
| `backtest_trades` | 0 | empty in current file |

### What the ETL script creates in Databricks

### Databricks backtesting (trade_plans → backtest_trades/results)

This repo includes a Databricks/PySpark module `databricks_trade_plans_backtest.py` that can be run in a Databricks notebook after loading the SQLite tables to Delta.

## Databricks notebooks (recommended workflow)

If you’re running analysis in Databricks, the repo’s “active” notebooks are the `databricks_*.ipynb` notebooks.

Suggested run order:

1. **Load data to Delta**
   - `copy_into_manual_upload_volume.ipynb` (manual upload volume + `COPY INTO`)
   - or `etl_sqlite_to_databricks.py` (automated SQLite → Databricks SQL Warehouse)

2. **EDA + data quality + clean universe**
   - `databricks_eda_sydney_time.ipynb`
   - Produces: `clean_universe` (filtered `(exchange,symbol,interval)` set with gap/dup/invalid-bar metrics)

3. **Alert → outcome analysis (optional but recommended)**
   - `databricks_alert_outcomes.ipynb`
   - Helps quantify which alert types/timeframes are predictive and in which Sydney sessions.

4. **ML dataset + training + scoring (4h, barrier label)**
   - `databricks_ml_barrier_4h_full_features.ipynb`
   - Produces:
     - `ml_barrier_dataset_4h`
     - `ml_barrier_predictions_4h`
   - Key knobs:
     - `TP_ATR`, `SL_ATR`, `W_BARS`
     - `AMBIGUITY_POLICY` (`tp_first` / `sl_first` / `discard_both`)
     - `TRAIN_END`, `VALID_END`

5. **Pattern backtest at scale (optionally ML-filtered)**
   - `databricks_momentum_swing_backtest_starter.ipynb`
   - Produces:
     - `backtest_trades`
     - `backtest_results`
   - Optional ML filter knobs:
     - `USE_ML_FILTER`, `ML_THRESHOLD`, `ML_RUN_ID`

## Archived notebooks

Older/local-only notebooks have been moved to `archive/` to keep the repo root focused on Databricks workflows.

**What it does (v1):**
- Uses `trade_plans.entry_price` as a limit-style entry fill (first candle where `low <= entry_price <= high`)
- Resolves against `tp1` and `stop_loss` (conservative intrabar default: stop wins if both hit same candle)
- Computes `r_multiple`, `mae_r`, `mfe_r`, `bars_to_resolve`
- Writes:
  - `<schema>.backtest_trades`
  - `<schema>.backtest_results`

**Run in a Databricks notebook:**

```python
from databricks_trade_plans_backtest import BacktestConfig, write_backtest_tables

cfg = BacktestConfig(
    schema="squeeze",              # change to your schema
    strategy_version="v1_entry_price_tp1",
    window_days=30,
    intrabar_priority="stop_first",  # or "tp_first"
)

# mode can be "append" or "overwrite"
write_backtest_tables(spark, cfg, mode="append")
```

Tip: start with a filter while validating:

```python
cfg = BacktestConfig(schema="squeeze", window_days=30, exchange="bybit", symbol="BTCUSDT")
write_backtest_tables(spark, cfg, mode="overwrite")
```


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
$env:DATABRICKS_HOST = "<SERVER>"
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

### Fast load option: COPY INTO (recommended for speed)

If `--truncate`/`--merge` loads are too slow, use `--copy-into`.

This mode:
1. Exports each SQLite table to a file locally (for COPY INTO, the script uses **tab-delimited** files **without headers** to safely handle JSON/text columns)
2. Stages/uploads the files to a Databricks filesystem path (DBFS *or* Unity Catalog Volumes)
3. Executes `COPY INTO` into Delta tables via the SQL Warehouse

Notes:
- Empty SQLite tables are skipped automatically in COPY INTO mode.
- Use `--recreate-tables` if you previously created tables with an incompatible schema.

#### Recommended for Unity Catalog Volumes: stage via Databricks CLI

If your workspace restricts DBFS REST (common), use `--stage-method databricks-cli` and point `--stage-dir` at your Volume.

Example (your managed Volume):

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --catalog workspace --schema squeeze `
  --copy-into --truncate --recreate-tables `
  --stage-method databricks-cli `
  --stage-dir "dbfs:/Volumes/workspace/squeeze/squeeze_bronze"
```

#### Default staging (DBFS FileStore)

If DBFS REST is permitted in your workspace, you can stage under FileStore (default):

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --copy-into --truncate
```

Optional: customize staging directory:

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --schema squeeze --copy-into --truncate --stage-dir "dbfs:/FileStore/squeeze_etl"
```

#### Export-only (no Databricks)

To just export CSVs locally:

```powershell
python etl_sqlite_to_databricks.py --db ohlc.sqlite3 --export-only --export-csv-dir .\export_csv
```

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

