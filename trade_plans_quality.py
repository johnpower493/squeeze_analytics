import argparse
import sqlite3
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class QualityThresholds:
    min_risk_per_unit: float = 0.0
    max_rr_reasonable: float = 50.0
    max_atr_mult_reasonable: float = 50.0


def _print_header(title: str, width: int = 88) -> None:
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def load_trade_plans(conn: sqlite3.Connection, limit: int | None) -> pd.DataFrame:
    q = "SELECT * FROM trade_plans"
    if limit and limit > 0:
        q += " ORDER BY ts DESC LIMIT ?"
        return pd.read_sql_query(q, conn, params=(int(limit),))
    return pd.read_sql_query(q, conn)


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Normalize numeric columns that should be numeric (SQLite may store as text in some cases)
    numeric_cols = [
        "entry_price",
        "stop_loss",
        "tp1",
        "tp2",
        "tp3",
        "atr",
        "atr_mult",
        "risk_per_unit",
        "rr_tp1",
        "rr_tp2",
        "rr_tp3",
    ]
    for c in numeric_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    # Risk per unit derived (absolute price distance)
    if {"entry_price", "stop_loss"}.issubset(out.columns):
        out["risk_abs"] = (out["entry_price"] - out["stop_loss"]).abs()

    # Expected direction checks
    if {"side", "entry_price", "stop_loss"}.issubset(out.columns):
        out["stop_correct_side"] = True
        buy = out["side"].astype(str).str.upper() == "BUY"
        sell = out["side"].astype(str).str.upper() == "SELL"
        out.loc[buy, "stop_correct_side"] = out.loc[buy, "stop_loss"] < out.loc[buy, "entry_price"]
        out.loc[sell, "stop_correct_side"] = out.loc[sell, "stop_loss"] > out.loc[sell, "entry_price"]

    for tp_col, flag_col in [("tp1", "tp1_correct_side"), ("tp2", "tp2_correct_side"), ("tp3", "tp3_correct_side")]:
        if {"side", "entry_price", tp_col}.issubset(out.columns):
            out[flag_col] = True
            buy = out["side"].astype(str).str.upper() == "BUY"
            sell = out["side"].astype(str).str.upper() == "SELL"
            out.loc[buy, flag_col] = out.loc[buy, tp_col].isna() | (out.loc[buy, tp_col] > out.loc[buy, "entry_price"])
            out.loc[sell, flag_col] = out.loc[sell, tp_col].isna() | (out.loc[sell, tp_col] < out.loc[sell, "entry_price"])

    return out


def summarize_nulls(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    n = len(df)
    for c in cols:
        if c not in df.columns:
            continue
        nn = int(df[c].notna().sum())
        rows.append({"column": c, "non_null": nn, "null": n - nn, "non_null_pct": (nn / n * 100.0) if n else 0.0})
    return pd.DataFrame(rows).sort_values(["null", "column"], ascending=[False, True])


def count_flag(df: pd.DataFrame, flag_col: str) -> tuple[int, float]:
    if flag_col not in df.columns:
        return 0, 0.0
    bad = int((df[flag_col] == False).sum())
    pct = (bad / len(df) * 100.0) if len(df) else 0.0
    return bad, pct


def run_quality_report(db: str, limit: int | None, thresholds: QualityThresholds) -> int:
    conn = sqlite3.connect(db)
    try:
        # Ensure table exists
        tables = set(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist())
        if "trade_plans" not in tables:
            print(f"ERROR: table 'trade_plans' not found in DB: {db}")
            return 2

        df = load_trade_plans(conn, limit)
    finally:
        conn.close()

    _print_header("TRADE PLANS QUALITY REPORT")
    print(f"DB: {db}")
    print(f"Rows analyzed: {len(df):,}" + (f" (limited)" if limit else ""))

    if df.empty:
        print("No trade_plans rows.")
        return 0

    # High-level distributions
    _print_header("DISTRIBUTIONS")
    for c in ["exchange", "side", "entry_type", "swing_ref"]:
        if c in df.columns:
            print(f"\n{c}:")
            print(df[c].value_counts(dropna=False).head(20).to_string())

    # Null coverage
    _print_header("COLUMN COVERAGE (NULLS)")
    key_cols = [
        "exchange",
        "symbol",
        "side",
        "entry_type",
        "entry_price",
        "stop_loss",
        "tp1",
        "tp2",
        "tp3",
        "atr",
        "atr_mult",
        "risk_per_unit",
        "rr_tp1",
        "rr_tp2",
        "rr_tp3",
        "plan_json",
    ]
    print(summarize_nulls(df, key_cols).to_string(index=False))

    # Derived consistency checks
    df2 = add_derived_fields(df)

    _print_header("CONSISTENCY CHECKS (ENTRY_PRICE-BASED)")

    # Missing critical prices
    missing_entry = int(df2["entry_price"].isna().sum()) if "entry_price" in df2.columns else 0
    missing_stop = int(df2["stop_loss"].isna().sum()) if "stop_loss" in df2.columns else 0
    print(f"Missing entry_price: {missing_entry:,} ({missing_entry/len(df2)*100:.2f}%)")
    print(f"Missing stop_loss:   {missing_stop:,} ({missing_stop/len(df2)*100:.2f}%)")

    # Stop/TP direction
    bad_stop, bad_stop_pct = count_flag(df2, "stop_correct_side")
    print(f"Stop on wrong side of entry: {bad_stop:,} ({bad_stop_pct:.2f}%)")

    for tp_flag, tp_col in [("tp1_correct_side", "tp1"), ("tp2_correct_side", "tp2"), ("tp3_correct_side", "tp3")]:
        bad, pct = count_flag(df2, tp_flag)
        if tp_flag in df2.columns:
            present = int(df2[tp_col].notna().sum()) if tp_col in df2.columns else 0
            print(f"{tp_col} on wrong side of entry (of {present:,} present): {bad:,} ({pct:.2f}% of all plans)")

    # Risk sanity
    if "risk_abs" in df2.columns:
        zero_risk = int((df2["risk_abs"] == 0).sum())
        neg_or_zero_risk = int((df2["risk_abs"] <= thresholds.min_risk_per_unit).sum())
        print(f"Zero risk (entry == stop): {zero_risk:,} ({zero_risk/len(df2)*100:.2f}%)")
        print(f"Risk <= {thresholds.min_risk_per_unit}: {neg_or_zero_risk:,} ({neg_or_zero_risk/len(df2)*100:.2f}%)")

    # Provided risk_per_unit vs derived risk
    if "risk_per_unit" in df2.columns and "risk_abs" in df2.columns:
        # consider only rows with both populated
        both = df2[df2["risk_per_unit"].notna() & df2["risk_abs"].notna()].copy()
        if len(both) > 0:
            both["risk_per_unit"] = pd.to_numeric(both["risk_per_unit"], errors="coerce")
            both["risk_ratio"] = both["risk_per_unit"] / both["risk_abs"].replace({0: pd.NA})
            bad_risk_ratio = both[(both["risk_ratio"] < 0.5) | (both["risk_ratio"] > 2.0)]
            print(f"risk_per_unit vs |entry-stop| mismatch (ratio outside [0.5,2.0]): {len(bad_risk_ratio):,} / {len(both):,}")

    # Outlier checks (heuristic)
    _print_header("OUTLIER CHECKS (HEURISTIC)")
    if "atr_mult" in df2.columns:
        outliers = int((df2["atr_mult"] > thresholds.max_atr_mult_reasonable).sum())
        print(f"atr_mult > {thresholds.max_atr_mult_reasonable}: {outliers:,}")
    for rr_col in ["rr_tp1", "rr_tp2", "rr_tp3"]:
        if rr_col in df2.columns:
            outliers = int((df2[rr_col] > thresholds.max_rr_reasonable).sum())
            print(f"{rr_col} > {thresholds.max_rr_reasonable}: {outliers:,}")

    # Top offenders samples
    _print_header("SAMPLE: PLANS WITH DIRECTIONAL ISSUES")
    issue_cols = [c for c in ["stop_correct_side", "tp1_correct_side", "tp2_correct_side", "tp3_correct_side"] if c in df2.columns]
    if issue_cols:
        issues = df2.copy()
        mask = False
        for c in issue_cols:
            mask = mask | (issues[c] == False)
        bad_df = issues[mask]
        if bad_df.empty:
            print("No directional issues found.")
        else:
            cols = [c for c in ["id", "alert_id", "exchange", "symbol", "side", "entry_price", "stop_loss", "tp1", "tp2", "tp3"] if c in bad_df.columns]
            print(bad_df[cols].head(20).to_string(index=False))
    else:
        print("Directional issue flags not computed (missing required columns).")

    _print_header("RECOMMENDED NEXT STEPS")
    print("- Since you backtest with entry_price fill logic, directional checks (stop/TP relative to entry) are the #1 data hygiene gate.")
    print("- Consider persisting 'risk_abs' and derived RR values into a Silver table on Databricks for consistent downstream metrics.")

    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Trade plan data quality report (entry_price-based).")
    ap.add_argument("db", nargs="?", default="ohlc.sqlite3", help="Path to SQLite DB")
    ap.add_argument("--limit", type=int, default=0, help="Analyze only last N rows by ts (0=all)")
    ap.add_argument("--max-rr", type=float, default=50.0, help="Heuristic outlier threshold for RR columns")
    ap.add_argument("--max-atr-mult", type=float, default=50.0, help="Heuristic outlier threshold for atr_mult")
    args = ap.parse_args()

    thresholds = QualityThresholds(max_rr_reasonable=float(args.max_rr), max_atr_mult_reasonable=float(args.max_atr_mult))
    raise SystemExit(run_quality_report(args.db, args.limit if args.limit > 0 else None, thresholds))


if __name__ == "__main__":
    main()
