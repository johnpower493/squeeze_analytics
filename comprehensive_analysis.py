import sqlite3
import pandas as pd
import json
from datetime import datetime
from collections import Counter

print("=" * 80)
print("COMPREHENSIVE CRYPTO DATABASE ANALYSIS")
print("=" * 80)

conn = sqlite3.connect('ohlc.sqlite3')

# ============================================
# 1. ALERTS TABLE ANALYSIS
# ============================================
print("\n" + "=" * 80)
print("1. ALERTS TABLE ANALYSIS")
print("=" * 80)

query = """
SELECT * FROM alerts
ORDER BY created_ts DESC
LIMIT 100
"""
alerts_df = pd.read_sql_query(query, conn)

print(f"\nTotal alerts in database: 17,031")
print(f"Sample data (last 100 alerts):")
print(f"\nAlert signal distribution:")
print(alerts_df['signal'].value_counts())

print(f"\nAlert source timeframe distribution:")
print(alerts_df['source_tf'].value_counts())

print(f"\nTop 10 exchanges by alerts:")
print(alerts_df['exchange'].value_counts().head(10))

# Parse metrics_json for additional insights
metrics_data = []
for metrics in alerts_df['metrics_json'].dropna():
    try:
        metrics_data.append(json.loads(metrics))
    except:
        pass

if metrics_data:
    metrics_df = pd.DataFrame(metrics_data)
    print(f"\nMetrics available: {metrics_df.columns.tolist()}")

# ============================================
# 2. OHLC DATA ANALYSIS
# ============================================
print("\n" + "=" * 80)
print("2. OHLC DATA ANALYSIS")
print("=" * 80)

# Get OHLC stats
query = """
SELECT 
    exchange,
    symbol,
    interval,
    COUNT(*) as candle_count,
    MIN(close_time) as first_candle,
    MAX(close_time) as last_candle,
    MIN(close) as min_price,
    MAX(close) as max_price,
    AVG(volume) as avg_volume
FROM ohlc
GROUP BY exchange, symbol, interval
ORDER BY candle_count DESC
LIMIT 20
"""
ohlc_summary = pd.read_sql_query(query, conn)

print(f"\nTotal OHLC records: 57,368")
print("\nTop 20 by candle count:")
print(ohlc_summary[['symbol', 'exchange', 'interval', 'candle_count', 'min_price', 'max_price']])

# ============================================
# 3. SNAPSHOT CACHE ANALYSIS
# ============================================
print("\n" + "=" * 80)
print("3. SNAPSHOT CACHE ANALYSIS (MARKET DATA)")
print("=" * 80)

query = "SELECT * FROM snapshot_cache"
snapshot_df = pd.read_sql_query(query, conn)

print(f"\nSnapshot records: {len(snapshot_df)}")

for idx, row in snapshot_df.iterrows():
    print(f"\nExchange: {row['exchange']}")
    print(f"Timestamp: {datetime.fromtimestamp(row['ts'] / 1000)}")
    
    try:
        snapshot_data = json.loads(row['snapshot_json'])
        df = pd.DataFrame(snapshot_data)
        
        print(f"Total pairs in snapshot: {len(df)}")
        
        # Signal strength
        print(f"\nSignal Strength Distribution:")
        print(df['signal_strength'].value_counts())
        
        # MTF Summary
        print(f"\nMulti-Timeframe Summary:")
        print(df['mtf_summary'].value_counts())
        
        # Top 10 by market cap
        print(f"\nTop 10 by Market Cap:")
        top_mc = df[df['market_cap'].notna()].sort_values('market_cap', ascending=False).head(10)
        for _, item in top_mc.iterrows():
            mc_billion = item['market_cap'] / 1e9
            print(f"  {item['symbol']:15s} ${mc_billion:12,.2f}B")
        
        # Top gainers/losers
        print(f"\nTop 5 Gainers (15m):")
        top_gainers = df.sort_values('change_15m', ascending=False).head(5)
        for _, item in top_gainers.iterrows():
            change_pct = item['change_15m'] * 100
            print(f"  {item['symbol']:15s} {change_pct:+.4f}%  ${item['last_price']:.4f}")
        
        print(f"\nTop 5 Losers (15m):")
        top_losers = df.sort_values('change_15m', ascending=True).head(5)
        for _, item in top_losers.iterrows():
            change_pct = item['change_15m'] * 100
            print(f"  {item['symbol']:15s} {change_pct:+.4f}%  ${item['last_price']:.4f}")
        
        # Top 10 by volume
        print(f"\nTop 10 by Volume (15m):")
        top_vol = df.sort_values('vol_15m', ascending=False).head(10)
        for _, item in top_vol.iterrows():
            print(f"  {item['symbol']:15s} Vol: {item['vol_15m']:15,.2f}")
        
        # Technical indicators stats
        print(f"\nTechnical Indicators Statistics:")
        indicators = ['rsi_14', 'rsi_1h', 'rsi_4h', 'rsi_1d', 'macd', 'macd_1h', 'macd_4h']
        for ind in indicators:
            if ind in df.columns:
                valid = df[ind].dropna()
                if len(valid) > 0:
                    print(f"  {ind}:")
                    print(f"    Min: {valid.min():.4f}")
                    print(f"    Max: {valid.max():.4f}")
                    print(f"    Mean: {valid.mean():.4f}")
        
        # Volatility analysis
        print(f"\nVolatility Percentile:")
        vol_stats = df['volatility_percentile'].describe()
        print(vol_stats)
        
        # Sector analysis
        all_sectors = []
        for sectors in df['sector_tags'].dropna():
            all_sectors.extend(sectors)
        sector_counts = Counter(all_sectors)
        print(f"\nTop 10 Sectors:")
        for sector, count in sector_counts.most_common(10):
            print(f"  {sector:30s}: {count}")
        
    except Exception as e:
        print(f"Error parsing snapshot: {e}")

# ============================================
# 4. MARKET CAP CACHE ANALYSIS
# ============================================
print("\n" + "=" * 80)
print("4. MARKET CAP CACHE ANALYSIS")
print("=" * 80)

query = "SELECT * FROM market_cap_cache ORDER BY market_cap DESC LIMIT 20"
mc_df = pd.read_sql_query(query, conn)

print(f"\nTotal tokens with market cap data: 237")
print("\nTop 20 by Market Cap:")
for idx, row in mc_df.iterrows():
    mc_billion = row['market_cap'] / 1e9
    print(f"{row['symbol']:10s} ${mc_billion:12,.2f}B")

# ============================================
# 5. TRADE PLANS ANALYSIS
# ============================================
print("\n" + "=" * 80)
print("5. TRADE PLANS ANALYSIS")
print("=" * 80)

query = """
SELECT 
    side,
    entry_type,
    COUNT(*) as count,
    AVG(rr_tp1) as avg_rr_tp1,
    AVG(rr_tp2) as avg_rr_tp2,
    AVG(rr_tp3) as avg_rr_tp3
FROM trade_plans
GROUP BY side, entry_type
"""
trade_plans_summary = pd.read_sql_query(query, conn)

print(f"\nTotal trade plans: 17,031")
print("\nTrade plan summary:")
print(trade_plans_summary)

query = """
SELECT 
    symbol,
    COUNT(*) as plan_count,
    AVG(rr_tp1) as avg_rr_tp1
FROM trade_plans
WHERE rr_tp1 IS NOT NULL
GROUP BY symbol
ORDER BY plan_count DESC
LIMIT 10
"""
top_symbols = pd.read_sql_query(query, conn)

print(f"\nTop 10 symbols by plan count:")
print(top_symbols)

conn.close()

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
