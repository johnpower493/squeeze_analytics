"""Databricks / PySpark pipeline: trade_plans -> backtest_trades + backtest_results.

This module is intended to be run inside a Databricks notebook (or a Databricks job)
where `spark` is available.

Assumptions
- Bronze Delta tables exist (loaded by etl_sqlite_to_databricks.py) in a schema, e.g. `squeeze`:
    - ohlc
    - alerts
    - trade_plans
    - backtest_trades (may be empty)
    - backtest_results (may be empty)

- OHLC `open_time`/`close_time` are epoch milliseconds.
- trade_plans `ts` is epoch milliseconds (plan timestamp).
- alerts `source_tf` is the timeframe string compatible with ohlc.interval (e.g., '15m', '4h').

Backtest model (initial, conservative)
- Entry fill:
  - default: limit-style entry using trade_plans.entry_price
  - entry is considered filled on the FIRST candle where low <= entry_price <= high
    (for both BUY/SELL).
  - If entry never fills within the lookahead window, the plan is skipped.

- Resolution:
  - Stop and TP are checked on each candle AFTER the entry fill candle (including the entry
    candle by default; configurable).
  - For BUY: stop hit if low <= stop_loss; TP hit if high >= tp1
  - For SELL: stop hit if high >= stop_loss; TP hit if low <= tp1

- Intrabar ambiguity:
  - If stop and TP are both hit in the same candle, `intrabar_priority` controls which wins.
    Default is 'stop_first' (conservative).

- Profit-taking:
  - This initial version resolves at TP1 only (tp2/tp3 are ignored for resolution, but are
    carried through for later analysis).

Outputs
- backtest_trades: one row per trade plan that fills + resolves
- backtest_results: aggregated metrics per (exchange, symbol, source_tf, window_days, strategy_version)

You can extend this to multi-take-profit ladders, partials, trailing stops, fees, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F


IntrabarPriority = Literal["stop_first", "tp_first"]


@dataclass(frozen=True)
class BacktestConfig:
    schema: str
    # Name of the strategy (written to backtest tables)
    strategy_version: str = "v1_entry_price_tp1"
    # Max forward window to search for entry fill + resolution
    window_days: int = 30
    # If true, include the entry candle when checking stop/TP hits
    include_entry_candle_in_resolution: bool = True
    intrabar_priority: IntrabarPriority = "stop_first"
    # Optional filters
    exchange: Optional[str] = None
    symbol: Optional[str] = None


def _tbl(cfg: BacktestConfig, name: str) -> str:
    return f"{cfg.schema}.{name}"


def build_silver_views(spark: SparkSession, cfg: BacktestConfig) -> dict[str, DataFrame]:
    """Create typed DataFrames (not persisted) to use for backtesting."""

    ohlc = spark.table(_tbl(cfg, "ohlc")).select(
        "exchange",
        "symbol",
        F.col("interval").alias("source_tf"),
        F.col("open_time").cast("bigint").alias("open_time_ms"),
        F.col("close_time").cast("bigint").alias("close_time_ms"),
        F.col("open").cast("double").alias("open"),
        F.col("high").cast("double").alias("high"),
        F.col("low").cast("double").alias("low"),
        F.col("close").cast("double").alias("close"),
        F.col("volume").cast("double").alias("volume"),
    ).withColumn("open_ts", (F.col("open_time_ms") / 1000).cast("timestamp"))

    alerts = spark.table(_tbl(cfg, "alerts")).select(
        F.col("id").cast("bigint").alias("alert_id"),
        F.col("exchange").alias("alert_exchange"),
        F.col("symbol").alias("alert_symbol"),
        F.col("source_tf").alias("alert_source_tf"),
        F.col("created_ts").cast("bigint").alias("alert_created_ms"),
    )

    plans = spark.table(_tbl(cfg, "trade_plans")).select(
        F.col("id").cast("bigint").alias("plan_id"),
        F.col("alert_id").cast("bigint").alias("alert_id"),
        F.col("ts").cast("bigint").alias("plan_ts_ms"),
        F.col("exchange"),
        F.col("symbol"),
        F.upper(F.col("side")).alias("side"),
        F.col("entry_type"),
        F.col("entry_price").cast("double").alias("entry_price"),
        F.col("stop_loss").cast("double").alias("stop_loss"),
        F.col("tp1").cast("double").alias("tp1"),
        F.col("tp2").cast("double").alias("tp2"),
        F.col("tp3").cast("double").alias("tp3"),
        F.col("atr").cast("double").alias("atr"),
        F.col("atr_mult").cast("double").alias("atr_mult"),
        F.col("swing_ref"),
        F.col("risk_per_unit").cast("double").alias("risk_per_unit"),
        F.col("rr_tp1").cast("double").alias("rr_tp1"),
        F.col("rr_tp2").cast("double").alias("rr_tp2"),
        F.col("rr_tp3").cast("double").alias("rr_tp3"),
        F.col("plan_json").alias("plan_json"),
    )

    # Attach timeframe from alert when available; otherwise default to '15m'.
    plans = (
        plans.join(alerts, on="alert_id", how="left")
        .withColumn(
            "source_tf",
            F.coalesce(F.col("alert_source_tf"), F.lit("15m")),
        )
        .drop("alert_exchange", "alert_symbol", "alert_source_tf", "alert_created_ms")
    )

    # Optional filters
    if cfg.exchange:
        plans = plans.filter(F.col("exchange") == F.lit(cfg.exchange))
    if cfg.symbol:
        plans = plans.filter(F.col("symbol") == F.lit(cfg.symbol))

    return {"ohlc": ohlc, "plans": plans}


def backtest_trade_plans(spark: SparkSession, cfg: BacktestConfig) -> DataFrame:
    """Generate per-plan backtest outcomes as a DataFrame."""

    silver = build_silver_views(spark, cfg)
    ohlc = silver["ohlc"]
    plans = silver["plans"]

    # Window bounds
    window_ms = int(cfg.window_days) * 24 * 60 * 60 * 1000

    # Join to candidate candles within the lookahead.
    # We restrict to matching exchange/symbol/source_tf.
    candidates = (
        plans.join(
            ohlc,
            on=["exchange", "symbol", "source_tf"],
            how="inner",
        )
        .where((F.col("open_time_ms") >= F.col("plan_ts_ms")) & (F.col("open_time_ms") <= F.col("plan_ts_ms") + F.lit(window_ms)))
    )

    # Entry fill condition (limit entry at entry_price)
    candidates = candidates.withColumn(
        "entry_fills",
        (F.col("entry_price").isNotNull())
        & (F.col("low") <= F.col("entry_price"))
        & (F.col("high") >= F.col("entry_price")),
    )

    entry_w = Window.partitionBy("plan_id").orderBy(F.col("open_time_ms").asc())

    filled = (
        candidates.where(F.col("entry_fills"))
        .withColumn("entry_rn", F.row_number().over(entry_w))
        .where(F.col("entry_rn") == 1)
        .select(
            "plan_id",
            "alert_id",
            "exchange",
            "symbol",
            "source_tf",
            "side",
            "entry_type",
            "entry_price",
            "stop_loss",
            "tp1",
            "tp2",
            "tp3",
            "atr",
            "atr_mult",
            "swing_ref",
            "risk_per_unit",
            "rr_tp1",
            "rr_tp2",
            "rr_tp3",
            "plan_ts_ms",
            F.col("open_time_ms").alias("entry_candle_open_ms"),
            F.col("close_time_ms").alias("entry_candle_close_ms"),
        )
    )

    # Add constant metadata
    filled = filled.withColumn("strategy_version", F.lit(cfg.strategy_version)).withColumn("window_days", F.lit(int(cfg.window_days)))

    # Risk definition (absolute distance)
    filled = filled.withColumn("risk_abs", F.abs(F.col("entry_price") - F.col("stop_loss")))

    # Resolve using candles after entry candle (or including entry candle)
    start_ms = F.col("entry_candle_open_ms") if cfg.include_entry_candle_in_resolution else F.col("entry_candle_close_ms")

    future = (
        filled.join(ohlc, on=["exchange", "symbol", "source_tf"], how="inner")
        .where((F.col("open_time_ms") >= start_ms) & (F.col("open_time_ms") <= F.col("entry_candle_open_ms") + F.lit(window_ms)))
    )

    is_buy = F.col("side") == F.lit("BUY")
    is_sell = F.col("side") == F.lit("SELL")

    stop_hit = F.when(is_buy, F.col("low") <= F.col("stop_loss")).when(is_sell, F.col("high") >= F.col("stop_loss")).otherwise(F.lit(False))
    tp_hit = F.when(is_buy, F.col("high") >= F.col("tp1")).when(is_sell, F.col("low") <= F.col("tp1")).otherwise(F.lit(False))

    future = future.withColumn("stop_hit", stop_hit).withColumn("tp_hit", tp_hit)

    # Candle index relative to the first candle considered for resolution.
    # 0 means the first candle in the resolution window.
    bar_w = Window.partitionBy("plan_id").orderBy(F.col("open_time_ms").asc())
    future = future.withColumn("bar_index", (F.row_number().over(bar_w) - F.lit(1)).cast("bigint"))

    # Event selection per candle
    if cfg.intrabar_priority == "stop_first":
        event = F.when(F.col("stop_hit"), F.lit("STOP")).when(F.col("tp_hit"), F.lit("TP1")).otherwise(F.lit(None))
        hit_rank = F.when(F.col("stop_hit") & F.col("tp_hit"), F.lit(0)).otherwise(F.lit(1))
    else:  # tp_first
        event = F.when(F.col("tp_hit"), F.lit("TP1")).when(F.col("stop_hit"), F.lit("STOP")).otherwise(F.lit(None))
        hit_rank = F.when(F.col("stop_hit") & F.col("tp_hit"), F.lit(0)).otherwise(F.lit(1))

    future = future.withColumn("event", event).withColumn("hit_rank", hit_rank)

    event_w = Window.partitionBy("plan_id").orderBy(F.col("open_time_ms").asc(), F.col("hit_rank").asc())
    first_event = (
        future.where(F.col("event").isNotNull())
        .withColumn("event_rn", F.row_number().over(event_w))
        .where(F.col("event_rn") == 1)
        .select("plan_id", F.col("open_time_ms").alias("resolved_candle_open_ms"), "event", "bar_index")
    )

    # MAE/MFE across the whole future window (from entry)
    mae_mfe = (
        future.groupBy("plan_id")
        .agg(
            F.min("low").alias("min_low"),
            F.max("high").alias("max_high"),
            F.count(F.lit(1)).alias("candles_observed"),
        )
        .select("plan_id", "min_low", "max_high", "candles_observed")
    )

    # Join metrics
    out = (
        filled.join(first_event, on="plan_id", how="inner")
        .join(mae_mfe, on="plan_id", how="left")
    )

    # Compute R-multiple and MAE/MFE in R
    # BUY:
    #   mae = (entry - min_low)/risk
    #   mfe = (max_high - entry)/risk
    # SELL:
    #   mae = (max_high - entry)/risk
    #   mfe = (entry - min_low)/risk

    out = out.withColumn(
        "resolved",
        F.lit(True),
    )

    # bar_index is already the number of candles since the start of resolution window.
    out = out.withColumn("bars_to_resolve", F.col("bar_index").cast("bigint"))

    out = out.withColumn(
        "resolved_price",
        F.when(F.col("event") == F.lit("STOP"), F.col("stop_loss")).when(F.col("event") == F.lit("TP1"), F.col("tp1")),
    )

    # Raw pnl in price units
    out = out.withColumn(
        "pnl_price",
        F.when(is_buy, F.col("resolved_price") - F.col("entry_price")).when(is_sell, F.col("entry_price") - F.col("resolved_price")),
    )

    out = out.withColumn("r_multiple", F.col("pnl_price") / F.when(F.col("risk_abs") == 0, F.lit(None)).otherwise(F.col("risk_abs")))

    out = out.withColumn(
        "mae_r",
        F.when(
            is_buy,
            (F.col("entry_price") - F.col("min_low")) / F.when(F.col("risk_abs") == 0, F.lit(None)).otherwise(F.col("risk_abs")),
        ).when(
            is_sell,
            (F.col("max_high") - F.col("entry_price")) / F.when(F.col("risk_abs") == 0, F.lit(None)).otherwise(F.col("risk_abs")),
        ),
    )

    out = out.withColumn(
        "mfe_r",
        F.when(
            is_buy,
            (F.col("max_high") - F.col("entry_price")) / F.when(F.col("risk_abs") == 0, F.lit(None)).otherwise(F.col("risk_abs")),
        ).when(
            is_sell,
            (F.col("entry_price") - F.col("min_low")) / F.when(F.col("risk_abs") == 0, F.lit(None)).otherwise(F.col("risk_abs")),
        ),
    )

    out = out.withColumn("resolved_ts", (F.col("resolved_candle_open_ms") / 1000).cast("timestamp"))

    # Align output columns with SQLite schema of backtest_trades as closely as possible.
    out = out.withColumn(
        "trade_id",
        F.sha2(
            F.concat_ws(
                "::",
                F.col("plan_id").cast("string"),
                F.col("strategy_version"),
                F.col("window_days").cast("string"),
            ),
            256,
        ),
    )

    out = out.select(
        F.col("trade_id").alias("id"),
        "alert_id",
        "window_days",
        "strategy_version",
        (F.col("plan_ts_ms") / 1000).cast("timestamp").alias("created_ts"),
        "exchange",
        "symbol",
        F.lit(None).cast("string").alias("signal"),
        "source_tf",
        F.lit(None).cast("string").alias("setup_grade"),
        F.lit(None).cast("double").alias("setup_score"),
        F.lit(None).cast("boolean").alias("liquidity_top200"),
        F.col("entry_price").alias("entry"),
        F.col("stop_loss").alias("stop"),
        "tp1",
        "tp2",
        "tp3",
        "resolved",
        "r_multiple",
        "mae_r",
        "mfe_r",
        F.col("bars_to_resolve").cast("double").alias("bars_to_resolve"),
        "resolved_ts",
    )

    return out


def write_backtest_tables(spark: SparkSession, cfg: BacktestConfig, mode: str = "append") -> None:
    """Compute backtest trades and write `backtest_trades` + aggregated `backtest_results`.

    mode: 'append' or 'overwrite'
    """

    trades = backtest_trade_plans(spark, cfg)

    # Write trades
    trades.write.format("delta").mode(mode).saveAsTable(_tbl(cfg, "backtest_trades"))

    # Aggregate results
    results = (
        trades.groupBy("exchange", "symbol", "source_tf", "window_days", "strategy_version")
        .agg(
            F.count(F.lit(1)).alias("n_trades"),
            F.avg(F.when(F.col("r_multiple") > 0, F.lit(1.0)).otherwise(F.lit(0.0))).alias("win_rate"),
            F.avg("r_multiple").alias("avg_r"),
            F.avg("mae_r").alias("avg_mae_r"),
            F.avg("mfe_r").alias("avg_mfe_r"),
            F.avg("bars_to_resolve").alias("avg_bars_to_resolve"),
        )
        .withColumn("ts", F.current_timestamp())
        .withColumn("results_json", F.lit(None).cast("string"))
        .select(
            F.sha2(
                F.concat_ws(
                    "::",
                    F.col("exchange"),
                    F.col("symbol"),
                    F.col("source_tf"),
                    F.col("strategy_version"),
                    F.col("window_days").cast("string"),
                ),
                256,
            ).alias("id"),
            "ts",
            "exchange",
            "symbol",
            "source_tf",
            "window_days",
            "strategy_version",
            "n_trades",
            "win_rate",
            "avg_r",
            "avg_mae_r",
            "avg_mfe_r",
            "avg_bars_to_resolve",
            "results_json",
        )
    )

    results.write.format("delta").mode(mode).saveAsTable(_tbl(cfg, "backtest_results"))


__all__ = [
    "BacktestConfig",
    "build_silver_views",
    "backtest_trade_plans",
    "write_backtest_tables",
]
