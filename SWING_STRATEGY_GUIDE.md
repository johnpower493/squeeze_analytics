# 13-Day Swing Trading Strategy - Usage Guide

## Quick Start

### 1. Add to TradingView
1. Copy the code from `Swing_Trading_Strategy_13D.pine`
2. Open TradingView → Pine Script Editor
3. Paste and click "Add to Chart"
4. **IMPORTANT:** Set chart to **DAILY timeframe**

### 2. Recommended Markets
- ✅ **Liquid Equities** (SPY, QQQ, AAPL, MSFT, etc.)
- ✅ **Futures** (ES, NQ, CL, GC)
- ✅ **Crypto** (BTC, ETH on major exchanges)
- ❌ Avoid low-volume stocks/assets

---

## Strategy Overview

### Core Concept
**Trade pullbacks in trending markets with strict risk management**

| Component | Description |
|-----------|-------------|
| **Timeframe** | Daily only |
| **Holding Period** | Up to 13 days (exit rules may close earlier) |
| **Entry** | Pullback into EMA zone + momentum breakout |
| **Exit** | 2R target, stop loss, or time-based exit |
| **Risk** | 1% per trade (adjustable) |

---

## How It Works

### 1. Market Regime Detection

**📈 TRENDING UP (Long Trades):**
- 20 EMA > 50 EMA
- 50 EMA slope is positive (rising)

**📉 TRENDING DOWN (Short Trades):**
- 20 EMA < 50 EMA  
- 50 EMA slope is negative (falling)

**↔ RANGING (No Trades):**
- Neither condition met
- No trades taken in ranging markets

---

### 2. Long Entry Process

**Step 1: Confirm Trending Up Market**
- 20 EMA above 50 EMA
- 50 EMA rising

**Step 2: Wait for Pullback**
- Price pulls back INTO the zone between 20 EMA and 50 EMA
- Strategy tracks the lowest low during pullback

**Step 3: Check Volatility**
- ATR must be decreasing over last 3 bars
- Shows market is calming down (consolidation)

**Step 4: Entry Trigger**
- Bullish close above prior day's high
- Shows momentum resuming

**Visual:**
```
Price Action:
    ↗ ↗ ↗ (trending up)
         ↘ ↘ (pullback into EMA zone)
              ↗ ← ENTRY (breakout above prior high)
```

---

### 3. Short Entry Process

Same as long but inverted:
1. Trending Down market (20 EMA < 50 EMA)
2. Pullback UP into EMA zone
3. ATR decreasing (reduced volatility)
4. Bearish close below prior day's low

---

### 4. Risk Management

**Position Sizing:**
- Risk = 1% of account equity per trade (adjustable)
- Position size automatically calculated based on stop distance

**Stop Loss:**
- **Long:** Below the pullback low
- **Short:** Above the pullback high

**Take Profit:**
- Default: 2R (risk 1%, target 2%)
- Adjustable R-multiple

**Example:**
```
Entry: $100
Stop: $98 (risk = $2)
Target: $104 (reward = $4, R = 2.0)

With $10,000 account and 1% risk:
Account risk = $100
Position size = $100 / $2 = 50 shares
```

---

### 5. Advanced Features

**🎯 Trailing Stop (Optional)**
- Activates after achieving 1R profit
- Trails based on ATR (default 2x ATR)
- Protects profits while allowing trends to run

**⏱ Time-Based Exit**
- If profit < 0.5R after 3 days → Exit at market
- Prevents dead money in non-performing trades
- Keeps capital active

**🔇 Volatility Filter**
- No trades when ATR < 20-period ATR average
- Avoids low-volatility, choppy conditions

---

## Settings Explained

### EMA Settings
| Setting | Default | Purpose |
|---------|---------|---------|
| Fast EMA | 20 | Short-term trend |
| Slow EMA | 50 | Long-term trend |

**Tip:** Don't change these unless backtesting shows better results

---

### ATR & Volatility
| Setting | Default | Purpose |
|---------|---------|---------|
| ATR Length | 14 | Standard ATR calculation |
| ATR SMA Length | 20 | Volatility filter baseline |
| Use Volatility Filter | ✓ ON | Skip low-volatility periods |

**Tip:** Disable volatility filter in crypto (often helpful)

---

### Risk Management
| Setting | Default | Notes |
|---------|---------|-------|
| Risk Per Trade | 1% | Conservative; can increase to 2% |
| Take Profit R-Multiple | 2.0 | Target 2x your risk |
| Trailing Stop | ✓ ON | Recommended for trending moves |
| Trailing ATR Mult | 2.0 | Distance of trailing stop |

**Conservative:** 1% risk, 2R target  
**Aggressive:** 2% risk, 3R target, trailing stop

---

### Time-Based Exit
| Setting | Default | Purpose |
|---------|---------|---------|
| Exit After X Bars | 3 | Days to wait |
| Min Progress | 0.5R | Required progress to stay in |

**Logic:** If trade hasn't moved 0.5R in 3 days, something's wrong → exit

---

### Trade Execution
| Setting | Default | Notes |
|---------|---------|-------|
| Slippage | 2 ticks | Adjust for market liquidity |
| Commission | 0.1% | Adjust for your broker |
| Trade Direction | Both | Can limit to Long or Short only |

---

## Visual Indicators

### On Chart
| Element | Color | Meaning |
|---------|-------|---------|
| **Blue Line** | Blue | 20 EMA (fast) |
| **Orange Line** | Orange | 50 EMA (slow) |
| **Shaded Zone** | Green/Red | Entry zone between EMAs |
| **▲ Triangle Up** | Green | Long entry |
| **▼ Triangle Down** | Red | Short entry |
| **Red Line** | Red | Stop loss level |
| **Green Line** | Green | Take profit level |
| **◆ Diamonds** | Light | Pullback lows/highs being tracked |

### Info Table (Top Right)
Shows real-time status:
- Market regime
- EMA values
- ATR trend
- Volatility status
- Current position
- R achieved
- Bars in trade

---

## Example Trade Walkthrough

### Long Trade Example (SPY)

**Day 1-10:** SPY trending up
- 20 EMA > 50 EMA ✓
- 50 EMA rising ✓
- **Regime:** 📈 TRENDING UP

**Day 11-12:** Pullback occurs
- Price drops into EMA zone
- Low of pullback: $450
- ATR decreasing ✓

**Day 13:** Entry trigger
- Close: $452 (above prior high) ✓
- **ENTRY LONG @ $452**
- Stop: $450 (risk = $2)
- Target: $456 (reward = $4, R = 2.0)

**Day 14-16:** Trade develops
- Day 14: Up to $453 (0.5R) ✓
- Day 15: Up to $454 (1R) - Trailing stop activates
- Day 16: Hits $456 - **TAKE PROFIT @ 2R** ✓

**Result:** Risk $2, Gain $4 = **+2R trade**

---

### Time Exit Example

**Entry:** $100, Stop: $98, Target: $104

**Day 1:** $100.50 (0.25R)  
**Day 2:** $100.25 (0.125R)  
**Day 3:** $100.75 (0.375R)  

After 3 days, progress is only 0.375R (< 0.5R required)  
→ **TIME EXIT triggered** → Close at market

**Why?** Trade is going nowhere, capital better deployed elsewhere

---

## Backtest Checklist

### Before Running Backtest

- [ ] Chart on **Daily timeframe**
- [ ] Liquid market selected
- [ ] Commission/slippage set for your broker
- [ ] Date range: Minimum 1 year
- [ ] Initial capital matches your account

### Analyzing Results

**Minimum Standards:**
| Metric | Good | Excellent |
|--------|------|-----------|
| Win Rate | >40% | >50% |
| Profit Factor | >1.5 | >2.0 |
| Max Drawdown | <20% | <15% |
| Avg R | >0.5R | >1.0R |
| Total Trades | >30 | >50 |

**Red Flags:**
- Win rate <35%
- Profit factor <1.2
- Max drawdown >25%
- Long streaks of losses (>5)

---

## Optimization Tips

### If Win Rate Too Low (<40%)
- Increase minimum R target (2.0 → 2.5)
- Make volatility filter stricter
- Add minimum ATR requirement

### If Too Few Trades
- Reduce fast EMA (20 → 15)
- Disable volatility filter
- Try "Long Only" on bullish markets

### If Too Many Losers
- Increase ATR decrease requirement (3 bars → 4 bars)
- Add pullback depth filter (must pull back at least 50% into zone)

### If Drawdown Too High
- Reduce risk per trade (1% → 0.5%)
- Enable trailing stop if disabled
- Add correlation filters (don't trade SPY and QQQ simultaneously)

---

## Common Issues

### "No trades showing"
**Causes:**
1. Wrong timeframe (must be Daily)
2. Market is ranging (not trending)
3. Volatility filter blocking trades
4. No pullbacks occurring

**Fix:** Check info table shows "TRENDING UP/DOWN", disable volatility filter temporarily

---

### "Too many losing trades"
**Causes:**
1. Market is choppy/whipsawing
2. EMAs too close together
3. Not enough confirmation

**Fix:** Increase EMA separation, add filters

---

### "Trades exit too early"
**Causes:**
1. Time-based exit too aggressive
2. Stop loss too tight
3. Trailing stop activating too soon

**Fix:** Increase exit bars (3 → 5), increase trailing ATR multiplier

---

## Advanced: Parameter Optimization

### Conservative (Lower risk, higher win rate)
```
Risk: 0.5%
R Target: 2.5
Trailing Stop: ON
Trailing ATR: 3.0
Exit Bars: 5
Min Progress: 0.3R
```

### Aggressive (Higher risk, bigger winners)
```
Risk: 2%
R Target: 3.0
Trailing Stop: ON
Trailing ATR: 1.5
Exit Bars: 2
Min Progress: 0.7R
```

### Trend Following (Let winners run)
```
Risk: 1%
R Target: 4.0
Trailing Stop: ON
Trailing ATR: 2.5
Exit Bars: 7
Min Progress: 0.3R
```

---

## Multi-Market Portfolio Approach

**Diversification Strategy:**
1. Run on 5-10 uncorrelated markets
2. Use 0.5% risk per market
3. Maximum 3 open positions at once

**Example Portfolio:**
- Equities: SPY, QQQ
- Commodities: GC, CL
- Forex: EURUSD, GBPUSD
- Crypto: BTC, ETH

**Benefits:**
- Smoother equity curve
- Less correlation risk
- Always opportunities somewhere

---

## Key Takeaways

✅ **DO:**
- Use on Daily timeframe only
- Trade liquid markets
- Let the system work (don't override)
- Track stats over 30+ trades
- Test before going live

❌ **DON'T:**
- Use on intraday timeframes
- Trade illiquid assets
- Override signals manually
- Judge on 5-10 trades
- Skip backtesting

---

## Next Steps

1. **Backtest on your preferred markets** (1-2 years)
2. **Analyze the statistics** (win rate, profit factor, etc.)
3. **Optimize settings** if needed (but don't overfit!)
4. **Paper trade** for 1-2 months
5. **Go live** with small position sizes
6. **Scale up** after proving consistency

---

## Support

If the strategy isn't working:
1. Check the info table for regime status
2. Verify you're on Daily timeframe
3. Review last 5-10 trades manually
4. Compare to examples in this guide

**Good luck and trade safely!** 📈
