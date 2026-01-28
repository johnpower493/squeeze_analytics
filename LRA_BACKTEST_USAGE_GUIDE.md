# LRA Backtest Strategy - Usage Guide

## Quick Start

### 1. Add to TradingView
1. Copy `LRA_Backtest_Strategy.pine` code
2. Open TradingView → Pine Script Editor
3. Paste and click "Add to Chart"

### 2. Recommended Initial Settings

| Setting | Value | Why |
|---------|-------|-----|
| **Timeframe** | 1H or 4H | Per book Chapter 2.3 |
| **Symbol** | EURUSD, ES, GC | High liquidity futures |
| **Date Range** | Last 6-12 months | Sufficient data |
| **Min Bars in Range** | 5-8 | Balance sensitivity |
| **Min Imbalance %** | 10-15% | Filter weak signals |
| **Entry Method** | Breakout | Most conservative |

---

## Debug Indicators (New!)

The strategy now shows visual markers to help you understand what's happening:

| Marker | Location | Meaning |
|--------|----------|---------|
| 🔵 Blue Circle | Bottom | LR range activated |
| ▲ Green Triangle | Below bar | Breakout UP detected |
| ▼ Red Triangle | Above bar | Breakout DOWN detected |
| 💎 Yellow Diamond | Top | Historical box drawn |

**If you don't see ANY blue circles** → No ranges are being detected at all

---

## Troubleshooting: No Ranges Detected

### Check 1: Statistics Table
Look at the top-right table. Does "Total Ranges" show 0?

**If YES** → Try these adjustments:

| Current Setting | Change To | Effect |
|----------------|-----------|---------|
| Min Bars in Range: 8 | **5** | Detect smaller consolidations |
| Narrow Range ATR Mult: 0.8 | **1.2** | More tolerant of volatility |
| Min Imbalance %: 15 | **10** | Accept weaker imbalances |
| Require HTF Confirmation: ON | **OFF** | Don't filter by higher TF |

### Check 2: Timeframe
- Too low (1m, 5m) → Not enough consolidation
- Too high (Daily) → Very rare ranges
- **Sweet spot: 1H or 4H**

### Check 3: Symbol Volatility
Some symbols consolidate more than others:

| More Consolidation | Less Consolidation |
|-------------------|-------------------|
| EURUSD | BTCUSD |
| Gold (GC) | Natural Gas |
| E-mini S&P 500 | Small-cap stocks |

---

## Understanding the Boxes

### Current Active Range (Dashed Border)
- Updates in real-time as range forms
- Color indicates type:
  - 🔴 Red = Resistance (buyers trapped)
  - 🟢 Green = Support (sellers trapped)
  - ⚪ Gray = Gravitation (balanced)

### Historical Ranges (Solid Border)
- Created when breakout occurs
- Shows completed ranges
- Label includes:
  - Range type
  - TOI (volume degree)
  - Breakout direction (▲ or ▼)

---

## Key Statistics to Monitor

### 1. Prediction Accuracy
**Most Important Metric!**

Per the book's methodology:
- **Resistance LR** should break DOWN
- **Support LR** should break UP

| Metric | Good | Excellent | Notes |
|--------|------|-----------|-------|
| Resistance Correct | >50% | >60% | Buyers trapped → expect down |
| Support Correct | >50% | >60% | Sellers trapped → expect up |
| Overall Directional | >50% | >60% | Combined accuracy |

**If accuracy is <50%** → The LRA methodology isn't working for this symbol/timeframe

### 2. TOI Analysis
Tests if higher volume = better signals:

| TOI Level | Expected Win Rate |
|-----------|------------------|
| High | Highest |
| Medium | Middle |
| Low | Lowest |

**If High TOI < Low TOI** → Volume degree not predictive for this market

### 3. Strategy Performance

| Metric | Meaning |
|--------|---------|
| Win Rate | % of profitable trades |
| Profit Factor | Gross Profit ÷ Gross Loss (>1 = profitable) |
| Max Drawdown | Largest peak-to-trough decline |
| Total Trades | Sample size (need >30 for validity) |

---

## Entry Methods Explained

### 1. Breakout (Recommended)
**When:** Price closes beyond range boundary

**Pros:**
- Waits for confirmation
- Lower false signals
- Trades with momentum

**Cons:**
- Later entry (less profit potential)
- May miss best entry

**Best For:** Conservative traders, validation testing

---

### 2. Immediate
**When:** As soon as LR type is identified

**Pros:**
- Earliest entry
- Maximum profit potential
- Purely predictive

**Cons:**
- No confirmation
- Higher false signals
- Requires strong imbalance

**Best For:** Aggressive traders, strong signals only

---

## Filters and Their Impact

### Minimum TOI Filter

| Setting | Effect on Trades | Effect on Win Rate |
|---------|-----------------|-------------------|
| Any | Most trades | May include weak signals |
| Medium | Moderate trades | Better quality |
| High | Fewer trades | Best quality (theoretically) |

**Recommendation:** Start with "Medium", adjust based on results

### Only Directional LR

| Enabled | Effect |
|---------|--------|
| ✓ ON | Skips Gravitation ranges, only trades Resistance/Support |
| ✗ OFF | Trades all range types |

**Recommendation:** Enable if Gravitation ranges have low win rate

### HTF Confirmation

| Enabled | Effect |
|---------|--------|
| ✓ ON | Only detects ranges when higher timeframe is consolidating |
| ✗ OFF | Detects ranges regardless of HTF |

**Recommendation:** Enable if getting too many false ranges during strong HTF trends

---

## Example Backtest Workflow

### Step 1: Initial Test (Validation)
**Goal:** Does LRA work for this market?

**Settings:**
- Entry Method: Breakout
- Filters: Minimal (Min TOI: Any, Only Directional: OFF)
- Date Range: 12 months

**Success Criteria:**
- Overall Directional Accuracy >50%
- Total Ranges >20 (sufficient sample)

**If Failed:** LRA may not be suitable for this symbol/timeframe

---

### Step 2: Optimization
**Goal:** Find best settings

**Test Variations:**
- Min Imbalance: 10%, 15%, 20%
- Min TOI: Any, Medium, High
- Entry Method: Breakout vs Immediate

**Compare:** Win Rate and Profit Factor

---

### Step 3: Final Validation
**Goal:** Confirm settings on new data

**Method:**
- Use optimized settings
- Test on different date range (out-of-sample)
- Compare results to initial test

**If Similar:** Settings are robust
**If Worse:** May be overfit

---

## Interpreting Results

### Scenario 1: High Accuracy, Low Profit
**Meaning:** LRA predictions are correct, but:
- Take-profits too small
- Stop-loss too tight
- Entry timing poor

**Fix:** Adjust TPSL levels or entry method

---

### Scenario 2: Low Accuracy, No Pattern
**Meaning:** LRA doesn't work for this market

**Possible Reasons:**
- Market is algorithmic (doesn't trap traders)
- Low liquidity (no real market maker)
- Crypto (different dynamics)

**Fix:** Try different symbol or timeframe

---

### Scenario 3: Good Resistance, Bad Support (or vice versa)
**Meaning:** Market has directional bias

**Fix:** 
- Trade Direction: Change to "Long Only" or "Short Only"
- Focus on the working side

---

### Scenario 4: TOI Shows No Difference
**Meaning:** Volume degree doesn't matter for this market

**Fix:** Ignore TOI filter, focus on imbalance percentage instead

---

## Advanced: Comparing Book Examples

Test these exact examples from the book (Chapter 2.5):

### Euro FX (Figure 9.1)
- **Contract:** December 2017
- **Timeframe:** 1H
- **Date:** Nov 21 - Dec 5, 2017
- **Expected Range:** 1.18850-1.18500
- **Expected Type:** Resistance (Buy 1/3)
- **Expected Breakout:** DOWN

**Test:** Does your script detect this range and predict correctly?

---

### Japanese Yen (Figure 9.2)
- **Contract:** June 2017
- **Timeframe:** 1H
- **Date:** May 12-26, 2017
- **Expected Range:** 0.008960-0.008940
- **Expected Type:** Support (Sell 1/3)
- **Expected Breakout:** UP

---

### Gold (Figure 9.11)
- **Contract:** June 2017
- **Timeframe:** 1H
- **Date:** April 6-23, 2017
- **Expected Range:** 1289.0-1279.5
- **Expected Type:** Resistance (Buy 1/3)
- **Expected Breakout:** DOWN

---

## Common Issues

### Issue: Boxes appear then disappear
**Cause:** Only current box is showing, historical boxes not drawing
**Status:** Should be fixed in latest version

### Issue: No boxes at all
**Cause 1:** No ranges detected → Check settings
**Cause 2:** "Show Range Boxes" disabled → Enable in settings
**Cause 3:** Wrong timeframe → Use 1H or 4H

### Issue: Too many boxes/cluttered
**Fix:** Increase "Min Imbalance %" to filter weak signals

### Issue: Strategy not taking trades
**Causes:**
- Time filter enabled and outside window
- Trade direction filter limiting entries
- No ranges detected (check Total Ranges stat)

---

## Performance Benchmarks

Based on book methodology, realistic expectations:

| Metric | Conservative | Good | Excellent |
|--------|-------------|------|-----------|
| Win Rate | 45-50% | 50-60% | 60%+ |
| Profit Factor | 1.0-1.5 | 1.5-2.0 | 2.0+ |
| Directional Accuracy | 50-55% | 55-65% | 65%+ |
| Annual Return | 0-10% | 10-30% | 30%+ |

**Note:** Results vary significantly by:
- Symbol selection
- Parameter settings
- Market conditions
- Execution quality (slippage, commissions)

---

## Next Steps

1. **If backtests look good:**
   - Forward test on demo account
   - Paper trade for 1-2 months
   - Compare live results to backtest

2. **If backtests look bad:**
   - Try different symbols
   - Adjust parameters
   - Consider LRA may not suit your market

3. **For deeper analysis:**
   - Export trade list
   - Analyze by session time
   - Check correlation with volatility

---

## Support

For issues with the script:
1. Check debug indicators are showing
2. Verify settings match recommendations
3. Test on book examples first
4. Share statistics table for analysis

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-26 | Initial backtest strategy |
| 1.1 | 2026-01-26 | Fixed historical box visualization |
| 1.2 | 2026-01-26 | Added debug indicators, improved box drawing |

---

## References

- **Book:** Leksey, T. (2017). *Locked-in Range Analysis*
- **Indicator:** `LRA_PINE_IMPROVED.pine`
- **Validation Guide:** `LRA_VALIDATION_GUIDE.md`
