import pandas as pd
import numpy as np

def calculate_smc(df: pd.DataFrame, swing_length: int = 5) -> pd.DataFrame:
    """
    Computes Smart Money Concepts (BOS, CHoCH, FVG, OB) on a DataFrame.
    Assumes df has 'Open', 'High', 'Low', 'Close', 'Volume'.
    """
    df = df.copy()
    
    # 1. Swing Highs & Lows
    # A swing high is the highest high in a window of size 2*swing_length + 1
    df['SwingHigh'] = df['High'].rolling(window=2*swing_length+1, center=True).max() == df['High']
    df['SwingLow'] = df['Low'].rolling(window=2*swing_length+1, center=True).min() == df['Low']
    
    # Store the actual levels (forward fill so we know the 'current' swing high/low)
    # We only know it's a swing high AFTER 'swing_length' bars have passed, so we shift by swing_length
    df['SwingHighLevel'] = np.where(df['SwingHigh'], df['High'], np.nan)
    df['SwingLowLevel'] = np.where(df['SwingLow'], df['Low'], np.nan)
    
    # Shift forward by swing_length to prevent lookahead bias in real-time signals
    df['SwingHighLevel'] = df['SwingHighLevel'].shift(swing_length).ffill()
    df['SwingLowLevel'] = df['SwingLowLevel'].shift(swing_length).ffill()
    
    # 2. Market Structure (Trend)
    # 1 for Bullish, -1 for Bearish
    df['Trend'] = np.nan
    df['Structure'] = ""  # BOS or CHoCH
    
    # We iterate to find BOS and CHoCH properly
    trend = 1
    last_sh = np.nan
    last_sl = np.nan
    
    structure_signals = []
    trends = []
    
    for i in range(len(df)):
        close = df['Close'].iloc[i]
        sh = df['SwingHighLevel'].iloc[i]
        sl = df['SwingLowLevel'].iloc[i]
        
        signal = ""
        
        if trend == 1:
            if not pd.isna(sh) and close > sh and last_sh != sh:
                signal = "Bullish BOS"
                last_sh = sh
            elif not pd.isna(sl) and close < sl and last_sl != sl:
                signal = "Bearish CHoCH"
                trend = -1
                last_sl = sl
        else:
            if not pd.isna(sl) and close < sl and last_sl != sl:
                signal = "Bearish BOS"
                last_sl = sl
            elif not pd.isna(sh) and close > sh and last_sh != sh:
                signal = "Bullish CHoCH"
                trend = 1
                last_sh = sh
                
        structure_signals.append(signal)
        trends.append(trend)
        
    df['Trend'] = trends
    df['Structure'] = structure_signals
    
    # 3. Fair Value Gaps (FVG)
    # Bullish FVG: Low of candle 3 > High of candle 1
    df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2)) & (df['Close'].shift(1) > df['Open'].shift(1))
    # Bearish FVG: High of candle 3 < Low of candle 1
    df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2)) & (df['Close'].shift(1) < df['Open'].shift(1))
    
    # FVG active status (price hasn't filled it)
    # Calculate top and bottom of FVG
    df['Bullish_FVG_Top'] = np.where(df['Bullish_FVG'], df['Low'], np.nan)
    df['Bullish_FVG_Bottom'] = np.where(df['Bullish_FVG'], df['High'].shift(2), np.nan)
    
    df['Bearish_FVG_Top'] = np.where(df['Bearish_FVG'], df['Low'].shift(2), np.nan)
    df['Bearish_FVG_Bottom'] = np.where(df['Bearish_FVG'], df['High'], np.nan)
    
    return df

def get_fibonacci_levels(high: float, low: float, trend: int = 1):
    """Calculate standard Fibonacci retracement levels."""
    diff = high - low
    levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    fib = {}
    if trend == 1: # Uptrend, retracing down
        for l in levels:
            fib[f"Fib_{l}"] = high - (diff * l)
    else: # Downtrend, retracing up
        for l in levels:
            fib[f"Fib_{l}"] = low + (diff * l)
            
    fib["Fib_0"] = high if trend == 1 else low
    fib["Fib_1"] = low if trend == 1 else high
    return fib

def get_pivot_points(high: float, low: float, close: float):
    """Standard Pivot Points (Floor)"""
    p = (high + low + close) / 3
    return {
        "Pivot": p,
        "R1": (2 * p) - low,
        "S1": (2 * p) - high,
        "R2": p + (high - low),
        "S2": p - (high - low),
        "R3": high + 2 * (p - low),
        "S3": low - 2 * (high - p)
    }
