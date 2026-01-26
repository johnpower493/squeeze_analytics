# LRA Pine Script Validation Guide

This guide helps you verify that the improved `LRA_PINE_IMPROVED.pine` indicator correctly implements Tom Leksey's Locked Range Analysis methodology from the book "Locked-in Range Analysis: Why most traders must lose money in the futures market."

---

## Table of Contents

1. [Setup Instructions](#setup-instructions)
2. [Test Case 1: Range Detection](#test-case-1-range-detection)
3. [Test Case 2: Range Type Classification](#test-case-2-range-type-classification)
4. [Test Case 3: Imbalance Calculation](#test-case-3-imbalance-calculation)
5. [Test Case 4: TPSL Level Calculation](#test-case-4-tpsl-level-calculation)
6. [Test Case 5: Breakout Detection](#test-case-5-breakout-detection)
7. [Test Case 6: Range Cancellation](#test-case-6-range-cancellation)
8. [Test Case 7: Volume Degree (TOI)](#test-case-7-volume-degree-toi)
9. [Test Case 8: Multi-Timeframe Confirmation](#test-case-8-multi-timeframe-confirmation)
10. [Historical Validation Checklist](#historical-validation-checklist)
11. [Known Limitations](#known-limitations)

---

## Setup Instructions

### Step 1: Add the Indicator to TradingView

1. Open TradingView and go to Pine Script Editor
2. Copy the contents of `LRA_PINE_IMPROVED.pine`
3. Click "Add to Chart"
4. Configure settings as needed

### Step 2: Recommended Test Symbols

Per the book (Chapter 2.3), test on these CME futures or their Forex equivalents:

| Symbol | Book Reference | Best Session |
|--------|---------------|--------------|
| 6E / EURUSD | Euro FX | European + American |
| 6J / USDJPY | Japanese Yen | American + Asian |
| 6B / GBPUSD | British Pound | European + American |
| 6A / AUDUSD | Australian Dollar | Asian + American |
| ES | E-mini S&P 500 | American |
| CL | Crude Oil | American |
| GC | Gold | American |

### Step 3: Recommended Timeframes

Per book Chapter 2.3:
- **Primary**: 1H (includes TPSL levels and recent trading days)
- **Confirmation**: 4H (for multi-timeframe analysis)
- **Context**: Daily (for major swing levels)

---

## Test Case 1: Range Detection

### Objective
Verify that locked ranges are detected when price consolidates within a defined area.

### Book Reference
- Chapter 2.1: "Locked-in Range (abbr. LR) is the trading range in which the volume of open positions accumulates"

### Test Steps

1. **Find a consolidation period** on the chart (sideways movement with at least 8 bars)
2. **Observe the indicator**:
   - [ ] A colored box should appear around the consolidation
   - [ ] The box should capture the high and low of the range
   - [ ] The label should show range type

### Expected Behavior

```
✓ Range detected after minimum bars (default: 8)
✓ Range boundaries expand to include new highs/lows
✓ Range resets if price trends without consolidating
✓ Range resets if exceeding max bars (default: 100)
```

### Validation Checklist

- [ ] Consolidation areas are identified
- [ ] Range boundaries are accurate
- [ ] No false positives during strong trends
- [ ] Range label displays correctly

---

## Test Case 2: Range Type Classification

### Objective
Verify correct classification of Resistance, Support, and Gravitation ranges.

### Book Reference
- Chapter 2.1:
  - "**Resistance LR** is the locked-in range in which the volume of open **buy positions prevails**, and it is profitable for the market maker to quote prices **below** the range."
  - "**Support LR** is the locked-in range in which the volume of open **sell positions prevails**, and it is profitable for the market maker to quote prices **above** the range."
  - "**Gravitation LR** is the trading range in which the volume of open 'buy & sell' positions accumulates with **no significant imbalance**"

### Test Steps

1. **Resistance LR Test**:
   - Find a range where price repeatedly touches the HIGH boundary
   - Higher volume at the top = more buyers entering at top (trapped longs)
   - [ ] Should be colored RED
   - [ ] Label should say "Resistance LR"
   - [ ] Expected direction arrow should point DOWN (▼)

2. **Support LR Test**:
   - Find a range where price repeatedly touches the LOW boundary
   - Higher volume at the bottom = more sellers entering at bottom (trapped shorts)
   - [ ] Should be colored GREEN
   - [ ] Label should say "Support LR"
   - [ ] Expected direction arrow should point UP (▲)

3. **Gravitation LR Test**:
   - Find a range with balanced touches at both boundaries
   - Similar volume at top and bottom
   - [ ] Should be colored GRAY
   - [ ] Label should say "Gravitation LR"
   - [ ] No expected direction arrow (neutral)

### Expected Behavior

```
Imbalance >= 15% with more volume at HIGH → Resistance (Red)
Imbalance >= 15% with more volume at LOW → Support (Green)
Imbalance < 15% → Gravitation (Gray)
```

### Validation Checklist

- [ ] Resistance ranges identified when buyers trapped at top
- [ ] Support ranges identified when sellers trapped at bottom
- [ ] Gravitation ranges show balanced volume
- [ ] Colors match type correctly

---

## Test Case 3: Imbalance Calculation

### Objective
Verify that imbalance percentage is calculated correctly based on volume at boundaries.

### Book Reference
- Chapter 2.4: Volume at boundaries determines imbalance
- Figure 8: "Average scenario for determining the volume's appearance"

### Test Steps

1. **Enable volume display** on your chart
2. **Observe a forming range**:
   - Note the volume on bars touching the HIGH boundary
   - Note the volume on bars touching the LOW boundary
3. **Compare with indicator**:
   - [ ] Imbalance % displayed in label
   - [ ] Positive imbalance = more buy pressure (Resistance)
   - [ ] Negative imbalance = more sell pressure (Support)

### Manual Calculation

```
avgVolHigh = Sum of volume at high touches / Number of high touches
avgVolLow = Sum of volume at low touches / Number of low touches
maxAvgVol = max(avgVolHigh, avgVolLow)

rawImbalance = (avgVolHigh - avgVolLow) / maxAvgVol

If rawImbalance > 0 → Resistance (buyers at top)
If rawImbalance < 0 → Support (sellers at bottom)
```

### Validation Checklist

- [ ] Imbalance percentage displays correctly
- [ ] Positive values = Resistance, Negative = Support
- [ ] "Weak" / "Moderate" / "Strong" labels are accurate
- [ ] 15% threshold differentiates Gravitation from directional LR

---

## Test Case 4: TPSL Level Calculation

### Objective
Verify Take-Profit/Stop-Loss levels are calculated per book methodology.

### Book Reference
- Chapter 2.2: "TPSL 1 is determined principally on the basis of:
  1. The nearest previous Swing High/Low before the current range
  2. High/Low prices of the current range
  3. Addition X points to High/Low prices of the current range, where X is equal to the height of the current range"

### Test Steps

1. **TPSL1 Test (Auto Mode)**:
   - Find a range with visible previous swing high/low BEFORE the range started
   - [ ] TPSL1 High should align with previous swing high (if above range)
   - [ ] TPSL1 Low should align with previous swing low (if below range)
   - [ ] If no swing available, should use range height projection

2. **TPSL1 Test (Range Height Mode)**:
   - Change setting to "Range Height"
   - [ ] TPSL1 High = Range High + Range Height
   - [ ] TPSL1 Low = Range Low - Range Height

3. **TPSL2 Test**:
   - Enable TPSL2 display
   - [ ] TPSL2 should be beyond TPSL1 (further from range)
   - [ ] Uses second previous swing or extends from TPSL1

### Visual Verification

```
Expected Layout (Support LR example):
                    
  ─────────────────  TPSL2 High (dotted line)
  ─────────────────  TPSL1 High (dashed line)
  ┌───────────────┐  Range High
  │   SUPPORT LR  │
  └───────────────┘  Range Low
  ─────────────────  TPSL1 Low (dashed line)
  ─────────────────  TPSL2 Low (dotted line)
```

### Validation Checklist

- [ ] TPSL1 lines display at correct levels
- [ ] TPSL2 lines are beyond TPSL1
- [ ] Auto mode uses swings when available
- [ ] Range height projection works when no swings
- [ ] Info table shows correct TPSL values

---

## Test Case 5: Breakout Detection

### Objective
Verify breakouts are detected correctly and trigger appropriate signals.

### Book Reference
- Chapter 2.4: "The breakout of Low extremum of LR (TPSL 1 Low) and previous swing Low (TPSL 2 Low) with a 'Medium' degree of volume's appearance is an indicator pointing to the volume imbalance"

### Test Steps

1. **Breakout Up Test**:
   - Find a range that breaks upward
   - [ ] Breakout label appears: "▲ BREAKOUT UP"
   - [ ] Label triggers when close > Range High + threshold
   - [ ] Range box is saved to history

2. **Breakout Down Test**:
   - Find a range that breaks downward
   - [ ] Breakout label appears: "▼ BREAKOUT DOWN"
   - [ ] Label triggers when close < Range Low - threshold
   - [ ] Range box is saved to history

3. **False Breakout Test**:
   - Find a wick that pierces range but closes inside
   - [ ] Should NOT trigger breakout
   - [ ] Range should remain active

### Breakout Threshold

```
Default: 0.5% of range height
Breakout Up: Close > Range High + (Range Height * 0.5%)
Breakout Down: Close < Range Low - (Range Height * 0.5%)
```

### Validation Checklist

- [ ] Breakout labels appear at correct bars
- [ ] Requires close beyond range (not just wick)
- [ ] Historical range is saved with correct properties
- [ ] Active range clears after breakout

---

## Test Case 6: Range Cancellation

### Objective
Verify that ranges are cancelled when price returns too far into the range after breakout.

### Book Reference
- Chapter 2.4: 
  - "Price return after the breakout of TPSL 1 level by **30-70%** of the height of the considered **gravitation** locked-in range in points"
  - "and by **>70%** of the height of the considered **resistance / support** locked-in range in points"

### Test Steps

1. **Resistance/Support Cancellation Test**:
   - Find a Resistance or Support LR that breaks out
   - Observe if price returns >70% into the range
   - [ ] "✗ LR CANCELLED" label should appear
   - [ ] Historical box should have dotted border
   - [ ] Label should show "(XX% return)"

2. **Gravitation Cancellation Test**:
   - Find a Gravitation LR that breaks out
   - Observe if price returns 30-70% into the range
   - [ ] Should trigger cancellation earlier than Resistance/Support

### Cancellation Thresholds

```
Resistance/Support LR: Cancel if price returns >70% into range
Gravitation LR: Cancel if price returns >50% into range (configurable)
```

### Validation Checklist

- [ ] Cancellation triggers at correct return percentage
- [ ] Cancelled ranges show dotted borders
- [ ] Cancellation label displays return percentage
- [ ] Different thresholds for different LR types

---

## Test Case 7: Volume Degree (TOI)

### Objective
Verify Thinkable Open Interest (TOI) classification based on volume.

### Book Reference
- Chapter 2.4, Table 13: "Properties of the locked-in range depending on the thinkable open interest (TOI)"
  - 3/3 = High number of open positions, Low volume appearance
  - 2/3 = Medium
  - 1/3 = Low number of open positions, High volume appearance

### Test Steps

1. **High TOI Test**:
   - Find a range with volume >1.5x average
   - [ ] Label should show "TOI: High"

2. **Medium TOI Test**:
   - Find a range with volume 0.8-1.5x average
   - [ ] Label should show "TOI: Medium"

3. **Low TOI Test**:
   - Find a range with volume <0.8x average
   - [ ] Label should show "TOI: Low"

### Volume Degree Calculation

```
volRatio = Total Range Volume / (Average Volume * Number of Bars)

volRatio > 1.5 → "High"
volRatio 0.8-1.5 → "Medium"
volRatio < 0.8 → "Low"
```

### Interpretation (Per Book)

| TOI | Open Positions | Volume Beyond TPSL | Meaning |
|-----|---------------|-------------------|---------|
| High (3/3) | High | Low | Strong trapped positions |
| Medium (2/3) | Medium | Medium | Moderate imbalance |
| Low (1/3) | Low | High | Weak, may not hold |

### Validation Checklist

- [ ] TOI displays on range labels
- [ ] TOI displays in info table
- [ ] Classification matches volume analysis
- [ ] Historical ranges retain TOI classification

---

## Test Case 8: Multi-Timeframe Confirmation

### Objective
Verify that higher timeframe consolidation check prevents false signals during HTF trends.

### Book Reference
- Chapter 2.3: "Significant price movements (going beyond the TPSL levels) at sessions with low influence on the formation of prices occur based on or taking into account and not contradicting the prevailing open positions during sessions with higher influence."

### Test Steps

1. **HTF Consolidating Test**:
   - Set chart to 1H, HTF to 4H
   - Find period where 4H is ranging
   - [ ] Info table shows "✓ Consolidating"
   - [ ] Ranges should be detected normally

2. **HTF Trending Test**:
   - Find period where 4H is strongly trending
   - [ ] Info table shows "✗ Trending"
   - [ ] Fewer/no ranges detected on 1H
   - [ ] Prevents false consolidation signals

3. **Disable MTF Test**:
   - Turn off "Enable Multi-Timeframe Confirmation"
   - [ ] All ranges detected regardless of HTF
   - [ ] Info table shows "Disabled"

### Validation Checklist

- [ ] HTF confirmation status displays correctly
- [ ] Ranges suppressed during HTF trends
- [ ] Feature can be disabled
- [ ] Different HTF timeframes can be selected

---

## Historical Validation Checklist

Use the book's example charts (Chapter 2.5) to validate:

### Euro FX Validation (Figure 9.1a-b)
- [ ] December 2017, 1H chart
- [ ] Range: 1.18850-1.18500
- [ ] Type: Resistance (Buy 1/3)
- [ ] Expected: Short positions below range

### Japanese Yen Validation (Figure 9.2a-b)
- [ ] June 2017, 1H chart
- [ ] Range: 0.008960-0.008940
- [ ] Type: Support (Sell 1/3)
- [ ] Expected: Long positions above range

### E-mini S&P 500 Validation (Figure 9.7a-b)
- [ ] December 2017, 1H chart
- [ ] Range: 2562.75-2556.75
- [ ] Type: Support (Sell 1/3)
- [ ] Expected: Long positions above range

### Gold Validation (Figure 9.11a-b)
- [ ] June 2017, 1H chart
- [ ] Range: 1289.0-1279.5
- [ ] Type: Resistance (Buy 1/3)
- [ ] Expected: Short positions below range

---

## Known Limitations

### 1. Repainting Behavior
- **Active ranges** update as new bars form
- **Pivot-based TPSL** levels confirm with delay
- **Historical ranges** do NOT repaint

### 2. Volume Data
- Forex volume may not reflect true market volume
- Best results on futures with real volume data

### 3. Subjectivity
- Range boundaries are algorithmically determined
- Manual LRA may identify slightly different ranges

### 4. Market Conditions
- Works best in ranging/consolidating markets
- May generate few signals during strong trends

---

## Troubleshooting

### No Ranges Detected
1. Check if market is trending (not consolidating)
2. Increase "Maximum Bars in Range" setting
3. Decrease "Narrow Range ATR Multiplier"
4. Disable MTF confirmation

### Too Many Ranges
1. Increase "Minimum Bars in Range"
2. Increase "Minimum Imbalance %" 
3. Enable MTF confirmation

### TPSL Levels Missing
1. Ensure sufficient historical data for swing detection
2. Increase "Swing High/Low Length"
3. Check TPSL display settings are enabled

### Cancellation Not Working
1. Verify "LR Cancellation Return %" setting
2. Check that breakout occurred first
3. Confirm price actually returned into range

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-26 | Initial improved version based on LRA_EN.pdf |

---

## References

- Leksey, T. (2017). *Locked-in Range Analysis: Why most traders must lose money in the futures market*. First Edition.
- LRAtrading.com - Daily LRA reports and analysis
