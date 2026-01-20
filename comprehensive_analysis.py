import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime

import pandas as pd


def _print_header(title: str, width: int = 80) -> None:
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def _safe_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def _coerce_snapshot_to_rows(obj):
    """Return a list-of-dict rows from snapshot_json.

    Supports:
      - A JSON array payload: [ {...}, {...} ]
      - A JSON object wrapper that contains an embedded array under a common key
        (e.g. {"data": [...]}, {"result": [...]}, etc.).

    Returns None if it can't find a list-like payload.
    """
    if isinstance(obj, list):
        return obj

    if not isinstance(obj, dict):
        return None

    candidate_keys = (
        "data",
        "result",
        "results",
        "items",
        "payload",
        "snapshot",
        "markets",
        "coins",
        "pairs",
        "rows",
        "assets",
    )

    for k in candidate_keys:
        v = obj.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for kk in candidate_keys:
                vv = v.get(kk)
                if isinstance(vv, list):
                    return vv

    for v in obj.values():
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, list):
                    return vv

    return None


def analyze_alerts(conn: sqlite3.Connection, limit: int) -> None:
    _print_header("1. ALERTS TABLE ANALYSIS")

    total = pd.read_sql_query("SELECT COUNT(*) AS n FROM alerts", conn)["n"].iloc[0]
    print(f"\nTotal alerts in database: {total:,}")

    if limit <= 0:
        print("(skipped; --alerts-limit <= 0)")
        return

    alerts_df = pd.read_sql_query(
        "SELECT * FROM alerts ORDER BY created_ts DESC LIMIT ?",
        conn,
        params=(int(limit),),
    )

    if alerts_df.empty:
        print("No alert rows returned.")
        return

    print(f"\nSample data (last {len(alerts_df)} alerts):")
    print("\nAlert signal distribution:")
    print(alerts_df["signal"].value_counts(dropna=False))

    print("\nAlert source timeframe distribution:")
    print(alerts_df["source_tf"].value_counts(dropna=False))

    print("\nTop 10 exchanges by alerts:")
    print(alerts_df["exchange"].value_counts(dropna=False).head(10))

    # Parse metrics_json for a quick overview of available keys
    metrics_data = []
    for metrics in alerts_df.get("metrics_json", pd.Series(dtype=object)).dropna():
        parsed = _safe_json_loads(metrics)
        if isinstance(parsed, dict):
            metrics_data.append(parsed)

    if metrics_data:
        metrics_df = pd.DataFrame(metrics_data)
        print(f"\nMetrics keys observed (sample): {sorted(metrics_df.columns.tolist())}")


def analyze_ohlc(conn: sqlite3.Connection, limit: int) -> None:
    _print_header("2. OHLC DATA ANALYSIS")

    total = pd.read_sql_query("SELECT COUNT(*) AS n FROM ohlc", conn)["n"].iloc[0]
    print(f"\nTotal OHLC records: {total:,}")

    if limit <= 0:
        print("(skipped; --ohlc-limit <= 0)")
        return

    ohlc_summary = pd.read_sql_query(
        """
        SELECT
            exchange,
            symbol,
            interval,
            COUNT(*) as candle_count,
            MIN(close_time) as first_candle_ms,
            MAX(close_time) as last_candle_ms,
            MIN(close) as min_price,
            MAX(close) as max_price,
            AVG(volume) as avg_volume
        FROM ohlc
        GROUP BY exchange, symbol, interval
        ORDER BY candle_count DESC
        LIMIT ?
        """,
        conn,
        params=(int(limit),),
    )

    if ohlc_summary.empty:
        print("No OHLC summary rows returned.")
        return

    print(f"\nTop {len(ohlc_summary)} by candle count:")
    print(ohlc_summary[["symbol", "exchange", "interval", "candle_count", "min_price", "max_price"]])


def analyze_snapshots(conn: sqlite3.Connection, limit: int) -> None:
    _print_header("3. SNAPSHOT CACHE ANALYSIS (MARKET DATA)")

    # Older/newer DB files may not include snapshots.
    tables = set(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist())
    if "snapshot_cache" not in tables:
        print("\n(snapshot analysis skipped; table 'snapshot_cache' not found in this DB)")
        return

    snapshot_df = pd.read_sql_query(
        "SELECT * FROM snapshot_cache ORDER BY ts DESC LIMIT ?",
        conn,
        params=(int(limit),),
    )

    print(f"\nSnapshot records analyzed: {len(snapshot_df)}")
    if snapshot_df.empty:
        return

    for _, row in snapshot_df.iterrows():
        print(f"\nExchange: {row['exchange']}")
        print(f"Timestamp: {datetime.fromtimestamp(row['ts'] / 1000)}")

        snapshot_obj = _safe_json_loads(row["snapshot_json"])
        rows = _coerce_snapshot_to_rows(snapshot_obj)
        if not isinstance(rows, list):
            top = type(snapshot_obj).__name__
            keys = list(snapshot_obj.keys())[:30] if isinstance(snapshot_obj, dict) else None
            msg = f"Error parsing snapshot: snapshot_json did not contain an array payload (type={top}" + (
                f", keys={keys}" if keys else ""
            ) + ")"
            print(msg)
            continue

        df = pd.DataFrame(rows)
        print(f"Total pairs in snapshot: {len(df)}")
        if df.empty:
            continue

        def _vc(col: str):
            if col in df.columns:
                print(df[col].value_counts(dropna=False).head(20))
            else:
                print(f"(missing column: {col})")

        print("\nSignal Strength Distribution:")
        _vc("signal_strength")

        print("\nMulti-Timeframe Summary:")
        _vc("mtf_summary")

        if "market_cap" in df.columns:
            print("\nTop 10 by Market Cap:")
            top_mc = df[df["market_cap"].notna()].sort_values("market_cap", ascending=False).head(10)
            for _, item in top_mc.iterrows():
                mc_billion = float(item["market_cap"]) / 1e9
                print(f"  {str(item.get('symbol','')):15s} ${mc_billion:12,.2f}B")

        if "change_15m" in df.columns:
            print("\nTop 5 Gainers (15m):")
            top_gainers = df.sort_values("change_15m", ascending=False).head(5)
            for _, item in top_gainers.iterrows():
                change_pct = float(item["change_15m"]) * 100
                last_price = item.get("last_price")
                lp = f"${float(last_price):.4f}" if last_price is not None else "N/A"
                print(f"  {str(item.get('symbol','')):15s} {change_pct:+.4f}%  {lp}")

            print("\nTop 5 Losers (15m):")
            top_losers = df.sort_values("change_15m", ascending=True).head(5)
            for _, item in top_losers.iterrows():
                change_pct = float(item["change_15m"]) * 100
                last_price = item.get("last_price")
                lp = f"${float(last_price):.4f}" if last_price is not None else "N/A"
                print(f"  {str(item.get('symbol','')):15s} {change_pct:+.4f}%  {lp}")

        if "vol_15m" in df.columns:
            print("\nTop 10 by Volume (15m):")
            top_vol = df.sort_values("vol_15m", ascending=False).head(10)
            for _, item in top_vol.iterrows():
                print(f"  {str(item.get('symbol','')):15s} Vol: {float(item['vol_15m']):15,.2f}")

        indicators = ["rsi_14", "rsi_1h", "rsi_4h", "rsi_1d", "macd", "macd_1h", "macd_4h"]
        print("\nTechnical Indicators Statistics:")
        for ind in indicators:
            if ind in df.columns:
                valid = pd.to_numeric(df[ind], errors="coerce").dropna()
                if len(valid) > 0:
                    print(f"  {ind}: min={valid.min():.4f} max={valid.max():.4f} mean={valid.mean():.4f}")

        if "volatility_percentile" in df.columns:
            print("\nVolatility Percentile:")
            print(pd.to_numeric(df["volatility_percentile"], errors="coerce").describe())

        if "sector_tags" in df.columns:
            all_sectors: list[str] = []
            for sectors in df["sector_tags"].dropna():
                if isinstance(sectors, list):
                    all_sectors.extend([str(s) for s in sectors])
            if all_sectors:
                sector_counts = Counter(all_sectors)
                print("\nTop 10 Sectors:")
                for sector, count in sector_counts.most_common(10):
                    print(f"  {sector:30s}: {count}")


def analyze_market_cap_cache(conn: sqlite3.Connection, limit: int) -> None:
    _print_header("4. MARKET CAP CACHE ANALYSIS")

    total = pd.read_sql_query("SELECT COUNT(*) AS n FROM market_cap_cache", conn)["n"].iloc[0]
    print(f"\nTotal tokens with market cap data: {total:,}")

    if limit <= 0:
        print("(skipped; --market-cap-limit <= 0)")
        return

    mc_df = pd.read_sql_query(
        "SELECT * FROM market_cap_cache ORDER BY market_cap DESC LIMIT ?",
        conn,
        params=(int(limit),),
    )

    print(f"\nTop {len(mc_df)} by Market Cap:")
    for _, row in mc_df.iterrows():
        mc_billion = float(row["market_cap"]) / 1e9
        print(f"{row['symbol']:10s} ${mc_billion:12,.2f}B")


def analyze_trade_plans(conn: sqlite3.Connection) -> None:
    _print_header("5. TRADE PLANS ANALYSIS")

    total = pd.read_sql_query("SELECT COUNT(*) AS n FROM trade_plans", conn)["n"].iloc[0]
    print(f"\nTotal trade plans: {total:,}")

    trade_plans_summary = pd.read_sql_query(
        """
        SELECT
            side,
            entry_type,
            COUNT(*) as count,
            AVG(rr_tp1) as avg_rr_tp1,
            AVG(rr_tp2) as avg_rr_tp2,
            AVG(rr_tp3) as avg_rr_tp3,
            AVG(atr) as avg_atr,
            AVG(atr_mult) as avg_atr_mult
        FROM trade_plans
        GROUP BY side, entry_type
        """,
        conn,
    )

    print("\nTrade plan summary by side/entry_type:")
    print(trade_plans_summary)

    top_symbols = pd.read_sql_query(
        """
        SELECT
            symbol,
            COUNT(*) as plan_count,
            AVG(rr_tp1) as avg_rr_tp1
        FROM trade_plans
        WHERE rr_tp1 IS NOT NULL
        GROUP BY symbol
        ORDER BY plan_count DESC
        LIMIT 10
        """,
        conn,
    )

    print("\nTop 10 symbols by plan count:")
    print(top_symbols)


def main() -> None:
    ap = argparse.ArgumentParser(description="Comprehensive crypto SQLite analysis.")
    ap.add_argument("db", nargs="?", default="ohlc.sqlite3", help="Path to SQLite DB")
    ap.add_argument("--alerts-limit", type=int, default=100, help="Number of most recent alerts to analyze")
    ap.add_argument("--ohlc-limit", type=int, default=20, help="Top N (exchange,symbol,interval) groups by candle count")
    ap.add_argument("--snapshots-limit", type=int, default=5, help="Number of most recent snapshots to analyze")
    ap.add_argument("--market-cap-limit", type=int, default=20, help="Top N market cap cache rows")
    ap.add_argument(
        "--trade-plans-only",
        action="store_true",
        help="Only run trade_plans section (useful when trade_plans drive research)",
    )
    args = ap.parse_args()

    print("=" * 80)
    print("COMPREHENSIVE CRYPTO DATABASE ANALYSIS")
    print("=" * 80)
    print(f"DB: {args.db}")

    conn = sqlite3.connect(args.db)
    try:
        if not args.trade_plans_only:
            analyze_alerts(conn, args.alerts_limit)
            analyze_ohlc(conn, args.ohlc_limit)
            analyze_snapshots(conn, args.snapshots_limit)
            analyze_market_cap_cache(conn, args.market_cap_limit)
        analyze_trade_plans(conn)
    finally:
        conn.close()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
