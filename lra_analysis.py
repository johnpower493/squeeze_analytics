#!/usr/bin/env python3
"""
Locked Range Analysis (LRA) - Python Script
Based on "Locked-in Range Analysis" by Tom Leksey

This script analyzes OHLC data from SQLite database to identify:
1. Resistance Locked Ranges (Buy positions prevail)
2. Support Locked Ranges (Sell positions prevail)
3. Gravitation Locked Ranges (No significant imbalance)
4. TPSL (Take-Profit/Stop-Loss) levels
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
import argparse


class LockedRangeAnalysis:
    """Main class for Locked Range Analysis"""
    
    def __init__(self, db_path: str = 'ohlc.sqlite3'):
        """
        Initialize LRA analyzer
        
        Args:
            db_path: Path to SQLite database containing OHLC data
        """
        self.db_path = db_path
        self.conn = None
        self.atr_period = 14
        self.swing_length = 5
        self.range_min_bars = 10
        self.atr_mult = 2.0
        
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def get_available_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """
        Get list of available symbols in the database
        
        Args:
            exchange: Filter by exchange (optional)
            
        Returns:
            List of symbol names
        """
        query = "SELECT DISTINCT symbol FROM ohlc"
        params = []
        
        if exchange:
            query += " WHERE exchange = ?"
            params.append(exchange)
            
        query += " ORDER BY symbol"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df['symbol'].tolist()
    
    def get_available_intervals(self, symbol: str, exchange: Optional[str] = None) -> List[str]:
        """
        Get available intervals for a symbol
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name (optional)
            
        Returns:
            List of available intervals
        """
        query = "SELECT DISTINCT interval FROM ohlc WHERE symbol = ?"
        params = [symbol]
        
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
            
        query += " ORDER BY interval"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df['interval'].tolist()
    
    def load_ohlc_data(self, symbol: str, interval: str, 
                       exchange: Optional[str] = None,
                       limit: int = 1000) -> pd.DataFrame:
        """
        Load OHLC data from database
        
        Args:
            symbol: Trading symbol
            interval: Time interval (e.g., '1h', '4h', '1d')
            exchange: Exchange name (optional)
            limit: Maximum number of bars to load
            
        Returns:
            DataFrame with OHLC data
        """
        query = """
        SELECT open_time, close_time, open, high, low, close, volume
        FROM ohlc
        WHERE symbol = ? AND interval = ?
        """
        params = [symbol, interval]
        
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
            
        query += " ORDER BY open_time DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Convert to datetime
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # Sort by time ascending
        df = df.sort_values('open_time').reset_index(drop=True)
        
        return df
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        
        Args:
            df: DataFrame with OHLC data
            period: ATR period
            
        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def find_swing_points(self, df: pd.DataFrame, length: int = 5) -> Tuple[pd.Series, pd.Series]:
        """
        Identify swing high and swing low points
        
        Args:
            df: DataFrame with OHLC data
            length: Swing length (bars on each side)
            
        Returns:
            Tuple of (swing_highs, swing_lows) Series
        """
        highs = df['high']
        lows = df['low']
        
        swing_high = pd.Series(False, index=df.index)
        swing_low = pd.Series(False, index=df.index)
        
        for i in range(length, len(df) - length):
            # Check for swing high
            is_swing_high = True
            for j in range(i - length, i + length + 1):
                if j != i and highs.iloc[j] >= highs.iloc[i]:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_high.iloc[i] = True
            
            # Check for swing low
            is_swing_low = True
            for j in range(i - length, i + length + 1):
                if j != i and lows.iloc[j] <= lows.iloc[i]:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_low.iloc[i] = True
        
        return swing_high, swing_low
    
    def detect_locked_ranges(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect locked ranges in price data
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of detected locked ranges with details
        """
        if len(df) < self.range_min_bars * 2:
            return []
        
        df = df.copy()
        df['atr'] = self.calculate_atr(df, self.atr_period)
        df['price_range'] = df['high'] - df['low']
        df['is_narrow'] = df['price_range'] < df['atr'] * 0.5
        
        swing_high, swing_low = self.find_swing_points(df, self.swing_length)
        df['swing_high'] = swing_high
        df['swing_low'] = swing_low
        
        locked_ranges = []
        in_range = False
        range_start_idx = 0
        range_high = 0.0
        range_low = 0.0
        high_touches = 0
        low_touches = 0
        sum_high_volume = 0.0
        sum_low_volume = 0.0
        
        for i in range(len(df)):
            if not in_range:
                # Look for range start
                if df['is_narrow'].iloc[i]:
                    in_range = True
                    range_start_idx = i
                    range_high = df['high'].iloc[i]
                    range_low = df['low'].iloc[i]
                    high_touches = 0
                    low_touches = 0
                    sum_high_volume = 0.0
                    sum_low_volume = 0.0
            else:
                # Expand range
                range_high = max(range_high, df['high'].iloc[i])
                range_low = min(range_low, df['low'].iloc[i])
                
                # Count touches (price near range boundaries)
                touch_threshold = df['atr'].iloc[i] * 0.1
                if df['high'].iloc[i] >= range_high - touch_threshold:
                    high_touches += 1
                    sum_high_volume += df['volume'].iloc[i]
                if df['low'].iloc[i] <= range_low + touch_threshold:
                    low_touches += 1
                    sum_low_volume += df['volume'].iloc[i]
                
                # Check if range is broken or matured
                # Range broken if price moves significantly outside
                if (df['high'].iloc[i] > range_high + df['atr'].iloc[i] * 0.5 or
                    df['low'].iloc[i] < range_low - df['atr'].iloc[i] * 0.5):
                    
                    # Check if range lasted long enough
                    if (i - range_start_idx) >= self.range_min_bars:
                        lr = self._analyze_locked_range(
                            df, range_start_idx, i-1,
                            range_high, range_low,
                            high_touches, low_touches,
                            sum_high_volume, sum_low_volume
                        )
                        locked_ranges.append(lr)
                    
                    in_range = False
                
                # Check for range maturity (max 50 bars)
                elif (i - range_start_idx) >= 50:
                    lr = self._analyze_locked_range(
                        df, range_start_idx, i,
                        range_high, range_low,
                        high_touches, low_touches,
                        sum_high_volume, sum_low_volume
                    )
                    locked_ranges.append(lr)
                    in_range = False
        
        return locked_ranges
    
    def _analyze_locked_range(self, df: pd.DataFrame, start_idx: int, end_idx: int,
                             range_high: float, range_low: float,
                             high_touches: int, low_touches: int,
                             sum_high_volume: float, sum_low_volume: float) -> Dict:
        """
        Analyze a detected locked range and determine its type
        
        Args:
            df: DataFrame with OHLC data
            start_idx: Start index of range
            end_idx: End index of range
            range_high: High of the range
            range_low: Low of the range
            high_touches: Number of touches at high
            low_touches: Number of touches at low
            sum_high_volume: Total volume at high touches
            sum_low_volume: Total volume at low touches
            
        Returns:
            Dictionary with range analysis
        """
        # Calculate volume imbalance
        buy_pressure = sum_high_volume / max(high_touches, 1)
        sell_pressure = sum_low_volume / max(low_touches, 1)
        
        if buy_pressure == 0 and sell_pressure == 0:
            imbalance = 0.0
        else:
            imbalance = (buy_pressure - sell_pressure) / max(buy_pressure, sell_pressure)
        
        # Determine range type
        if imbalance > 0.15:
            lr_type = "Resistance"  # Buy positions prevail
        elif imbalance < -0.15:
            lr_type = "Support"  # Sell positions prevail
        else:
            lr_type = "Gravitation"  # No significant imbalance
        
        # Calculate range metrics
        range_height = range_high - range_low
        duration_bars = end_idx - start_idx + 1
        avg_volume = df.loc[start_idx:end_idx, 'volume'].mean()
        
        # Find TPSL levels
        tpsl1_high, tpsl1_low, tpsl2_high, tpsl2_low = self._calculate_tpsl_levels(
            df, start_idx, end_idx, range_high, range_low, range_height
        )
        
        return {
            'start_time': df['open_time'].iloc[start_idx],
            'end_time': df['open_time'].iloc[end_idx],
            'start_idx': start_idx,
            'end_idx': end_idx,
            'range_high': range_high,
            'range_low': range_low,
            'range_height': range_height,
            'duration_bars': duration_bars,
            'avg_volume': avg_volume,
            'high_touches': high_touches,
            'low_touches': low_touches,
            'buy_pressure': buy_pressure,
            'sell_pressure': sell_pressure,
            'imbalance': imbalance,
            'type': lr_type,
            'tpsl1_high': tpsl1_high,
            'tpsl1_low': tpsl1_low,
            'tpsl2_high': tpsl2_high,
            'tpsl2_low': tpsl2_low
        }
    
    def _calculate_tpsl_levels(self, df: pd.DataFrame, start_idx: int, end_idx: int,
                             range_high: float, range_low: float,
                             range_height: float) -> Tuple[Optional[float], Optional[float],
                                                         Optional[float], Optional[float]]:
        """
        Calculate TPSL (Take-Profit/Stop-Loss) levels
        
        Args:
            df: DataFrame with OHLC data
            start_idx: Range start index
            end_idx: Range end index
            range_high: Range high
            range_low: Range low
            range_height: Range height
            
        Returns:
            Tuple of (tpsl1_high, tpsl1_low, tpsl2_high, tpsl2_low)
        """
        # TPSL 1: Nearest swing before range or range + height
        prev_swing_high = None
        prev_swing_low = None
        
        # Look for previous swings before range
        for i in range(start_idx - 1, max(0, start_idx - 50), -1):
            if df['swing_high'].iloc[i]:
                prev_swing_high = df['high'].iloc[i]
                break
        for i in range(start_idx - 1, max(0, start_idx - 50), -1):
            if df['swing_low'].iloc[i]:
                prev_swing_low = df['low'].iloc[i]
                break
        
        # TPSL 1: Use nearest swing or range + height
        tpsl1_high = prev_swing_high if prev_swing_high and prev_swing_high > range_high else range_high + range_height
        tpsl1_low = prev_swing_low if prev_swing_low and prev_swing_low < range_low else range_low - range_height
        
        # TPSL 2: Second swing before nearest
        tpsl2_high = None
        tpsl2_low = None
        
        found_first_high = False
        found_first_low = False
        
        for i in range(start_idx - 1, max(0, start_idx - 100), -1):
            if df['swing_high'].iloc[i] and not found_first_high:
                found_first_high = True
            elif df['swing_high'].iloc[i] and found_first_high:
                tpsl2_high = df['high'].iloc[i]
                break
        
        for i in range(start_idx - 1, max(0, start_idx - 100), -1):
            if df['swing_low'].iloc[i] and not found_first_low:
                found_first_low = True
            elif df['swing_low'].iloc[i] and found_first_low:
                tpsl2_low = df['low'].iloc[i]
                break
        
        return tpsl1_high, tpsl1_low, tpsl2_high, tpsl2_low
    
    def analyze_symbol(self, symbol: str, interval: str,
                       exchange: Optional[str] = None,
                       limit: int = 1000) -> Dict:
        """
        Perform complete LRA analysis for a symbol
        
        Args:
            symbol: Trading symbol
            interval: Time interval
            exchange: Exchange name (optional)
            limit: Number of bars to analyze
            
        Returns:
            Dictionary with analysis results
        """
        df = self.load_ohlc_data(symbol, interval, exchange, limit)
        
        if len(df) == 0:
            return {'error': f'No data found for {symbol} {interval}'}
        
        locked_ranges = self.detect_locked_ranges(df)
        
        # Get current price info
        latest = df.iloc[-1]
        current_price = latest['close']
        current_time = latest['open_time']
        
        return {
            'symbol': symbol,
            'interval': interval,
            'exchange': exchange,
            'analysis_time': datetime.now(),
            'data_start': df['open_time'].iloc[0],
            'data_end': df['open_time'].iloc[-1],
            'current_price': current_price,
            'current_time': current_time,
            'bars_analyzed': len(df),
            'locked_ranges_count': len(locked_ranges),
            'locked_ranges': locked_ranges
        }
    
    def export_to_json(self, analysis: Dict, filename: str):
        """
        Export analysis results to JSON file
        
        Args:
            analysis: Analysis dictionary
            filename: Output filename
        """
        # Convert datetime objects to strings
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=datetime_handler)
        
        print(f"Analysis exported to {filename}")
    
    def print_analysis(self, analysis: Dict):
        """
        Print analysis results in readable format
        
        Args:
            analysis: Analysis dictionary
        """
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            return
        
        print("\n" + "="*70)
        print("LOCKED RANGE ANALYSIS")
        print("="*70)
        print(f"Symbol: {analysis['symbol']} | Interval: {analysis['interval']}")
        if analysis['exchange']:
            print(f"Exchange: {analysis['exchange']}")
        print(f"Current Price: {analysis['current_price']}")
        print(f"Bars Analyzed: {analysis['bars_analyzed']}")
        print(f"Locked Ranges Found: {analysis['locked_ranges_count']}")
        print("="*70 + "\n")
        
        for i, lr in enumerate(analysis['locked_ranges'], 1):
            print(f"Locked Range #{i}")
            print(f"  Type: {lr['type']}")
            print(f"  Period: {lr['start_time']} to {lr['end_time']}")
            print(f"  Range: {lr['range_low']:.4f} - {lr['range_high']:.4f}")
            print(f"  Height: {lr['range_height']:.4f}")
            print(f"  Duration: {lr['duration_bars']} bars")
            print(f"  Imbalance: {lr['imbalance']*100:.1f}%")
            print(f"  High Touches: {lr['high_touches']} | Low Touches: {lr['low_touches']}")
            print(f"  Buy Pressure: {lr['buy_pressure']:.0f} | Sell Pressure: {lr['sell_pressure']:.0f}")
            print(f"  TPSL 1 High: {lr['tpsl1_high']:.4f}")
            print(f"  TPSL 1 Low: {lr['tpsl1_low']:.4f}")
            if lr['tpsl2_high']:
                print(f"  TPSL 2 High: {lr['tpsl2_high']:.4f}")
            if lr['tpsl2_low']:
                print(f"  TPSL 2 Low: {lr['tpsl2_low']:.4f}")
            print()
        
        print("="*70 + "\n")


def main():
    """Main function for CLI usage"""
    parser = argparse.ArgumentParser(
        description='Locked Range Analysis (LRA) - Analyze OHLC data for locked ranges'
    )
    parser.add_argument('--db', default='ohlc.sqlite3', help='SQLite database path')
    parser.add_argument('--symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('--interval', default='1h', help='Time interval (e.g., 1h, 4h, 1d)')
    parser.add_argument('--exchange', help='Exchange name (optional)')
    parser.add_argument('--limit', type=int, default=1000, help='Number of bars to analyze')
    parser.add_argument('--export', help='Export results to JSON file')
    parser.add_argument('--list-symbols', action='store_true', help='List available symbols')
    parser.add_argument('--list-intervals', help='List available intervals for a symbol')
    
    args = parser.parse_args()
    
    lra = LockedRangeAnalysis(args.db)
    lra.connect()
    
    try:
        if args.list_symbols:
            symbols = lra.get_available_symbols(args.exchange)
            print("Available symbols:")
            for sym in symbols:
                print(f"  {sym}")
        elif args.list_intervals:
            intervals = lra.get_available_intervals(args.list_intervals, args.exchange)
            print(f"Available intervals for {args.list_intervals}:")
            for interval in intervals:
                print(f"  {interval}")
        else:
            analysis = lra.analyze_symbol(
                args.symbol, args.interval, args.exchange, args.limit
            )
            lra.print_analysis(analysis)
            
            if args.export:
                lra.export_to_json(analysis, args.export)
    
    finally:
        lra.close()


if __name__ == '__main__':
    main()
