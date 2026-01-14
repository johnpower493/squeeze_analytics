# Crypto Database Analysis Summary

**Analysis Date:** January 15, 2026  
**Database:** ohlc.sqlite3

---

## Executive Summary

This analysis provides a comprehensive overview of the cryptocurrency trading database, covering alerts, OHLC price data, market snapshots, market cap data, and trade plans.

---

## Database Structure Overview

The database contains **9 tables** with the following key data:

| Table | Records | Description |
|-------|---------|-------------|
| alerts | 17,031 | Trading alerts with signals and metrics |
| ohlc | 57,368 | Open-High-Low-Close price data |
| market_cap_cache | 237 | Market capitalization data |
| trade_plans | 17,031 | Trading plan entries |
| snapshot_cache | 2 | Real-time market snapshots |

---

## Key Findings

### 1. Alerts Analysis

**Total Alerts:** 17,031

**Signal Distribution (Last 100 Alerts):**
- SELL signals: 67% (67 alerts)
- BUY signals: 33% (33 alerts)

**Timeframe Distribution:**
- 4h timeframe: 66% of alerts
- 15m timeframe: 34% of alerts

**Exchange Distribution:**
- Binance: 61% of alerts
- Bybit: 39% of alerts

**Available Metrics (65 indicators):**
- Price indicators: last_price, change_1m, change_5m, change_15m, change_60m
- Technical indicators: RSI (14, 1h, 4h, 1d), MACD, Stochastic, MFI
- Volume metrics: vol_1m, vol_5m, vol_15m, rvol_1m
- Momentum indicators: impulse_score, momentum_score, signal_score
- Multi-timeframe analysis: mtf_bull_count, mtf_bear_count, mtf_summary
- Volatility: atr, volatility_percentile, vol_zscore_1m
- Market structure: market_cap, liquidity_rank, open_interest

### 2. OHLC Data Analysis

**Total Records:** 57,368 candles

**Most Tracked Pairs (Top 5):**
1. **1000PEPEUSDT** - 287 candles (15m interval)
   - Price range: $0.005709 - $0.006862
2. **ADAUSDT** - 287 candles (15m interval)
   - Price range: $0.3822 - $0.4262
3. **ASTERUSDT** - 287 candles (15m interval)
   - Price range: $0.6827 - $0.7860
4. **AVAXUSDT** - 287 candles (15m interval)
   - Price range: $13.445 - $14.915
5. **BCHUSDT** - 287 candles (15m interval)
   - Price range: $595.46 - $655.80

**Major Cryptocurrencies Tracked:**
- **BTCUSDT**: $90,241 - $97,606 (15m data)
- **ETHUSDT**: $3,076 - $3,389 (15m data)
- **BNBUSDT**: $896 - $952 (15m data)

### 3. Market Capitalization Analysis

**Total Tokens Tracked:** 237

**Top 10 Cryptocurrencies by Market Cap:**

| Rank | Symbol | Market Cap | Category |
|------|--------|------------|----------|
| 1 | BTC | $1,936.72B | Store of Value |
| 2 | ETH | $404.31B | Smart Contract |
| 3 | USDT | $186.82B | Stablecoin |
| 4 | BNB | $130.25B | Exchange Token |
| 5 | XRP | $129.62B | Payments |
| 6 | STETH | $29.99B | DeFi/Staking |
| 7 | TRX | $28.70B | Smart Contract |
| 8 | ADA | $15.15B | Smart Contract |
| 9 | FIGR_HELOC | $14.90B | Real Estate |
| 10 | XMR | $13.17B | Privacy |

### 4. Trade Plans Analysis

**Total Trade Plans:** 17,031

**Trade Plan Summary:**

| Side | Entry Type | Count | Avg RR TP1 | Avg RR TP2 | Avg RR TP3 |
|------|------------|-------|------------|------------|------------|
| BUY | market | 4,037 | 1.0x | 2.0x | 3.0x |
| SELL | market | 12,994 | 1.0x | 2.0x | 3.0x |

**Observations:**
- SELL signals outnumber BUY signals by ~3.2:1 ratio
- All trades use market entry type
- Consistent risk-reward ratios across all trades (1:2:3)
- SELL trades have higher activity volume

**Top 10 Symbols by Trade Plan Count:**

| Symbol | Plan Count | Avg RR TP1 |
|--------|------------|------------|
| FARTCOINUSDT | 1,134 | 1.0x |
| 1000PEPEUSDT | 1,024 | 1.0x |
| DOGEUSDT | 972 | 1.0x |
| ASTERUSDT | 966 | 1.0x |
| AXSUSDT | 939 | 1.0x |
| IPUSDT | 913 | 1.0x |
| BCHUSDT | 816 | 1.0x |
| BERAUSDT | 762 | 1.0x |
| ZENUSDT | 751 | 1.0x |
| BTCUSDT | 746 | 1.0x |

**High-Volume Trading Symbols:**
- Meme coins (FARTCOIN, PEPE, DOGE) have highest alert frequency
- Major assets (BTC, BCH) also well-represented
- Suggests both speculative and fundamental trading approaches

### 5. Market Snapshots

**Available Snapshots:** 2
- Binance snapshot (30 pairs)
- Bybit snapshot (30 pairs)

**Snapshot Timestamps:**
- Binance: 2026-01-15 10:04:50
- Bybit: 2026-01-15 10:04:52

---

## Technical Insights

### Alert System Characteristics

1. **Multi-Timeframe Analysis**
   - System monitors both 15m and 4h timeframes
   - 4h timeframe generates 66% of alerts (swing trading focus)
   - 15m timeframe captures 34% of alerts (intraday opportunities)

2. **Technical Indicator Coverage**
   - **Momentum:** RSI, MACD, Stochastic across multiple timeframes
   - **Volume:** Real-time volume, relative volume, volume z-score
   - **Trend:** WaveTrend (wt1, wt2), multi-timeframe trend analysis
   - **Volatility:** ATR, volatility percentile
   - **Market Structure:** Liquidity rank, market cap, open interest

3. **Signal Strength Classification**
   - Strong buy/sell signals with scoring system
   - Multi-timeframe confirmation (bull/bear count)
   - Avoid reasons for filtering

### Risk Management

1. **Trade Plan Structure**
   - Consistent 1:2:3 risk-reward ratio
   - Market entry execution
   - Stop loss and three take profit levels

2. **Position Sizing**
   - ATR-based stop losses
   - Multiple ATR multipliers for different exit levels
   - Risk per unit calculations

---

## Data Quality Observations

### Strengths
- Comprehensive technical indicator coverage
- Multi-timeframe analysis
- Historical OHLC data available
- Market cap data for fundamental analysis
- Structured trade planning system

### Areas for Enhancement
1. **Alert Imbalance:** SELL signals significantly outnumber BUY signals (67:33)
2. **Backtesting:** No backtest results available (empty tables)
3. **Funding Rates:** No funding rate data in current snapshots
4. **Sector Coverage:** Only some assets have sector tags

---

## Recommendations

### 1. Strategy Optimization
- Investigate BUY signal generation - may be missing bullish opportunities
- Consider rebalancing timeframe allocation if 4h is too dominant
- Analyze win rates for different timeframes

### 2. Data Collection
- Implement backtesting to validate strategies
- Expand sector tagging for better classification
- Add funding rate monitoring for futures trading insights

### 3. Risk Management
- Review risk-reward ratios - 1:2:3 may be too aggressive for some market conditions
- Consider dynamic R:R based on volatility
- Implement position sizing optimization

### 4. Monitoring
- Set up alerts for significant market cap changes
- Monitor liquidity rank shifts
- Track volume anomalies across tracked pairs

---

## Conclusion

The database represents a sophisticated crypto trading system with:
- **17,031 trading alerts** across multiple timeframes
- **57,368 OHLC candles** for technical analysis
- **237 cryptocurrencies** with market cap data
- **17,031 trade plans** with structured risk management

The system shows strong technical analysis capabilities but would benefit from:
1. Backtesting implementation
2. Balanced signal generation
3. Enhanced data collection for futures markets
4. Sector classification improvements

The high frequency of alerts on meme coins and altcoins suggests an opportunistic trading approach complemented by positions in major cryptocurrencies (BTC, ETH).

---

*Analysis generated automatically on January 15, 2026*
