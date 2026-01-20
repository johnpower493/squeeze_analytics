import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime

import pandas as pd


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

    # Common wrapper keys from APIs
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
        # sometimes nested like {data: {items: [...]}}
        if isinstance(v, dict):
            for kk in candidate_keys:
                vv = v.get(kk)
                if isinstance(vv, list):
                    return vv

    # Fallback: first list value that looks like rows
    for v in obj.values():
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, list):
                    return vv

    return None


def _print_header(title: str, width: int = 70) -> None:
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def load_snapshot(conn: sqlite3.Connection, exchange: str | None, latest: bool) -> tuple[str, int, pd.DataFrame]:
    tables = set(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist())
    if "snapshot_cache" not in tables:
        raise SystemExit("Table 'snapshot_cache' not found in this DB. Cannot run snapshot analysis.")

    if latest:
        if exchange:
            row = pd.read_sql_query(
                "SELECT exchange, ts, snapshot_json FROM snapshot_cache WHERE exchange = ? ORDER BY ts DESC LIMIT 1",
                conn,
                params=(exchange,),
            )
        else:
            row = pd.read_sql_query(
                "SELECT exchange, ts, snapshot_json FROM snapshot_cache ORDER BY ts DESC LIMIT 1",
                conn,
            )
    else:
        # oldest snapshot can be useful for diffing when you have many
        if exchange:
            row = pd.read_sql_query(
                "SELECT exchange, ts, snapshot_json FROM snapshot_cache WHERE exchange = ? ORDER BY ts ASC LIMIT 1",
                conn,
                params=(exchange,),
            )
        else:
            row = pd.read_sql_query(
                "SELECT exchange, ts, snapshot_json FROM snapshot_cache ORDER BY ts ASC LIMIT 1",
                conn,
            )

    if row.empty:
        raise SystemExit("No snapshot_cache rows found (or exchange not present).")

    ex = row["exchange"].iloc[0]
    ts = int(row["ts"].iloc[0])
    payload = row["snapshot_json"].iloc[0]

    data = _safe_json_loads(payload)
    rows = _coerce_snapshot_to_rows(data)
    if not isinstance(rows, list):
        top = type(data).__name__
        keys = list(data.keys())[:30] if isinstance(data, dict) else None
        raise SystemExit(
            "snapshot_json did not contain a list payload that this script can analyze. "
            f"Top-level type={top}" + (f", keys={keys}" if keys else "")
        )

    df = pd.DataFrame(rows)
    return ex, ts, df


def main() -> None:
    ap = argparse.ArgumentParser(description="Detailed snapshot_cache analysis.")
    ap.add_argument("db", nargs="?", default="ohlc.sqlite3", help="Path to SQLite DB")
    ap.add_argument("--exchange", default=None, help="Filter snapshots by exchange")
    ap.add_argument(
        "--latest",
        action="store_true",
        help="Analyze latest snapshot (default: oldest; useful once you have many snapshots)",
    )
    args = ap.parse_args()

    print("=" * 70)
    print("DETAILED CRYPTO DATABASE ANALYSIS")
    print("=" * 70)
    print(f"DB: {args.db}")

    conn = sqlite3.connect(args.db)
    try:
        exchange, ts, df = load_snapshot(conn, args.exchange, latest=args.latest)
    finally:
        conn.close()

    print(f"\nSnapshot exchange: {exchange}")
    print(f"Snapshot timestamp: {datetime.fromtimestamp(ts / 1000)}")
    print(f"Total crypto pairs tracked: {len(df)}")

    if df.empty:
        print("No rows in snapshot payload.")
        return

    _print_header("EXCHANGE DISTRIBUTION")
    if "exchange" in df.columns:
        print(df["exchange"].value_counts().to_string())
    else:
        print("(missing column: exchange)")

    _print_header("MARKET CAP ANALYSIS (Top 20)")
    if "market_cap" in df.columns:
        market_cap_df = df[pd.to_numeric(df["market_cap"], errors="coerce").notna()].copy()
        market_cap_df["market_cap"] = pd.to_numeric(market_cap_df["market_cap"], errors="coerce")
        market_cap_df = market_cap_df.sort_values("market_cap", ascending=False)
        for _, row in market_cap_df.head(20).iterrows():
            mc_billion = float(row["market_cap"]) / 1e9
            print(f"{str(row.get('symbol','')):15s} ${mc_billion:12,.2f}B")
    else:
        print("(missing column: market_cap)")

    _print_header("LIQUIDITY ANALYSIS")
    if "liquidity_top200" in df.columns and "liquidity_rank" in df.columns:
        tmp = df.copy()
        tmp["liquidity_rank"] = pd.to_numeric(tmp["liquidity_rank"], errors="coerce")
        liquidity_df = tmp[tmp["liquidity_top200"] == True].sort_values("liquidity_rank")
        print(f"Total pairs in top 200 by liquidity: {len(liquidity_df)}")
        print("\nTop 20 by liquidity rank:")
        for _, row in liquidity_df.head(20).iterrows():
            mc = row.get("market_cap")
            mc_b = float(mc) / 1e9 if mc is not None else float('nan')
            print(f"{str(row.get('symbol','')):15s}  Rank: {int(row['liquidity_rank']) if pd.notna(row['liquidity_rank']) else -1:3d}  MC: ${mc_b:10.2f}B")
    else:
        print("(missing columns: liquidity_top200/liquidity_rank)")

    _print_header("SIGNAL STRENGTH DISTRIBUTION")
    if "signal_strength" in df.columns:
        print(df["signal_strength"].value_counts(dropna=False).to_string())
    else:
        print("(missing column: signal_strength)")

    _print_header("MULTI-TIMEFRAME (MTF) SUMMARY")
    if "mtf_summary" in df.columns:
        print(df["mtf_summary"].value_counts(dropna=False).to_string())
    else:
        print("(missing column: mtf_summary)")

    _print_header("SECTOR TAGS ANALYSIS")
    if "sector_tags" in df.columns:
        all_sectors: list[str] = []
        for sectors in df["sector_tags"].dropna():
            if isinstance(sectors, list):
                all_sectors.extend([str(s) for s in sectors])
        sector_counts = Counter(all_sectors)
        if sector_counts:
            print("\nMost common sectors:")
            for sector, count in sector_counts.most_common(20):
                print(f"{sector:30s}: {count:3d}")
        else:
            print("No sector tags in snapshot.")
    else:
        print("(missing column: sector_tags)")

    _print_header("TECHNICAL INDICATORS STATISTICS")
    indicators = ["rsi_14", "rsi_1h", "rsi_4h", "rsi_1d", "macd", "macd_1h", "macd_4h", "macd_1d"]
    for indicator in indicators:
        if indicator in df.columns:
            valid_data = pd.to_numeric(df[indicator], errors="coerce").dropna()
            if len(valid_data) > 0:
                print(f"\n{indicator}:")
                print(f"  Min: {valid_data.min():.4f}")
                print(f"  Max: {valid_data.max():.4f}")
                print(f"  Mean: {valid_data.mean():.4f}")
                print(f"  Median: {valid_data.median():.4f}")

    _print_header("MOMENTUM ANALYSIS")
    for col in ["momentum_score", "impulse_score", "signal_score"]:
        if col in df.columns:
            v = pd.to_numeric(df[col], errors="coerce")
            if v.notna().any():
                print(f"\n{col}:")
                print(f"  Min: {v.min():.4f}")
                print(f"  Max: {v.max():.4f}")
                print(f"  Mean: {v.mean():.4f}")

    _print_header("PRICE CHANGES ANALYSIS")
    for col in ["change_1m", "change_5m", "change_15m", "change_60m"]:
        if col in df.columns:
            valid = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(valid) > 0:
                print(f"\n{col}:")
                print(f"  Min: {valid.min()*100:.4f}%")
                print(f"  Max: {valid.max()*100:.4f}%")
                print(f"  Mean: {valid.mean()*100:.4f}%")

    if "change_15m" in df.columns:
        _print_header("TOP GAINERS AND LOSERS (15 minutes)")
        df_sorted = df.copy()
        df_sorted["change_15m"] = pd.to_numeric(df_sorted["change_15m"], errors="coerce")
        df_sorted = df_sorted.sort_values("change_15m", ascending=False)

        print("\nTop 10 Gainers:")
        for _, row in df_sorted.head(10).iterrows():
            change_pct = float(row["change_15m"]) * 100 if pd.notna(row["change_15m"]) else float('nan')
            lp = row.get("last_price")
            lp_str = f"${float(lp):.4f}" if lp is not None else "N/A"
            print(f"{str(row.get('symbol','')):15s}  {change_pct:+.4f}%  Price: {lp_str}")

        print("\nTop 10 Losers:")
        for _, row in df_sorted.tail(10).iterrows():
            change_pct = float(row["change_15m"]) * 100 if pd.notna(row["change_15m"]) else float('nan')
            lp = row.get("last_price")
            lp_str = f"${float(lp):.4f}" if lp is not None else "N/A"
            print(f"{str(row.get('symbol','')):15s}  {change_pct:+.4f}%  Price: {lp_str}")

    _print_header("VOLATILITY ANALYSIS")
    if "volatility_percentile" in df.columns:
        vol_dist = pd.to_numeric(df["volatility_percentile"], errors="coerce").describe()
        print(vol_dist.to_string())
    else:
        print("(missing column: volatility_percentile)")

    _print_header("VOLUME ANALYSIS")
    for col in ["vol_1m", "vol_5m", "vol_15m", "rvol_1m"]:
        if col in df.columns:
            valid = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(valid) > 0:
                print(f"\n{col}:")
                print(f"  Min: {valid.min():,.2f}")
                print(f"  Max: {valid.max():,.2f}")
                print(f"  Mean: {valid.mean():,.2f}")

    if "vol_15m" in df.columns:
        _print_header("TOP 10 BY VOLUME (15 minutes)")
        df_sorted_vol = df.copy()
        df_sorted_vol["vol_15m"] = pd.to_numeric(df_sorted_vol["vol_15m"], errors="coerce")
        df_sorted_vol = df_sorted_vol.sort_values("vol_15m", ascending=False)
        for _, row in df_sorted_vol.head(10).iterrows():
            lp = row.get("last_price")
            lp_str = f"${float(lp):.4f}" if lp is not None else "N/A"
            print(f"{str(row.get('symbol','')):15s}  Vol: {float(row['vol_15m']):15,.2f}  Price: {lp_str}")

    _print_header("OPEN INTEREST ANALYSIS")
    if "open_interest" in df.columns:
        oi_valid = df[pd.to_numeric(df["open_interest"], errors="coerce").notna()].copy()
        oi_valid["open_interest"] = pd.to_numeric(oi_valid["open_interest"], errors="coerce")
        if len(oi_valid) > 0:
            print("\nTop 10 by Open Interest:")
            oi_sorted = oi_valid.sort_values("open_interest", ascending=False).head(10)
            for _, row in oi_sorted.iterrows():
                oi_millions = float(row["open_interest"]) / 1e6
                lp = row.get("last_price")
                lp_str = f"${float(lp):.4f}" if lp is not None else "N/A"
                print(f"{str(row.get('symbol','')):15s}  OI: ${oi_millions:10.2f}M  Price: {lp_str}")
        else:
            print("No open interest values in snapshot.")
    else:
        print("(missing column: open_interest)")

    if "funding_rate" in df.columns:
        funding_df = df[pd.to_numeric(df["funding_rate"], errors="coerce").notna()].copy()
        funding_df["funding_rate"] = pd.to_numeric(funding_df["funding_rate"], errors="coerce")
        if len(funding_df) > 0:
            _print_header("FUNDING RATE ANALYSIS")
            print(f"Pairs with funding data: {len(funding_df)}")
            print("\nFunding Rate:")
            print(f"  Min: {funding_df['funding_rate'].min()*100:.4f}%")
            print(f"  Max: {funding_df['funding_rate'].max()*100:.4f}%")
            print(f"  Mean: {funding_df['funding_rate'].mean()*100:.4f}%")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
