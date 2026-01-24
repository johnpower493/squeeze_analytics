# LRA Trading Guide - Understanding and Trading Locked Ranges

## Quick Reference Card

| Range Type | Market Maker Position | Trader Position | Expected Move | Win Rate Context |
|------------|----------------------|-----------------|---------------|------------------|
| **Resistance LR** 🟢 | Holds SELL positions | Majority LONG (buyers trapped) | **DOWN** ⬇️ | High probability short |
| **Support LR** 🔴 | Holds BUY positions | Majority SHORT (sellers trapped) | **UP** ⬆️ | High probability long |
| **Gravitation LR** ⚪ | Balanced positions | No clear majority | **Return to range** ↩️ | Mean reversion play |

---

## Understanding the Three Range Types

### 🟢 Resistance Locked Range (R-LR)

**What It Means:**
- **Buy positions prevail** in the range (bullish sentiment from traders)
- Imbalance > +10% (more volume at range high)
- Market makers accumulate SHORT positions as counterparty
- Label shows: "Resistance" with positive imbalance (e.g., "+15.3%")

**The Psychology:**
```
Most traders think: "Price is consolidating, ready to break UP!"
Reality: Market makers WANT to sell to all these buyers
Result: Price moves DOWN to lock in the buy positions at a loss
```

**What Actually Happened:**
1. Traders accumulated LONG positions at range boundaries
2. They placed stop-losses below the range
3. Market maker sees this via order book data
4. Market maker quotes price BELOW range to trigger stop-losses
5. Trapped buyers sell at a loss

**Visual on Chart:**
- Green/bullish colored box (but ironically bearish for outcome!)
- Imbalance arrow pointing DOWN (▼) if imbalance > 15%
- After breakout: Price drops, often reaching TPSL 1 Low or beyond

---

### 🔴 Support Locked Range (S-LR)

**What It Means:**
- **Sell positions prevail** in the range (bearish sentiment from traders)
- Imbalance < -10% (more volume at range low)
- Market makers accumulate LONG positions as counterparty
- Label shows: "Support" with negative imbalance (e.g., "-18.7%")

**The Psychology:**
```
Most traders think: "Price is consolidating, ready to break DOWN!"
Reality: Market makers WANT to buy from all these sellers
Result: Price moves UP to lock in the sell positions at a loss
```

**What Actually Happened:**
1. Traders accumulated SHORT positions at range boundaries
2. They placed stop-losses above the range
3. Market maker sees this via order book data
4. Market maker quotes price ABOVE range to trigger stop-losses
5. Trapped sellers cover at a loss

**Visual on Chart:**
- Red/bearish colored box (but ironically bullish for outcome!)
- Imbalance arrow pointing UP (▲) if imbalance > 15%
- After breakout: Price rises, often reaching TPSL 1 High or beyond

---

### ⚪ Gravitation Locked Range (G-LR)

**What It Means:**
- **No significant imbalance** between buyers and sellers
- Imbalance between -10% and +10%
- Market maker has balanced long/short positions
- Label shows: "Gravitation" with near-zero imbalance (e.g., "+2.1%")

**The Psychology:**
```
Market is uncertain - no clear sentiment
Traders on both sides waiting for direction
Result: Price may break out but tends to RETURN to range
```

**What Actually Happened:**
1. Equal distribution of long and short positions
2. No clear trapped majority to profit from
3. Market maker has no strong incentive to move price away
4. Price "gravitates" back to range after brief excursions

**Visual on Chart:**
- Gray/neutral colored box
- No imbalance arrow (or very small)
- After breakout: Price often returns to range (30-70% of range height)

**Special Behavior:**
- Acts as a **price magnet** in future
- If market lacks direction, price tends to return here
- Old gravitation ranges become support/resistance zones later

---

## Trading Strategies by Range Type

### Strategy 1: Trend Following (Recommended by Book)

#### Trading Resistance LR (Expecting DOWN move)

**Entry Rules:**
1. ✅ Wait for Resistance LR to form (green box, positive imbalance)
2. ✅ Wait for price to break BELOW the range
3. ✅ Look for confirmation:
   - Breakout label appears: "▼ DOWN"
   - Volume spike on breakout bar
   - Price stays below range (doesn't immediately return)
4. ✅ Enter SHORT position when:
   - Price returns to test the LOW boundary of the range, OR
   - On first pullback after breakout (better entry)

**Position Management:**
```
Entry: Near LR Low boundary (after breakout)
Stop Loss: Above LR High boundary + buffer (range height × 20%)
Take Profit 1: TPSL 1 Low (dashed red line) - take 50% off
Take Profit 2: TPSL 2 Low (dotted red line) - take remaining 50%
Break Even: Move stop to entry after price moves 50% toward TP1
```

**Risk/Reward:**
- Typical R:R = 1:2 to 1:3
- Stop loss = range height + buffer
- Target = previous swing low or range height projection

**Example Trade:**
```
LR: 1.1850 - 1.1800 (50 pips range)
Imbalance: +18.3% (Resistance)
Breakout: Price closes at 1.1785 (below 1.1800)
Entry: 1.1805 (pullback to LR low)
Stop: 1.1865 (above LR high + 15 pips buffer) = 60 pips risk
TP1: 1.1750 (TPSL 1 Low, previous swing) = 55 pips (0.9:1)
TP2: 1.1700 (TPSL 2 Low) = 105 pips (1.75:1 overall)
```

---

#### Trading Support LR (Expecting UP move)

**Entry Rules:**
1. ✅ Wait for Support LR to form (red box, negative imbalance)
2. ✅ Wait for price to break ABOVE the range
3. ✅ Look for confirmation:
   - Breakout label appears: "▲ UP"
   - Volume spike on breakout bar
   - Price stays above range
4. ✅ Enter LONG position when:
   - Price returns to test the HIGH boundary of the range, OR
   - On first pullback after breakout

**Position Management:**
```
Entry: Near LR High boundary (after breakout)
Stop Loss: Below LR Low boundary - buffer (range height × 20%)
Take Profit 1: TPSL 1 High (dashed green line) - take 50% off
Take Profit 2: TPSL 2 High (dotted green line) - take remaining 50%
Break Even: Move stop to entry after price moves 50% toward TP1
```

**Example Trade:**
```
LR: 2550.00 - 2556.00 (6 points range)
Imbalance: -16.8% (Support)
Breakout: Price closes at 2558.50 (above 2556.00)
Entry: 2556.50 (pullback to LR high)
Stop: 2548.75 (below LR low - 1.25 buffer) = 7.75 points risk
TP1: 2563.00 (TPSL 1 High) = 6.5 points (0.84:1)
TP2: 2570.00 (TPSL 2 High) = 13.5 points (1.74:1 overall)
```

---

### Strategy 2: Mean Reversion (Gravitation Range)

#### Trading Gravitation LR (Expecting RETURN to range)

**Entry Rules:**
1. ✅ Wait for Gravitation LR to form (gray box, near-zero imbalance)
2. ✅ Wait for price to break OUT of the range (either direction)
3. ✅ Look for weak breakout signs:
   - Quick/sharp movement beyond range (not slow grind)
   - No significant volume increase
   - Imbalance arrow NOT showing (or very small)
4. ✅ Enter OPPOSITE direction when:
   - Price is 100% of range height away from range, OR
   - Price shows reversal pattern (rejection wick, engulfing)

**Position Management:**
```
If breakout UP:
  Entry: When price extends 1× range height above LR High
  Stop Loss: At TPSL 1 High level
  Take Profit: Middle of LR (50% retracement)
  
If breakout DOWN:
  Entry: When price extends 1× range height below LR Low
  Stop Loss: At TPSL 1 Low level
  Take Profit: Middle of LR (50% retracement)
```

**Risk/Reward:**
- Typical R:R = 1:1 to 1:1.5
- Lower win rate than trend following (~55-65%)
- Best in ranging/flat markets

**Example Trade:**
```
LR: 51.30 - 51.73 (43 cent range)
Imbalance: +3.2% (Gravitation)
Breakout DOWN: Price drops to 50.87 (43 cents below range)
Entry: 50.90 SHORT → LONG reversal
Stop: 50.30 (TPSL 1 Low) = 60 cents risk
TP: 51.51 (middle of range) = 61 cents reward (1.02:1)
Result: Price gravitates back to range ✓
```

---

## Advanced Concepts

### 1. Range Cancellation (Important!)

**When Does a Range Cancel?**

A locked range loses its predictive power when:

**For Resistance/Support LR:**
- Price returns INSIDE the range by >70% of range height
- This means trapped positions got out at break-even
- The imbalance no longer exists

**For Gravitation LR:**
- Price returns INSIDE the range by >30% of range height
- Profitable positions were closed
- Range becomes invalidated

**What To Do:**
❌ Cancel your analysis of that specific range
✅ Look for NEW range formation
✅ Check if previous older ranges are still valid

**Example:**
```
Resistance LR: 1.2940 - 1.2970 (30 pips)
Breakout DOWN to 1.2920 ✓
BUT: Price rallies back to 1.2955 (inside range, 15 pips = 50% retracement)
Status: RANGE CANCELLED - don't short anymore
Reason: Trapped longs likely closed at break-even
```

---

### 2. Previous LR Influence

**Old ranges don't disappear** - they continue to influence price:

**Historical Resistance LR (was green, broke down):**
- NOW acts as: **Resistance zone** if price returns
- Why: Remaining breakeven longs waiting to exit
- Trade: Short if price returns to old LR from below

**Historical Support LR (was red, broke up):**
- NOW acts as: **Support zone** if price returns
- Why: Remaining breakeven shorts waiting to cover
- Trade: Long if price returns to old LR from above

**Historical Gravitation LR:**
- NOW acts as: **Price magnet**
- Why: Balanced zone, market "remembers" fair value
- Trade: Fade extremes back toward old GLR

**Visual Tip:** This is why historical ranges (dashed boxes) are crucial!

---

### 3. Confluence of Multiple Ranges

**Strongest Setups:**

**Same Type Ranges Stacking:**
```
Resistance LR #1: 1.1850-1.1800 (broke down)
Resistance LR #2: 1.1820-1.1780 (broke down)
Resistance LR #3: 1.1790-1.1760 (current)

Analysis: Strong bearish structure, multiple buyer traps
Trade: HIGH confidence SHORT on LR #3 breakout
```

**Alternating Ranges:**
```
Support LR: 2550-2556 (broke up)
Resistance LR: 2562-2568 (current)

Analysis: Market uncertainty, flip-flopping sentiment
Trade: LOWER confidence, wait for clearer pattern
```

---

### 4. Session Timing (Critical Per Book)

#### Best Trading Sessions by Instrument:

**Currency Futures (6E, 6B, 6J, 6A, 6C, 6S):**
- ✅ **Best:** Asian-Pacific session (22:00-09:00 GMT)
  - Why: Low volume, market maker accumulates positions
  - Look for: Range formation and initial breakout signals
  
- ⚠️ **Caution:** American session (13:00-21:00 GMT)
  - Why: High volume can reverse earlier ranges
  - What to do: Take profits, tighten stops on existing positions

**Index Futures (ES, NQ, YM):**
- ✅ **Best:** American session (13:00-21:00 GMT)
  - Why: Highest liquidity for equity derivatives
  - Look for: Clear directional moves

**Commodity Futures (CL, GC, SI):**
- ✅ **Best:** American session for CL, European for GC
  - Why: Aligns with main trading centers

**Key Rule from Book:**
> "Avoid entries during high-volume sessions for the instrument. Large new position volumes can change the imbalance to the opposite."

---

## Trade Management Rules

### Position Sizing (Per Book Recommendations)

```
Risk per trade: 1-2% of capital
Stop loss: Beyond LR boundary + buffer

Example with $50,000 account:
- Risk per trade: $1,000 (2%)
- LR range: 50 pips
- Stop loss: 60 pips (range + 20% buffer)
- Position size: $1,000 ÷ 60 pips = $16.67 per pip
- Contracts: Depends on instrument
```

### Stop Loss Placement

**For Trend Trades (Resistance/Support LR):**
```
Aggressive: 10% beyond opposite boundary
Standard: 20% beyond opposite boundary  
Conservative: 30% beyond opposite boundary

Example (Resistance LR short):
LR High: 1.1850
Aggressive stop: 1.1850 + (50 pips × 0.10) = 1.1855
Standard stop: 1.1850 + (50 pips × 0.20) = 1.1860
Conservative stop: 1.1850 + (50 pips × 0.30) = 1.1865
```

**Why the buffer?**
- Market maker may spike price to trigger stops at exact boundary
- 20% buffer accounts for this manipulation
- Book calls this "testing for break-even closures"

### Take Profit Scaling

**Recommended Approach:**
```
1st Target (TPSL 1): Take 50% off
   - Lock in profits
   - Move stop to break-even on remainder
   
2nd Target (TPSL 2): Take 30% off
   - Significant profit secured
   - Move stop to TPSL 1 level on remainder
   
3rd Target (Trail): Let 20% run with trailing stop
   - Catch extended moves
   - Trail stop at swing lows/highs
```

**Why Scale?**
- TPSL 1 hit rate: ~70-80%
- TPSL 2 hit rate: ~40-50%
- Beyond TPSL 2: ~20-30%

---

## Common Mistakes to Avoid

### ❌ Mistake #1: Trading Against the Imbalance
```
BAD: Seeing Resistance LR (green) and buying the breakout UP
GOOD: Shorting when it breaks DOWN (against trapped buyers)
```

### ❌ Mistake #2: Ignoring Range Cancellation
```
BAD: Holding short after price returns 80% into Resistance LR
GOOD: Exit immediately when range is cancelled (>70% return)
```

### ❌ Mistake #3: Trading Every Range
```
BAD: Trading all ranges regardless of quality
GOOD: Only trade when:
  - Imbalance > 15% (strong)
  - Clean breakout with volume
  - Confirms with previous ranges
  - Appropriate session timing
```

### ❌ Mistake #4: Forgetting Historical Context
```
BAD: Trading new range without checking historical dashed boxes
GOOD: Check if:
  - Previous ranges show same direction (confluence)
  - Old ranges might act as support/resistance
  - Market structure is trending or flat
```

### ❌ Mistake #5: Wrong Timeframe
```
BAD: Using 15-minute charts (too much noise)
GOOD: Using 1H-4H charts as recommended in book
```

---

## Visual Identification Checklist

### On Your Chart You Should See:

**Current Active Range (if present):**
- [ ] Solid bordered box (green/red/gray)
- [ ] Label showing type and imbalance %
- [ ] TPSL 1 levels (dashed lines extending right)
- [ ] TPSL 2 levels (dotted lines extending right)
- [ ] Imbalance arrow (▲ or ▼) if strong imbalance

**Historical Ranges:**
- [ ] Dashed bordered boxes (semi-transparent)
- [ ] Labels showing historical type and imbalance
- [ ] Multiple ranges showing market structure
- [ ] Breakout labels (▲ UP or ▼ DOWN) at breakout points

**Information Table (top right):**
- [ ] Current range type
- [ ] Range high/low values
- [ ] Current imbalance %
- [ ] TPSL 1 levels
- [ ] Historical LR count

---

## Example Trade Walkthrough

### Real Scenario: EUR/USD Support LR

**1. Range Formation (Day 1-3):**
```
Price consolidates: 1.1800 - 1.1840
Volume pattern: Heavy selling at lows (1.1800-1.1810)
Imbalance: -19.3% (Support LR)
Visual: RED box appears, labeled "Support -19.3%"
Analysis: Majority SHORT positions trapped
```

**2. Monitoring (Day 3-4):**
```
TPSL 1 High: 1.1860 (previous swing high)
TPSL 2 High: 1.1890 (second swing high)
Watch for: Breakout ABOVE 1.1840
Wait: Patience for confirmation
```

**3. Breakout (Day 4):**
```
Price action: Sharp move to 1.1852 with volume spike
Confirmation: "▲ UP" label appears
Imbalance arrow: Pointing UP
Historical: Previous Support LR also broke up (confluence!)
Decision: Prepare to enter LONG
```

**4. Entry (Day 4-5):**
```
Price pullback: Returns to 1.1842 (just above LR high)
Entry: 1.1843 LONG
Stop: 1.1795 (below LR low - 5 pip buffer) = 48 pips risk
Position: $1000 risk ÷ 48 pips = $20.83/pip
```

**5. Trade Management (Day 5-7):**
```
Price moves to 1.1860 (TPSL 1)
Action: Close 50%, move stop to 1.1843 (break-even) ✓
Profit: 17 pips × 50% position = +$177

Price continues to 1.1888 (near TPSL 2)
Action: Close 30%, move stop to 1.1860 (TPSL 1) ✓
Profit: 45 pips × 30% position = +$281

Price reaches 1.1902, then reverses
Action: Trail stop hit at 1.1875 on final 20% ✓
Profit: 32 pips × 20% position = +$133

Total Profit: $591 on $1,000 risk = +59.1% return
```

---

## Quick Decision Tree

```
Is there a locked range visible?
├─ NO → Wait for range formation
└─ YES → What type?
    ├─ Resistance (Green, +ve imbalance)
    │   └─ Has it broken DOWN?
    │       ├─ YES → Enter SHORT on pullback
    │       └─ NO → Wait for breakout
    │
    ├─ Support (Red, -ve imbalance)
    │   └─ Has it broken UP?
    │       ├─ YES → Enter LONG on pullback
    │       └─ NO → Wait for breakout
    │
    └─ Gravitation (Gray, ~zero imbalance)
        └─ Has it broken OUT (either way)?
            ├─ YES → Enter OPPOSITE direction (fade)
            └─ NO → Wait for breakout or skip
```

---

## Summary Table: Range Trading Playbook

| Scenario | Range Type | Signal | Entry | Stop | Target | R:R |
|----------|-----------|--------|-------|------|--------|-----|
| **Trapped Buyers** | Resistance 🟢 | Break DOWN + ▼ | Pullback to LR Low | Above LR High +20% | TPSL 1/2 Low | 1:2-1:3 |
| **Trapped Sellers** | Support 🔴 | Break UP + ▲ | Pullback to LR High | Below LR Low -20% | TPSL 1/2 High | 1:2-1:3 |
| **Mean Reversion** | Gravitation ⚪ | Break either + extension | 1× range beyond | TPSL 1 level | Middle of LR | 1:1-1:1.5 |
| **Range Cancelled** | Any | Price returns >70% (R/S) or >30% (G) | EXIT | N/A | N/A | Cut loss |

---

## Final Tips

1. **Trust the imbalance** - The market maker sees the trapped traders, you don't
2. **Be patient** - Wait for clear breakout confirmation, don't anticipate
3. **Respect range cancellation** - Exit when ranges invalidate (>70% return)
4. **Use historical context** - Previous ranges show market structure
5. **Session timing matters** - Avoid high-volume sessions for entries
6. **Scale your exits** - Don't try to nail the exact top/bottom
7. **Risk management first** - Never risk more than 2% per trade
8. **Keep it simple** - Focus on high-probability setups only

---

**Remember the Core Insight:**

> The futures market with market makers is designed to move AGAINST the majority of open positions. Find where traders are trapped, and trade with the market maker who is profiting from their losses.

---

*Based on "Locked-in Range Analysis" by Tom Leksey (2017)*
*For educational purposes only. Trade at your own risk.*
