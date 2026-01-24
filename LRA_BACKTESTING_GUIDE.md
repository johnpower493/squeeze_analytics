# LRA Backtesting Guide - Step-by-Step

## Overview

Since the LRA indicator now shows **historical locked ranges**, you can manually backtest by scrolling through historical data and analyzing past ranges. Pine Script indicators cannot be directly backtested with TradingView's Strategy Tester, so this guide shows you how to do systematic manual backtesting.

---

## Method 1: Manual Visual Backtesting (Recommended)

### Step 1: Load the Indicator

1. Open TradingView
2. Load the chart you want to test (e.g., EUR/USD, ES, GC)
3. Click "Indicators" → "My scripts" → Load **`LRA_PineScript_Optimized.pine`**
4. Set timeframe to **1H or 4H** (recommended per book)

---

### Step 2: Configure Settings for Backtesting

**Optimal backtest settings:**
```
[Range Detection]
Swing High/Low Length: 3-5
Minimum Bars in Range: 5-8
ATR Multiple for Range Height: 1.5
Maximum Bars in Range: 100
Breakout Threshold %: 0.5

[TPSL Levels]
TPSL 1 Method: Auto
Show TPSL 2 Levels: ✓ YES

[Visual]
Show Locked Ranges: ✓ YES
Show TPSL 1 Levels: ✓ YES
Show TPSL 2 Levels: ✓ YES
Show Imbalance Arrows: ✓ YES
Max Historical Ranges to Display: 20-30
Show Breakout Labels: ✓ YES

[Colors]
Historical Range Transparency: 85%
```

---

### Step 3: Navigate to Historical Data

**Option A: Bar Replay (Best for learning)**
1. Right-click on chart → "Bar Replay"
2. Select start date (e.g., 6 months ago)
3. Use playback controls to step through bar-by-bar
4. **Advantage:** See ranges form in real-time, see your decisions
5. **Disadvantage:** Time-consuming

**Option B: Manual Scrolling (Faster)**
1. Scroll left to historical data (e.g., 3-6 months ago)
2. Move forward chunk by chunk
3. **Advantage:** Faster, can skip boring periods
4. **Disadvantage:** Less realistic

---

### Step 4: Create a Tracking Spreadsheet

Download template or create your own:

| Trade # | Date | Pair | Range Type | Imbalance | Entry | Stop | TP1 | TP2 | Exit | P/L | R:R | Notes |
|---------|------|------|------------|-----------|-------|------|-----|-----|------|-----|-----|-------|
| 1 | 2024-10-15 | EURUSD | Resistance | +16.2% | 1.0850 | 1.0900 | 1.0800 | 1.0750 | 1.0795 | +55 pips | 1:1.1 | Hit TP1 partial |
| 2 | 2024-10-18 | ES | Support | -18.5% | 4325 | 4315 | 4340 | 4355 | 4342 | +17 pts | 1:1.7 | Hit TP2, stopped at BE |

**Columns explained:**
- **Range Type:** Resistance / Support / Gravitation
- **Imbalance:** % shown on label
- **Entry:** Your entry price
- **Stop:** Your stop loss
- **TP1/TP2:** TPSL 1 and TPSL 2 levels
- **Exit:** Where you actually exited
- **P/L:** Profit or loss in pips/points
- **R:R:** Actual risk:reward ratio achieved
- **Notes:** What happened, lessons learned

---

### Step 5: Trade Identification Process

**For each historical locked range you see (dashed boxes):**

#### A. Identify the Setup

```
1. Is there a locked range visible (dashed box)?
   → If NO: Move forward, look for next range
   → If YES: Continue to step 2

2. What type is it?
   → Check label: Resistance / Support / Gravitation
   → Check imbalance: Is it >15%? (higher confidence)
   → Check color: Green/Red/Gray

3. Is there a breakout?
   → Look for breakout label: ▲ UP or ▼ DOWN
   → Check if breakout aligns with expectation:
      - Resistance should break DOWN
      - Support should break UP
      - Gravitation can break either way (fade it)
```

#### B. Would You Have Taken This Trade?

**Quality filters (only take trades that pass ALL):**

✅ **Filter 1: Imbalance Strength**
- Resistance/Support: Imbalance >15% (REQUIRED)
- Gravitation: Imbalance <5% (REQUIRED)

✅ **Filter 2: Clean Breakout**
- Breakout label present
- Bar closes beyond range boundary
- Volume increase visible (check volume histogram)

✅ **Filter 3: Historical Context**
- Check other historical ranges (dashed boxes)
- Are previous ranges in same direction? (confluence = good)
- Any old ranges acting as support/resistance? (check)

✅ **Filter 4: Session Timing** (if tracking time)
- Currency pairs: Avoid American session entries
- Indices: American session preferred
- Commodities: Depends on type

✅ **Filter 5: No Immediate Cancellation**
- Price doesn't return >70% into range immediately
- Breakout has momentum

---

#### C. Record the Trade

**Entry point:**
```
Resistance LR: Enter SHORT on first pullback to LR Low boundary
Support LR: Enter LONG on first pullback to LR High boundary
Gravitation LR: Enter when price extends 1× range height beyond boundary
```

**Example:**
```
Range: 1.1800 - 1.1850 (50 pips) - Support LR, -17.3%
Breakout: UP to 1.1862 (▲ UP label appears)
Pullback: Returns to 1.1852
Entry: 1.1852 LONG ✓ (record in spreadsheet)
Stop: 1.1795 (below 1.1800 - 5 pip buffer)
TP1: 1.1890 (TPSL 1 High - dashed green line)
TP2: 1.1920 (TPSL 2 High - dotted green line)
```

**Track the outcome:**
- Scroll forward to see what happened
- Mark where price hit TP1, TP2, or stop
- Calculate P/L and R:R
- Add notes: "Clean breakout, hit TP1 in 8 hours"

---

### Step 6: Repeat for Multiple Ranges

**Goal:** Test at least 30-50 trades for statistical significance

**Process:**
1. Scroll forward to next historical range
2. Identify setup (steps A-B above)
3. Record if you'd take it (step C)
4. Track outcome
5. Repeat

**Time estimate:**
- 1-2 hours per 10 trades (detailed analysis)
- 3-4 hours for 30 trades
- 6-8 hours for 50 trades

---

## Method 2: Automated Data Export (Advanced)

### Convert Indicator to Strategy

Since you can't directly backtest an indicator, you need to convert it to a strategy script.

**I can create a strategy version that:**
1. Automatically enters trades on breakouts
2. Manages stop loss and take profits
3. Logs all trades to Strategy Tester
4. Generates performance reports

**Pros:**
- Automated backtesting
- Exact statistics
- Fast (test years in seconds)

**Cons:**
- Less realistic (no discretion, follows rules blindly)
- May not capture pullback entries perfectly
- Requires more complex code

**Would you like me to create the strategy version?** It's a significant modification but gives you proper automated backtesting.

---

## Method 3: Hybrid Approach (Best of Both Worlds)

### Step 1: Use Strategy for Initial Filter

I can create a **simple strategy** that:
- Marks all valid range breakouts
- Shows where entries would be
- Tracks basic statistics

### Step 2: Manual Review of Signals

You then:
- Review each signal visually
- Decide if you'd really take it (discretion)
- Track only the ones you approve
- Compare your discretionary results vs. pure algo

**This combines automation speed with human judgment**

---

## Backtesting Analysis Framework

### Metrics to Track

#### 1. Win Rate by Range Type

```
Resistance LR:
- Trades taken: 15
- Winners: 11
- Losers: 4
- Win rate: 73.3%

Support LR:
- Trades taken: 18
- Winners: 13
- Losers: 5
- Win rate: 72.2%

Gravitation LR:
- Trades taken: 8
- Winners: 5
- Losers: 3
- Win rate: 62.5%
```

#### 2. Average Risk:Reward by Type

```
Resistance LR:
- Average R:R: 1:2.1
- Best: 1:3.5
- Worst: 1:0.4

Support LR:
- Average R:R: 1:2.3
- Best: 1:3.8
- Worst: 1:0.3

Gravitation LR:
- Average R:R: 1:1.2
- Best: 1:1.8
- Worst: 1:0.6
```

#### 3. Success by Imbalance Strength

```
Imbalance > 20%:
- Win rate: 82%
- Average R:R: 1:2.7

Imbalance 15-20%:
- Win rate: 71%
- Average R:R: 1:2.1

Imbalance 10-15%:
- Win rate: 58%
- Average R:R: 1:1.8

Imbalance < 10% (Gravitation):
- Win rate: 63%
- Average R:R: 1:1.1
```

**Conclusion example:** "Only take trades with >15% imbalance"

#### 4. Target Hit Rates

```
TPSL 1 Hit Rate:
- Resistance LR: 78%
- Support LR: 75%
- Gravitation LR: 68%

TPSL 2 Hit Rate:
- Resistance LR: 42%
- Support LR: 45%
- Gravitation LR: 31%
```

**Conclusion example:** "Scale out 50% at TPSL 1, 30% at TPSL 2"

#### 5. Time to Target

```
TPSL 1 Average Time:
- 1H chart: 8-12 bars (8-12 hours)
- 4H chart: 3-6 bars (12-24 hours)

TPSL 2 Average Time:
- 1H chart: 18-30 bars (18-30 hours)
- 4H chart: 8-15 bars (32-60 hours)
```

**Conclusion example:** "Give trades at least 24 hours to develop"

---

## Sample Backtest Report Template

```
═══════════════════════════════════════════════════════
LRA BACKTEST REPORT
═══════════════════════════════════════════════════════

Instrument: EUR/USD
Timeframe: 4H
Period: Jan 1, 2024 - Jun 30, 2024 (6 months)
Total Bars: ~1,095

RANGE STATISTICS:
─────────────────────────────────────────────────────
Total Ranges Formed: 47
- Resistance LR: 18 (38%)
- Support LR: 21 (45%)
- Gravitation LR: 8 (17%)

Ranges Traded: 32 (filtered out 15 low-quality)
- Imbalance < 15%: 10 excluded
- Poor breakout: 3 excluded
- Bad timing: 2 excluded

TRADE RESULTS:
─────────────────────────────────────────────────────
Total Trades: 32
Winners: 23
Losers: 9
Win Rate: 71.9%

Profit Factor: 2.4
Average R:R: 1:2.1
Expectancy: +0.51R per trade

Total Return: +67.2R (risk units)
With 1% risk per trade: +67.2% account growth

BREAKDOWN BY TYPE:
─────────────────────────────────────────────────────
Resistance LR (13 trades):
- Win rate: 76.9% (10W / 3L)
- Avg R:R: 1:2.3
- Contribution: +31.2R

Support LR (15 trades):
- Win rate: 73.3% (11W / 4L)
- Avg R:R: 1:2.0
- Contribution: +28.8R

Gravitation LR (4 trades):
- Win rate: 50.0% (2W / 2L)
- Avg R:R: 1:1.3
- Contribution: +7.2R

BEST PRACTICES IDENTIFIED:
─────────────────────────────────────────────────────
✓ Imbalance >18%: 85% win rate
✓ Wait for pullback entry: +0.3R avg improvement
✓ Avoid American session entries: +15% win rate
✓ Scale exits 50/30/20: +0.5R improvement vs full exit
✓ Respect range cancellation: Saved 5 losing trades

IMPROVEMENTS NEEDED:
─────────────────────────────────────────────────────
⚠ Gravitation trades underperforming - reduce allocation
⚠ 3 trades stopped out due to news events - check calendar
⚠ Range detection too sensitive - increase min bars to 8

CONCLUSION:
─────────────────────────────────────────────────────
Strategy is viable with proper filters:
- 72% win rate is excellent
- 2.4 profit factor is strong
- Risk 1% per trade for 67% in 6 months
- Focus on Resistance/Support LRs with >15% imbalance
```

---

## Quick Start: Your First Backtest Session

### 30-Minute Quick Test

**Goal:** Test 10 trades to get a feel for the system

**Steps:**
1. Load indicator on EUR/USD 4H chart
2. Scroll back 3 months
3. Find first historical range (dashed box)
4. Check: Type? Imbalance? Breakout?
5. If quality setup: Record entry, stop, targets
6. Scroll forward: See outcome
7. Calculate P/L and R:R
8. Repeat for 9 more ranges
9. Calculate basic stats: Win rate, avg R:R
10. Decide: Worth deeper testing?

**Expected results after 10 trades:**
- If win rate >65%: Continue testing ✓
- If R:R averaging >1:1.5: Promising ✓
- If <60% or <1:1: Adjust parameters or filters

---

## Common Backtesting Pitfalls

### ❌ Pitfall #1: Hindsight Bias
**Problem:** "I would have seen that obvious resistance!"  
**Solution:** Only use information available BEFORE the trade  
**Rule:** Don't look right at the outcome before recording entry

### ❌ Pitfall #2: Cherry Picking
**Problem:** Only testing ranges that "look good"  
**Solution:** Test EVERY range that meets your filters  
**Rule:** Can't skip a trade just because it looks like a loser

### ❌ Pitfall #3: Overfitting
**Problem:** "If I use 3.7 for swing length, win rate is 85%!"  
**Solution:** Use round, logical numbers (3, 5, 10, 20)  
**Rule:** If parameters are oddly specific, you're curve-fitting

### ❌ Pitfall #4: Ignoring Costs
**Problem:** Not accounting for spreads, commissions, slippage  
**Solution:** Deduct realistic costs from each trade  
**Rule:** Assume 1-2 pips slippage on entries/exits

### ❌ Pitfall #5: Small Sample Size
**Problem:** "I tested 8 trades, 7 won, this is amazing!"  
**Solution:** Need minimum 30 trades for basic confidence  
**Rule:** 50+ trades for reliable statistics

### ❌ Pitfall #6: Not Testing Losses
**Problem:** Focusing only on winners  
**Solution:** Analyze WHY losers happened  
**Rule:** Learn more from losses than wins

---

## Next Steps After Backtesting

### If Results Are Positive (>65% win rate, >1:1.5 R:R):

1. **Forward Test** on demo account
   - Trade real-time with fake money
   - Ensure you can execute the system live
   - Test for 1-2 months

2. **Paper Trade** manually
   - Record trades in journal
   - Don't actually place orders
   - Verify emotions don't interfere

3. **Start Small** on live account
   - Risk 0.5% per trade (half normal)
   - Trade for 20-30 trades
   - Gradually increase to 1% risk

### If Results Are Negative (<60% win rate, <1:1 R:R):

1. **Adjust Filters**
   - Increase min imbalance to 18% or 20%
   - Add confluence requirements
   - Tighten entry rules

2. **Test Different Instruments**
   - Currency pairs may work better than indices
   - Or vice versa
   - Each instrument has personality

3. **Adjust Timeframes**
   - Try 2H or 6H instead of 4H
   - Higher timeframe = less noise

4. **Revisit the Book**
   - Re-read chapters 2.4 and 2.5
   - May have missed a nuance

---

## FAQ

**Q: How many trades do I need to test?**  
A: Minimum 30, ideally 50-100 for confidence

**Q: Can I backtest on different timeframes?**  
A: Yes, but 1H-4H is recommended per the book

**Q: Should I test multiple instruments?**  
A: Yes! Each behaves differently. Test your main trading instruments

**Q: How far back should I test?**  
A: 6-12 months is good. More is better but diminishing returns

**Q: What if my results don't match the book's expectations?**  
A: Parameters may need tuning. Try stricter filters first (higher imbalance threshold)

**Q: Can I skip the manual backtesting and go straight to live?**  
A: ❌ NO! You'll lose money. You must verify the system works for YOU first

**Q: Should I test on different market conditions?**  
A: YES! Test trending periods AND ranging periods separately

---

## Tools & Resources

**Spreadsheet Template:**
- Google Sheets: (Create your own using table above)
- Excel: Same structure

**TradingView Features to Use:**
- Bar Replay (right-click chart)
- Drawing tools (mark entries/exits)
- Alerts (practice setting them)

**Optional Advanced Tools:**
- Trading journal software (Edgewonk, TraderSync)
- R programming for statistical analysis
- Python + pandas for trade log analysis

---

## Would You Like Me To...?

1. **Create an automated strategy version** of the indicator for full backtesting in Strategy Tester?
   - Pros: Fast, exact statistics, test years of data
   - Cons: Takes time to build, less realistic (no discretion)

2. **Create a detailed spreadsheet template** with formulas for automatic calculations?
   - Win rate auto-calc
   - R:R auto-calc
   - Performance charts

3. **Show you a live example** of analyzing a specific historical range?
   - Walk through one complete trade analysis
   - Show exactly what to look for

**Let me know which would be most helpful!** 📊