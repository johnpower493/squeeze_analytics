import sqlite3
import pandas as pd
import json
from collections import Counter

print("=" * 70)
print("DETAILED CRYPTO DATABASE ANALYSIS")
print("=" * 70)

conn = sqlite3.connect('ohlc.sqlite3')

# Parse JSON data from market_data table
cursor = conn.cursor()
cursor.execute("SELECT data FROM market_data")
raw_data = cursor.fetchone()

# Parse JSON and create dataframe
if raw_data and raw_data[0]:
    try:
        # The data is stored as a JSON array
        data = json.loads(raw_data[0])
        df = pd.DataFrame(data)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        df = pd.DataFrame()
else:
    df = pd.DataFrame()

print(f"\nTotal crypto pairs tracked: {len(df)}")
print(f"Data timestamp: {pd.to_datetime(df['ts'].iloc[0], unit='ms')}")

# Exchange distribution
print("\n" + "=" * 70)
print("EXCHANGE DISTRIBUTION")
print("=" * 70)
print(df['exchange'].value_counts().to_string())

# Market Cap Analysis
print("\n" + "=" * 70)
print("MARKET CAP ANALYSIS (Top 20)")
print("=" * 70)
market_cap_df = df[df['market_cap'].notna()].sort_values('market_cap', ascending=False)
for idx, row in market_cap_df.head(20).iterrows():
    mc_billion = row['market_cap'] / 1e9
    print(f"{row['symbol']:15s} ${mc_billion:12,.2f}B  {row.get('sector_tags', 'N/A')}")

# Liquidity Analysis
print("\n" + "=" * 70)
print("LIQUIDITY ANALYSIS")
print("=" * 70)
liquidity_df = df[df['liquidity_top200'] == True].sort_values('liquidity_rank')
print(f"Total pairs in top 200 by liquidity: {len(liquidity_df)}")
print("\nTop 20 by liquidity rank:")
for idx, row in liquidity_df.head(20).iterrows():
    print(f"{row['symbol']:15s}  Rank: {row['liquidity_rank']:3d}  MC: ${row['market_cap']/1e9:10.2f}B")

# Signal Strength Distribution
print("\n" + "=" * 70)
print("SIGNAL STRENGTH DISTRIBUTION")
print("=" * 70)
signal_counts = df['signal_strength'].value_counts()
print(signal_counts.to_string())

# Multi-timeframe Analysis
print("\n" + "=" * 70)
print("MULTI-TIMEFRAME (MTF) SUMMARY")
print("=" * 70)
mtf_counts = df['mtf_summary'].value_counts()
print(mtf_counts.to_string())

# Sector Tags Analysis
print("\n" + "=" * 70)
print("SECTOR TAGS ANALYSIS")
print("=" * 70)
all_sectors = []
for sectors in df['sector_tags'].dropna():
    all_sectors.extend(sectors)
sector_counts = Counter(all_sectors)
print("\nMost common sectors:")
for sector, count in sector_counts.most_common(20):
    print(f"{sector:30s}: {count:3d}")

# Technical Indicators Statistics
print("\n" + "=" * 70)
print("TECHNICAL INDICATORS STATISTICS")
print("=" * 70)

indicators = ['rsi_14', 'rsi_1h', 'rsi_4h', 'rsi_1d', 'macd', 'macd_1h', 'macd_4h', 'macd_1d']
for indicator in indicators:
    if indicator in df.columns and df[indicator].notna().sum() > 0:
        valid_data = df[indicator].dropna()
        print(f"\n{indicator}:")
        print(f"  Min: {valid_data.min():.4f}")
        print(f"  Max: {valid_data.max():.4f}")
        print(f"  Mean: {valid_data.mean():.4f}")
        print(f"  Median: {valid_data.median():.4f}")

# Momentum Analysis
print("\n" + "=" * 70)
print("MOMENTUM ANALYSIS")
print("=" * 70)
momentum_cols = ['momentum_score', 'impulse_score', 'signal_score']
for col in momentum_cols:
    if col in df.columns:
        print(f"\n{col}:")
        print(f"  Min: {df[col].min():.4f}")
        print(f"  Max: {df[col].max():.4f}")
        print(f"  Mean: {df[col].mean():.4f}")

# Price Changes Analysis
print("\n" + "=" * 70)
print("PRICE CHANGES ANALYSIS")
print("=" * 70)
change_cols = ['change_1m', 'change_5m', 'change_15m', 'change_60m']
for col in change_cols:
    if col in df.columns:
        print(f"\n{col}:")
        valid = df[col].dropna()
        print(f"  Min: {valid.min()*100:.4f}%")
        print(f"  Max: {valid.max()*100:.4f}%")
        print(f"  Mean: {valid.mean()*100:.4f}%")

# Top Gainers and Losers (15m)
print("\n" + "=" * 70)
print("TOP GAINERS AND LOSERS (15 minutes)")
print("=" * 70)
df_sorted = df.sort_values('change_15m', ascending=False)
print("\nTop 10 Gainers:")
for idx, row in df_sorted.head(10).iterrows():
    change_pct = row['change_15m'] * 100
    print(f"{row['symbol']:15s}  {change_pct:+.4f}%  Price: ${row['last_price']:.4f}")

print("\nTop 10 Losers:")
for idx, row in df_sorted.tail(10).iterrows():
    change_pct = row['change_15m'] * 100
    print(f"{row['symbol']:15s}  {change_pct:+.4f}%  Price: ${row['last_price']:.4f}")

# Volatility Analysis
print("\n" + "=" * 70)
print("VOLATILITY ANALYSIS")
print("=" * 70)
print(f"\nVolatility Percentile Distribution:")
vol_dist = df['volatility_percentile'].describe()
print(vol_dist.to_string())

# Volume Analysis
print("\n" + "=" * 70)
print("VOLUME ANALYSIS")
print("=" * 70)
volume_cols = ['vol_1m', 'vol_5m', 'vol_15m', 'rvol_1m']
for col in volume_cols:
    if col in df.columns:
        valid = df[col].dropna()
        if len(valid) > 0:
            print(f"\n{col}:")
            print(f"  Min: {valid.min():,.2f}")
            print(f"  Max: {valid.max():,.2f}")
            print(f"  Mean: {valid.mean():,.2f}")

# Top 10 by Volume (15m)
print("\n" + "=" * 70)
print("TOP 10 BY VOLUME (15 minutes)")
print("=" * 70)
df_sorted_vol = df.sort_values('vol_15m', ascending=False)
for idx, row in df_sorted_vol.head(10).iterrows():
    print(f"{row['symbol']:15s}  Vol: {row['vol_15m']:15,.2f}  Price: ${row['last_price']:8.4f}")

# Open Interest Analysis
print("\n" + "=" * 70)
print("OPEN INTEREST ANALYSIS")
print("=" * 70)
oi_valid = df[df['open_interest'].notna()]
if len(oi_valid) > 0:
    print(f"\nTop 10 by Open Interest:")
    oi_sorted = oi_valid.sort_values('open_interest', ascending=False)
    for idx, row in oi_sorted.head(10).iterrows():
        oi_millions = row['open_interest'] / 1e6
        print(f"{row['symbol']:15s}  OI: ${oi_millions:10.2f}M  Price: ${row['last_price']:8.4f}")

# Funding Rate Analysis (if available)
funding_df = df[df['funding_rate'].notna()]
if len(funding_df) > 0:
    print("\n" + "=" * 70)
    print("FUNDING RATE ANALYSIS")
    print("=" * 70)
    print(f"Pairs with funding data: {len(funding_df)}")
    print(f"\nFunding Rate:")
    print(f"  Min: {funding_df['funding_rate'].min()*100:.4f}%")
    print(f"  Max: {funding_df['funding_rate'].max()*100:.4f}%")
    print(f"  Mean: {funding_df['funding_rate'].mean()*100:.4f}%")

conn.close()

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
