"""
NSE Nifty 500 — Stock Data Pipeline (v2)
Features:
  • Full Nifty 500 list (download + cache + hardcoded fallback)
  • Multi-timeframe support (5m / 15m / 1h / 4h / Daily / Weekly)
  • Volume analysis (Relative Volume, OBV, Volume SMA)
  • Volume-aware signal engine
"""

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import math
import os
import requests
import time
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = BASE_DIR / "nifty500_cache.csv"

# ---------------------------------------------------------------------------
# Timeframe definitions  (yfinance interval → period → resample rule)
# ---------------------------------------------------------------------------
TIMEFRAMES = {
    "5 Min":  {"interval": "5m",  "period": "5d",   "resample": None},
    "15 Min": {"interval": "15m", "period": "60d",  "resample": None},
    "1 Hour": {"interval": "1h",  "period": "180d", "resample": None},
    "4 Hour": {"interval": "1h",  "period": "365d", "resample": "4h"},
    "Daily":  {"interval": "1d",  "period": "1y",   "resample": None},
    "Weekly": {"interval": "1wk", "period": "2y",   "resample": None},
}

# ---------------------------------------------------------------------------
# Hardcoded fallback — top ~200 Nifty 500 constituents by market-cap
# ---------------------------------------------------------------------------
NIFTY500_FALLBACK = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "ITC", "SBIN", "BHARTIARTL", "LT", "KOTAKBANK", "AXISBANK",
    "BAJFINANCE", "ASIANPAINT", "MARUTI", "HCLTECH", "SUNPHARMA",
    "TITAN", "WIPRO", "ULTRACEMCO", "NESTLEIND", "TECHM", "NTPC",
    "POWERGRID", "TATAMOTORS", "M&M", "ONGC", "ADANIENT", "ADANIPORTS",
    "BAJAJFINSV", "COALINDIA", "DRREDDY", "DIVISLAB", "GRASIM",
    "JSWSTEEL", "TATASTEEL", "CIPLA", "EICHERMOT", "BPCL", "HEROMOTOCO",
    "APOLLOHOSP", "TATACONSUM", "BRITANNIA", "INDUSINDBK", "HINDALCO",
    "SBILIFE", "HDFCLIFE", "DABUR", "GODREJCP", "PIDILITIND",
    "BERGEPAINT", "HAVELLS", "SIEMENS", "MARICO", "AMBUJACEM",
    "ACC", "COLPAL", "BALKRISIND", "BIOCON", "MCDOWELL-N",
    "CONCOR", "DLF", "GAIL", "INDIGO", "LUPIN", "MUTHOOTFIN",
    "NAUKRI", "PEL", "PETRONET", "TATAPOWER", "TORNTPHARM",
    "VOLTAS", "ZYDUSLIFE", "ABBOTINDIA", "ALKEM", "ATUL",
    "AUROPHARMA", "BANDHANBNK", "BEL", "CANBK", "CHOLAFIN",
    "CUMMINSIND", "ESCORTS", "FEDERALBNK", "FORTIS", "GLAXO",
    "GMRINFRA", "HINDPETRO", "ICICIPRULI", "IDFCFIRSTB", "IGL",
    "IRCTC", "JINDALSTEL", "JUBLFOOD", "LICHSGFIN", "LTF",
    "LTIM", "MFSL", "MGL", "MOTHERSON", "MPHASIS",
    "NAM-INDIA", "OBEROIRLTY", "OFSS", "PAGEIND", "PIIND",
    "PNB", "POLYCAB", "PVRINOX", "RAMCOCEM", "RECLTD",
    "SBICARD", "SHREECEM", "SRF", "STAR", "SUNTV",
    "TATACOMM", "TATAELXSI", "TATACHEM", "TRENT", "UNIONBANK",
    "UPL", "VEDL", "WHIRLPOOL", "ZEEL", "BANKBARODA",
    "CANFINHOME", "CROMPTON", "DALBHARAT", "DEEPAKNTR", "DIXON",
    "HAL", "HONAUT", "IDBI", "INDUSTOWER", "IOC",
    "IPCALAB", "JSL", "KPITTECH", "LALPATHLAB", "LAURUSLABS",
    "LTTS", "MANAPPURAM", "MAXHEALTH", "MCX", "METROBRAND",
    "MSUMI", "NATIONALUM", "NAVINFLUOR", "NMDC", "PRESTIGE",
    "SAIL", "SONACOMS", "SUMICHEM", "SYNGENE", "THERMAX",
    "TORNTPOWER", "TVSMOTOR", "UBL", "VBL", "VINATIORGA",
    "YESBANK", "ZOMATO", "ADANIGREEN", "ADANIPOWER", "ATGL",
    "AWL", "CAMS", "CDSL", "CLEAN", "COFORGE",
    "DELHIVERY", "DEVYANI", "FACT", "FINEORG", "FSL",
    "GRINDWELL", "HAPPSTMNDS", "HUDCO", "IIFL", "INDIANB",
    "IRB", "IRFC", "ITI", "JIOFIN", "JKCEMENT",
    "JSWENERGY", "KALYANKJIL", "KEI", "KEC", "LICI",
    "LODHA", "MAZDOCK", "NHPC", "NLCINDIA", "PAYTM",
    "PFC", "PHOENIXLTD", "POLICYBZR", "POONAWALLA", "RAJESHEXPO",
    "RVNL", "SOLARINDS", "SUNDARMFIN", "SUPREMEIND", "SYRMA",
    "TIINDIA", "TRIDENT", "UNOMINDA",
]


def _safe_round(value, decimals=2):
    """Round a value safely, returning None for NaN / None."""
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
        return round(value, decimals)
    except (TypeError, ValueError):
        return None


# ===================================================================
# NIFTY 500 LIST MANAGEMENT
# ===================================================================

def download_nifty500_from_nse() -> list[str]:
    """
    Try to download the live Nifty 500 constituent list from NSE India.
    Returns a plain list of ticker symbols (without .NS suffix).
    """
    try:
        session = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        }
        # Step 1: get cookies by visiting the homepage
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(0.5)

        # Step 2: fetch the index constituents
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        symbols = []
        for item in data.get("data", []):
            sym = item.get("symbol")
            if sym and sym != "NIFTY 500":
                symbols.append(sym)

        if symbols:
            # Cache to CSV
            pd.DataFrame({"Symbol": symbols}).to_csv(CACHE_FILE, index=False)
        return symbols

    except Exception as exc:
        print(f"[WARN] Could not download Nifty 500 from NSE: {exc}")
        return []


def get_nifty500_tickers(force_refresh: bool = False) -> list[str]:
    """
    Get the full Nifty 500 ticker list.
    Priority: 1) Cached CSV  2) Live download  3) Hardcoded fallback.
    Returns symbols WITHOUT the .NS suffix.
    """
    # Use cache if fresh (< 7 days old) and not forcing refresh
    if not force_refresh and CACHE_FILE.exists():
        age_days = (time.time() - CACHE_FILE.stat().st_mtime) / 86400
        if age_days < 7:
            try:
                df = pd.read_csv(CACHE_FILE)
                return df["Symbol"].tolist()
            except Exception:
                pass

    # Try live download
    symbols = download_nifty500_from_nse()
    if symbols:
        return symbols

    # Use cached file regardless of age
    if CACHE_FILE.exists():
        try:
            df = pd.read_csv(CACHE_FILE)
            return df["Symbol"].tolist()
        except Exception:
            pass

    # Last resort: hardcoded fallback
    return NIFTY500_FALLBACK


def add_ns_suffix(symbols: list[str]) -> list[str]:
    """Ensure each symbol ends with .NS for Yahoo Finance."""
    return [s if s.endswith(".NS") else f"{s}.NS" for s in symbols]


# ===================================================================
# DATA FETCHING — Multi-timeframe + Volume
# ===================================================================

def fetch_historical_data(
    ticker_symbol: str,
    timeframe: str = "Daily",
) -> pd.DataFrame:
    """
    Download OHLCV for a single ticker at the given timeframe,
    then append technical + volume indicators.
    """
    tf = TIMEFRAMES.get(timeframe, TIMEFRAMES["Daily"])
    stock = yf.Ticker(ticker_symbol)
    df = stock.history(period=tf["period"], interval=tf["interval"])

    if df.empty:
        return pd.DataFrame()

    # Resample if needed (e.g. 1h → 4h)
    if tf["resample"]:
        df = _resample(df, tf["resample"])

    # ── Technical indicators ──
    df.ta.rsi(length=14, append=True)
    # For intraday, 50 & 200 period SMAs may not have enough bars;
    # calculate what's available
    if len(df) >= 50:
        df.ta.sma(length=50, append=True)
    if len(df) >= 200:
        df.ta.sma(length=200, append=True)
    df.ta.macd(append=True)
    df.ta.ema(length=20, append=True)

    # ── Volume indicators ──
    vol_sma_len = min(20, max(5, len(df) // 3))
    df["Volume_SMA"] = df["Volume"].rolling(window=vol_sma_len).mean()
    df["Relative_Volume"] = df["Volume"] / df["Volume_SMA"]
    df["OBV"] = (df["Volume"] * ((df["Close"] > df["Close"].shift(1)).astype(int) * 2 - 1)).cumsum()
    # VWAP (intraday-style, calculated as cumulative)
    df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()

    # ── SMC & Pivot/Fib calculations ──
    df = _add_smc_features(df)
    
    return df


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample OHLCV data to a coarser timeframe."""
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    resampled = df.resample(rule).agg(agg).dropna(subset=["Close"])
    return resampled


def _add_smc_features(df: pd.DataFrame, swing_length: int = 5) -> pd.DataFrame:
    """Calculate Smart Money Concepts (Swing structure, BOS, CHoCH, FVG, OB)."""
    if len(df) < swing_length * 2 + 1:
        return df

    # 1. Swing Highs & Lows
    df['SwingHigh'] = df['High'].rolling(window=2*swing_length+1, center=True).max() == df['High']
    df['SwingLow'] = df['Low'].rolling(window=2*swing_length+1, center=True).min() == df['Low']
    
    df['SwingHighLevel'] = np.where(df['SwingHigh'], df['High'], np.nan)
    df['SwingLowLevel'] = np.where(df['SwingLow'], df['Low'], np.nan)
    
    # Fill forward so we know current structure (shifted by length to avoid lookahead bias)
    df['SwingHighLevel'] = df['SwingHighLevel'].shift(swing_length).ffill()
    df['SwingLowLevel'] = df['SwingLowLevel'].shift(swing_length).ffill()

    # 2. Fair Value Gaps (FVG)
    # Bullish FVG: Low of candle 3 > High of candle 1
    df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2)) & (df['Close'].shift(1) > df['Open'].shift(1))
    # Bearish FVG: High of candle 3 < Low of candle 1
    df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2)) & (df['Close'].shift(1) < df['Open'].shift(1))
    
    # 3. Basic Market Structure
    trend = 1
    last_sh = np.nan
    last_sl = np.nan
    signals = []
    
    for i in range(len(df)):
        close = df['Close'].iloc[i]
        sh = df['SwingHighLevel'].iloc[i]
        sl = df['SwingLowLevel'].iloc[i]
        
        sig = ""
        if trend == 1:
            if not pd.isna(sh) and close > sh and last_sh != sh:
                sig = "Bullish_BOS"
                last_sh = sh
            elif not pd.isna(sl) and close < sl and last_sl != sl:
                sig = "Bearish_CHoCH"
                trend = -1
                last_sl = sl
        else:
            if not pd.isna(sl) and close < sl and last_sl != sl:
                sig = "Bearish_BOS"
                last_sl = sl
            elif not pd.isna(sh) and close > sh and last_sh != sh:
                sig = "Bullish_CHoCH"
                trend = 1
                last_sh = sh
        signals.append(sig)
        
    df['SMC_Signal'] = signals
    return df


def calculate_pivot_points(df: pd.DataFrame) -> dict:
    """Standard Pivot Points (Floor) based on last closed bar."""
    if len(df) < 2: return {}
    # Use the previous bar's HLC for today's pivots
    prev = df.iloc[-2]
    high = prev.get("High", 0)
    low = prev.get("Low", 0)
    close = prev.get("Close", 0)
    
    if high == 0 or low == 0: return {}
    p = (high + low + close) / 3
    return {
        "Pivot": _safe_round(p),
        "R1": _safe_round((2 * p) - low),
        "S1": _safe_round((2 * p) - high),
        "R2": _safe_round(p + (high - low)),
        "S2": _safe_round(p - (high - low)),
        "R3": _safe_round(high + 2 * (p - low)),
        "S3": _safe_round(low - 2 * (high - p))
    }


def calculate_fibonacci(df: pd.DataFrame) -> dict:
    """Calculate standard Fibonacci retracement levels for recent swing."""
    if len(df) < 20: return {}
    recent = df.tail(60) # Last 60 bars for local structure
    high = recent['High'].max()
    low = recent['Low'].min()
    
    diff = high - low
    if diff == 0: return {}
    
    current_price = df.iloc[-1]['Close']
    trend = 1 if current_price > (high + low)/2 else -1
    
    levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    fib = {"High": _safe_round(high), "Low": _safe_round(low)}
    
    if trend == 1:
        for l in levels: fib[f"Fib_{l}"] = _safe_round(high - (diff * l))
    else:
        for l in levels: fib[f"Fib_{l}"] = _safe_round(low + (diff * l))
        
    return fib


def fetch_fundamentals(ticker_symbol: str) -> dict:
    """Return a dict of key fundamental metrics."""
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    return {
        "Company Name": info.get("longName") or info.get("shortName") or ticker_symbol,
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "Market Cap": info.get("marketCap"),
        "Trailing P/E": _safe_round(info.get("trailingPE")),
        "Forward P/E": _safe_round(info.get("forwardPE")),
        "Debt-to-Equity": _safe_round(info.get("debtToEquity")),
        "Dividend Yield": _safe_round(info.get("dividendYield"), 4),
        "52w High": _safe_round(info.get("fiftyTwoWeekHigh")),
        "52w Low": _safe_round(info.get("fiftyTwoWeekLow")),
        "Book Value": _safe_round(info.get("bookValue")),
        "EPS (TTM)": _safe_round(info.get("trailingEps")),
    }


def extract_latest_technicals(df: pd.DataFrame) -> dict:
    """Pull latest row of technical + volume indicator values."""
    if df.empty:
        return {}
    latest = df.iloc[-1]
    return {
        "Last Price": _safe_round(latest.get("Close")),
        "RSI_14": _safe_round(latest.get("RSI_14")),
        "SMA_50": _safe_round(latest.get("SMA_50")),
        "SMA_200": _safe_round(latest.get("SMA_200")),
        "EMA_20": _safe_round(latest.get("EMA_20")),
        "MACD": _safe_round(latest.get("MACD_12_26_9")),
        "MACD_Signal": _safe_round(latest.get("MACDs_12_26_9")),
        "MACD_Hist": _safe_round(latest.get("MACDh_12_26_9")),
        "VWAP": _safe_round(latest.get("VWAP")),
        "Volume": int(latest.get("Volume", 0)),
        "Volume_SMA": _safe_round(latest.get("Volume_SMA")),
        "Relative_Volume": _safe_round(latest.get("Relative_Volume")),
        "OBV": _safe_round(latest.get("OBV"), 0),
        "SMC_Signal": latest.get("SMC_Signal", ""),
        "SwingHigh": _safe_round(latest.get("SwingHighLevel")),
        "SwingLow": _safe_round(latest.get("SwingLowLevel")),
        "Bullish_FVG": bool(latest.get("Bullish_FVG", False)),
        "Bearish_FVG": bool(latest.get("Bearish_FVG", False)),
    }

# ===================================================================
# SIGNAL ENGINE  (volume-aware)
# ===================================================================

def generate_signal(technicals: dict, fundamentals: dict) -> dict:
    """
    Volume-aware rule-based signal generator.
    Returns dict with 'action', 'reason', 'confidence', 'volume_note'.
    """
    rsi = technicals.get("RSI_14")
    sma50 = technicals.get("SMA_50")
    sma200 = technicals.get("SMA_200")
    price = technicals.get("Last Price")
    macd_hist = technicals.get("MACD_Hist")
    rel_vol = technicals.get("Relative_Volume")
    vwap = technicals.get("VWAP")

    if rsi is None or price is None:
        return {
            "action": "⏳ Insufficient Data",
            "reason": "Not enough data for indicators.",
            "confidence": 0,
            "volume_note": "N/A",
        }

    # Volume classification
    vol_str = "🔇 Low"
    vol_boost = 0
    if rel_vol is not None:
        if rel_vol >= 2.5:
            vol_str = "🔊 Spike (%.1fx)" % rel_vol
            vol_boost = 15
        elif rel_vol >= 1.5:
            vol_str = "📢 High (%.1fx)" % rel_vol
            vol_boost = 10
        elif rel_vol >= 0.8:
            vol_str = "🔈 Normal (%.1fx)" % rel_vol
            vol_boost = 0
        else:
            vol_str = "🔇 Low (%.1fx)" % rel_vol
            vol_boost = -10  # low volume = less conviction

    # VWAP position
    vwap_note = ""
    if vwap and price:
        if price > vwap:
            vwap_note = " Price above VWAP (bullish)."
        else:
            vwap_note = " Price below VWAP (bearish)."

    # ——— OVERSOLD BOUNCE ———
    if rsi < 30:
        conf = 70 + vol_boost
        reason = f"RSI at {rsi} — deep oversold.{vwap_note}"
        if rel_vol and rel_vol >= 1.5:
            reason = f"RSI at {rsi} oversold + volume surge ({rel_vol:.1f}x) confirms capitulation.{vwap_note}"
            conf += 5
        return {"action": "🟢 LONG (Oversold Bounce)", "reason": reason,
                "confidence": min(conf, 95), "volume_note": vol_str}

    # ——— DEATH CROSS / BEARISH ———
    if sma50 and sma200 and sma50 < sma200 and macd_hist and macd_hist < 0:
        conf = 65 + vol_boost
        reason = f"SMA50 ({sma50}) < SMA200 ({sma200}), MACD histogram negative.{vwap_note}"
        if rel_vol and rel_vol >= 1.5:
            reason = f"Bearish structure confirmed by heavy selling volume ({rel_vol:.1f}x).{vwap_note}"
            conf += 5
        return {"action": "🔴 AVOID / SELL", "reason": reason,
                "confidence": min(conf, 90), "volume_note": vol_str}

    # ——— GOLDEN CROSS / BULLISH ———
    if sma50 and sma200 and sma50 > sma200 and price > sma50:
        conf = 60 + vol_boost
        reason = f"Price above SMA50 ({sma50}) > SMA200 ({sma200}) — bullish alignment.{vwap_note}"
        if rel_vol and rel_vol >= 1.5:
            reason = f"Bullish trend confirmed by volume expansion ({rel_vol:.1f}x).{vwap_note}"
            conf += 5
        return {"action": "🟢 BUY (Trend Long)", "reason": reason,
                "confidence": min(conf, 90), "volume_note": vol_str}

    # ——— VOLUME BREAKOUT (price near SMA50 + volume spike) ———
    if sma50 and price and rel_vol:
        pct_from_sma = abs(price - sma50) / sma50 * 100
        if pct_from_sma < 2 and rel_vol >= 2.0:
            direction = "above" if price > sma50 else "below"
            return {
                "action": f"⚡ BREAKOUT ({'Long' if price > sma50 else 'Short'})",
                "reason": f"Price near SMA50 ({direction}) with {rel_vol:.1f}x volume spike — breakout imminent.{vwap_note}",
                "confidence": min(70 + vol_boost, 90),
                "volume_note": vol_str,
            }

    # ——— OVERBOUGHT ———
    if rsi > 70:
        conf = 55 + vol_boost
        reason = f"RSI at {rsi} — overbought, potential pullback.{vwap_note}"
        if rel_vol and rel_vol >= 1.5:
            reason = f"RSI {rsi} overbought + heavy volume may indicate distribution.{vwap_note}"
        return {"action": "🟡 CAUTION (Overbought)", "reason": reason,
                "confidence": min(conf, 85), "volume_note": vol_str}

    # ——— NEUTRAL / WATCHLIST ———
    reason = f"No strong directional signal. RSI {rsi}.{vwap_note}"
    return {"action": "👀 WATCHLIST", "reason": reason,
            "confidence": max(35 + vol_boost, 10), "volume_note": vol_str}


# ===================================================================
# MASTER FETCH
# ===================================================================

def fetch_single_stock(ticker: str, timeframe: str) -> tuple:
    try:
        df = fetch_historical_data(ticker, timeframe=timeframe)
        if df.empty:
            return ticker, {"error": f"No data returned"}

        fundamentals = fetch_fundamentals(ticker)
        technicals = extract_latest_technicals(df)
        signal = generate_signal(technicals, fundamentals)
        
        pivots = calculate_pivot_points(df)
        fibs = calculate_fibonacci(df)

        return ticker, {
            "Fundamentals": fundamentals,
            "Technicals": technicals,
            "Signal": signal,
            "Pivots": pivots,
            "Fibonacci": fibs,
            "History": df,
        }
    except Exception as exc:
        return ticker, {"error": str(exc)}

def fetch_all_stocks(tickers: list, timeframe: str = "Daily", progress_callback=None):
    """
    Fetch fundamentals + technicals + signal for each ticker at 'timeframe' via multithreading.
    """
    results = {}
    total = len(tickers)
    completed = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_stock, t, timeframe): t for t in tickers}
        
        for future in as_completed(futures):
            ticker, data = future.result()
            results[ticker] = data
            
            completed += 1
            if progress_callback:
                progress_callback(completed, total, ticker)

    return results


def results_to_json(results: dict) -> str:
    """Serialize results to JSON (History DataFrames excluded)."""
    export = {}
    for ticker, data in results.items():
        if "error" in data:
            export[ticker] = {"error": data["error"]}
        else:
            export[ticker] = {
                "Fundamentals": data["Fundamentals"],
                "Technicals": data["Technicals"],
                "Signal": data["Signal"],
            }
    return json.dumps(export, indent=4, default=str)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Fetching Nifty 500 list …")
    symbols = get_nifty500_tickers()
    print(f"  → {len(symbols)} tickers loaded")

    # For CLI demo, just scan 5 stocks
    test = add_ns_suffix(symbols[:5])
    print(f"\n  Scanning {test} on Daily …")
    data = fetch_all_stocks(
        test,
        timeframe="Daily",
        progress_callback=lambda c, t, tk: print(f"  [{c}/{t}] {tk}"),
    )
    json_str = results_to_json(data)
    print("\n--- Data ---")
    print(json_str)

    with open("stock_data.json", "w") as f:
        f.write(json_str)
    print("✅  Saved to stock_data.json")
