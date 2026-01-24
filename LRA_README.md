# Locked Range Analysis (LRA)

Based on "Locked-in Range Analysis" by Tom Leksey

This repository contains two implementations of Locked Range Analysis:
1. **Pine Script** for TradingView (real-time chart analysis)
2. **Python Script** for SQLite database analysis (backtesting/research)

## What is Locked Range Analysis?

Locked Range Analysis is a technical analysis method that identifies trading ranges where open positions accumulate, causing the price to move against the prevailing positions. The method recognizes three types of locked ranges:

### Types of Locked Ranges

1. **Resistance Locked Range (R-LR)**
   - Buy positions prevail (bullish sentiment)
   - Market maker profits by quoting prices BELOW the range
   - Price tends to break downward

2. **Support Locked Range (S-LR)**
   - Sell positions prevail (bearish sentiment)
   - Market maker profits by quoting prices ABOVE the range
   - Price tends to break upward

3. **Gravitation Locked Range (G-LR)**
   - No significant imbalance between buy/sell positions
   - Price tends to return to the range after breakout
   - Acts as a price magnet

### TPSL Levels (Take-Profit/Stop-Loss)

- **TPSL 1**: Nearest previous swing high/low or range height extension
- **TPSL 2**: Second swing before the nearest one
- These levels represent where market participants are likely to exit positions

---

## Pine Script for TradingView

### Features
- Real-time detection of locked ranges
- Visual range boxes with color coding (Green=Resistance, Red=Support, Gray=Gravitation)
- Automatic TPSL level calculation and display
- Imbalance percentage calculation
- Breakout detection and alerts
- Customizable parameters

### How to Use

1. Open [TradingView](https://www.tradingview.com)
2. Open the Pine Script editor
3. Copy the contents of `LRA_PineScript.pine`
4. Paste into the editor
5. Click "Add to Chart"

### Customizable Parameters

**Range Detection:**
- Swing High/Low Length: Bars on each side for swing detection (default: 5)
- Minimum Bars in Range: Minimum duration for valid range (default: 10)
- ATR Multiple: ATR multiplier for range height (default: 2.0)

**TPSL Levels:**
- TPSL 1 Method: Auto/Range+Height/Swing (default: Auto)
- Show TPSL 2 Levels: Enable/disable TPSL 2 display

**Visual:**
- Show Locked Ranges: Toggle range box display
- Show TPSL 1 Levels: Toggle TPSL 1 lines
- Show TPSL 2 Levels: Toggle TPSL 2 lines
- Show Imbalance Arrows: Show directional arrows for strong imbalance

### Alerts

The script provides the following alerts:
- Resistance LR Detected
- Support LR Detected
- Gravitation LR Detected
- Breakout Up
- Breakout Down

### Interpreting the Analysis

**Information Table** (top-right corner):
- Range Type: R-LR (Resistance), S-LR (Support), or G-LR (Gravitation)
- Range High/Low: Price boundaries
- Imbalance: Percentage showing buy/sell pressure difference
  - Positive = Buy pressure dominates (Resistance)
  - Negative = Sell pressure dominates (Support)

**Trading Guidance:**
- **Trend Preference**: Enter positions OPPOSITE to the LR type
  - For Resistance LR: Short below the range
  - For Support LR: Long above the range
- **Flat Preference**: Enter at price deviation from LR, exit on return
- Take-Profit: At TPSL 1 or TPSL 2 levels
- Stop-Loss: Beyond the opposite LR boundary

---

## Python Script for SQLite Analysis

### Features
- Batch analysis of multiple symbols
- Export results to JSON
- CLI interface for flexible usage
- Historical analysis for backtesting
- Database integration with ohlc.sqlite3

### Requirements

```bash
pip install pandas numpy
```

### Usage Examples

**List all available symbols:**
```bash
python lra_analysis.py --list-symbols
```

**List available intervals for a symbol:**
```bash
python lra_analysis.py --list-intervals BTCUSDT
```

**Analyze a symbol with default settings:**
```bash
python lra_analysis.py --symbol BTCUSDT --interval 1h
```

**Analyze with custom parameters:**
```bash
python lra_analysis.py --symbol BTCUSDT --interval 4h --limit 2000 --exchange BINANCE
```

**Export results to JSON:**
```bash
python lra_analysis.py --symbol BTCUSDT --interval 1h --export btc_lra_analysis.json
```

**Full usage help:**
```bash
python lra_analysis.py --help
```

### Parameters

- `--db`: Path to SQLite database (default: ohlc.sqlite3)
- `--symbol`: Trading symbol to analyze (e.g., BTCUSDT)
- `--interval`: Time interval (e.g., 1h, 4h, 1d)
- `--exchange`: Exchange name filter (optional)
- `--limit`: Number of bars to analyze (default: 1000)
- `--export`: Export results to JSON file
- `--list-symbols`: List all available symbols in database
- `--list-intervals`: List available intervals for a symbol

### Output Format

The script provides a detailed analysis including:

**Locked Range Details:**
- Type: Resistance/Support/Gravitation
- Period: Start and end timestamps
- Range: High and low price levels
- Height: Range size in points
- Duration: Number of bars
- Imbalance: Buy vs sell pressure percentage
- High/Low Touches: Number of touches at boundaries
- Buy/Sell Pressure: Average volume per touch
- TPSL 1/2 Levels: Calculated take-profit/stop-loss levels

### Python API Usage

You can also use the LockedRangeAnalysis class directly in your code:

```python
from lra_analysis import LockedRangeAnalysis

# Initialize
lra = LockedRangeAnalysis('ohlc.sqlite3')
lra.connect()

# Analyze a symbol
analysis = lra.analyze_symbol('BTCUSDT', '1h', limit=500)

# Print results
lra.print_analysis(analysis)

# Export to JSON
lra.export_to_json(analysis, 'output.json')

# Get available symbols
symbols = lra.get_available_symbols()

# Get available intervals
intervals = lra.get_available_intervals('BTCUSDT')

# Close connection
lra.close()
```

---

## Trading Strategy Guidance

### Trend Preference (Following Market Maker)

**Entry Rules:**
1. Wait for price to approach a locked range
2. Enter in direction OPPOSITE to range type:
   - Resistance LR → Short position
   - Support LR → Long position
3. Entry point: Price touches range boundary

**Exit Rules:**
- Take-Profit: At TPSL 1 or TPSL 2
- Stop-Loss: Beyond opposite range boundary
- Exit early if new significant volume appears (imbalance changes)

**Example:**
- Resistance LR detected at 90,000 - 92,000 with 39% imbalance
- Enter SHORT at 91,800
- Take-Profit at TPSL 1 Low: 87,850
- Stop-Loss above 92,000

### Flat Preference (Range Trading)

**Entry Rules:**
1. Wait for price deviation from LR (between TPSL levels)
2. Enter in direction back to range
3. OR enter after breakout, expecting return

**Exit Rules:**
- Take-Profit: Price returns to LR
- OR price breaks through opposite TPSL level
- Stop-Loss: At TPSL 2 or TPSL 3 levels

### Risk Management

**Position Sizing:**
- Risk 1-2% of capital per trade
- Use range height for risk calculation
- Account for slippage at TPSL levels

**Session Awareness:**
- Avoid entries during high-volume sessions (American for futures)
- Prefer low-volume sessions (Asian-Pacific)
- Session influence on price formation (see LRA book Chapter 2.3)

---

## Key Concepts from LRA Methodology

### Volume Analysis

The method uses volume at range boundaries to determine imbalance:
- High volume at range high → Buy pressure → Resistance LR
- High volume at range low → Sell pressure → Support LR
- Balanced volume → Gravitation LR

### Im Calculation

Imbalance = (Buy Pressure - Sell Pressure) / Max(Buy Pressure, Sell Pressure)

- > +15%: Resistance LR
- < -15%: Support LR
- Between: Gravitation LR

### Range Breakouts

**Strong Imbreakout Signs:**
- Slow trend in breakout direction
- Price stays beyond LR for extended period
- Previous LR still has remaining positions

**Weak Imbalance Signs:**
- Quick sharp movement (spike)
- Price returns to 30-70% of range height
- Fast rollback to LR boundaries

---

## Database Schema

The Python script expects an SQLite database with the following structure:

```sql
CREATE TABLE ohlc (
    exchange TEXT,
    symbol TEXT,
    interval TEXT,
    open_time INTEGER,  -- milliseconds since epoch
    close_time INTEGER,  -- milliseconds since epoch
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL
);
```

---

## Performance Notes

### Pine Script
- Use on timeframes 1H or higher for best results
- May need to increase `max_lines_count` for very long historical charts
- Performance depends on number of active ranges

### Python Script
- Efficient batch processing with pandas
- Can analyze thousands of bars quickly
- Memory usage scales with dataset size

---

## Troubleshooting

### Pine Script
- **"Too many lines" error**: Increase `max_lines_count` parameter
- **"Too many labels" error**: Increase `max_labels_count` parameter
- **No ranges detected**: Try adjusting swing length or minimum bars

### Python Script
- **"No data found"**: Check symbol name and interval are correct
- **Database locked**: Ensure no other process is using the database
- **Memory issues**: Reduce `--limit` parameter

---

## References

- **Book**: "Locked-in Range Analysis: Why most traders must lose money in the futures market" by Tom Leksey
- **Website**: LRAtrading.com
- **Methodology**: Based on market maker behavior and open interest analysis

---

## License

This implementation is provided for educational and research purposes. Trading involves substantial risk of loss.

## Disclaimer

This software is for educational purposes only. Past performance is not indicative of future results. Always conduct your own research and use proper risk management before trading.
