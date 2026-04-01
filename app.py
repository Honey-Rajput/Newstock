"""
NSE Stock Agent — Streamlit Dashboard (v2)
Features:
  • Full Nifty 500 universe with search/filter
  • Multi-timeframe charting (5m / 15m / 1h / 4h / Daily / Weekly)
  • Volume analysis panel (Relative Volume, OBV, VWAP)
  • Interactive Plotly candlestick + volume charts
  • Signal summary with volume confirmation
Run:  streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json

from fetch_stock_data import (
    TIMEFRAMES,
    get_nifty500_tickers,
    add_ns_suffix,
    fetch_all_stocks,
    fetch_historical_data,
    fetch_fundamentals,
    extract_latest_technicals,
    generate_signal,
    results_to_json,
)

# ──────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Stock Agent — Nifty 500",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Premium dark CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Main background: deep charcoal with subtle warm undertone ── */
.stApp {
    background: linear-gradient(160deg, #0d1117 0%, #161b22 50%, #1c2333 100%);
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: rgba(13,17,23,0.97);
    border-right: 1px solid rgba(48,54,61,0.8);
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 { color: #e6edf3; }

/* metric cards */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(22,27,34,0.9), rgba(13,17,23,0.7));
    border: 1px solid rgba(48,54,61,0.6);
    border-radius: 12px;
    padding: 16px 18px;
    backdrop-filter: blur(12px);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(45,212,191,0.1);
    border-color: rgba(45,212,191,0.3);
}
div[data-testid="stMetric"] label {
    color: #8b949e !important; font-weight: 500 !important;
    font-size: 0.78rem !important; letter-spacing: 0.05em; text-transform: uppercase;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #e6edf3 !important; font-weight: 700 !important; font-size: 1.35rem !important;
}

/* tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid rgba(48,54,61,0.6); }
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 8px 8px 0 0;
    color: #8b949e; font-weight: 500; padding: 10px 20px; transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: rgba(45,212,191,0.08) !important;
    color: #2dd4bf !important; border-bottom: 2px solid #2dd4bf;
}

/* buttons — teal-to-emerald gradient */
.stButton > button {
    background: linear-gradient(135deg, #0d9488 0%, #059669 100%);
    color: white; border: none; border-radius: 10px;
    padding: 0.55rem 1.8rem; font-weight: 600; font-size: 0.92rem;
    transition: all 0.25s ease; box-shadow: 0 4px 15px rgba(13,148,136,0.3);
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(13,148,136,0.45);
    background: linear-gradient(135deg, #14b8a6 0%, #10b981 100%);
}

/* signal badges */
.signal-badge {
    display: inline-block; padding: 5px 14px; border-radius: 20px;
    font-weight: 600; font-size: 0.85rem; letter-spacing: 0.02em;
}
.signal-buy    { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.signal-sell   { background: rgba(239,68,68,0.15);  color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.signal-watch  { background: rgba(234,179,8,0.15);  color: #facc15; border: 1px solid rgba(234,179,8,0.3); }
.signal-caution{ background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.signal-break  { background: rgba(56,189,248,0.15); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3); }
.signal-nodata { background: rgba(139,148,158,0.10); color: #8b949e; border: 1px solid rgba(139,148,158,0.2); }

/* volume badge */
.vol-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 500;
}
.vol-spike  { background: rgba(239,68,68,0.18); color: #fca5a5; }
.vol-high   { background: rgba(245,158,11,0.15); color: #fcd34d; }
.vol-normal { background: rgba(139,148,158,0.1);  color: #8b949e; }
.vol-low    { background: rgba(75,85,99,0.1);     color: #6b7280; }

/* glass card */
.glass-card {
    background: rgba(22,27,34,0.6); border: 1px solid rgba(48,54,61,0.5);
    border-radius: 12px; padding: 20px 24px; backdrop-filter: blur(10px); margin-bottom: 14px;
    transition: border-color 0.2s;
}
.glass-card:hover { border-color: rgba(45,212,191,0.25); }
.glass-card h3 { color: #e6edf3; margin: 0 0 8px; font-size: 1.02rem; font-weight: 600; }
.glass-card p, .glass-card span { color: #b1bac4; font-size: 0.88rem; }

/* header banner */
.header-banner {
    background: linear-gradient(135deg, rgba(13,148,136,0.1) 0%, rgba(5,150,105,0.06) 50%, rgba(234,179,8,0.04) 100%);
    border: 1px solid rgba(45,212,191,0.15); border-radius: 14px;
    padding: 26px 34px; margin-bottom: 22px;
}
.header-banner h1 {
    margin: 0 0 4px; font-size: 1.9rem;
    background: linear-gradient(135deg, #5eead4, #2dd4bf, #fbbf24);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;
}
.header-banner p { color: #8b949e; margin: 0; font-size: 0.92rem; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def signal_badge(action: str) -> str:
    a = action.lower()
    if "buy" in a or "long" in a:
        cls = "signal-buy"
    elif "avoid" in a or "sell" in a:
        cls = "signal-sell"
    elif "breakout" in a:
        cls = "signal-break"
    elif "caution" in a or "overbought" in a:
        cls = "signal-caution"
    elif "watch" in a:
        cls = "signal-watch"
    else:
        cls = "signal-nodata"
    return f'<span class="signal-badge {cls}">{action}</span>'


def vol_badge(vol_note: str) -> str:
    v = vol_note.lower()
    if "spike" in v:
        cls = "vol-spike"
    elif "high" in v:
        cls = "vol-high"
    elif "normal" in v:
        cls = "vol-normal"
    else:
        cls = "vol-low"
    return f'<span class="vol-badge {cls}">{vol_note}</span>'


def fmt_mcap(val):
    if val is None: return "N/A"
    if val >= 1e12: return f"₹{val/1e12:.2f}T"
    if val >= 1e9:  return f"₹{val/1e9:.2f}B"
    if val >= 1e7:  return f"₹{val/1e7:.2f}Cr"
    return f"₹{val:,.0f}"


def fmt_vol(val):
    if val is None: return "N/A"
    if val >= 1e7: return f"{val/1e7:.2f}Cr"
    if val >= 1e5: return f"{val/1e5:.2f}L"
    if val >= 1e3: return f"{val/1e3:.1f}K"
    return str(int(val))


def build_candlestick_chart(df, ticker, show_vwap=True, fibs=None, pivots=None):
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        row_heights=[0.50, 0.25, 0.25],
        subplot_titles=("", "Volume", "MACD"),
    )
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color="#22c55e", decreasing_line_color="#ef4444",
        increasing_fillcolor="#22c55e", decreasing_fillcolor="#ef4444",
        name="Price",
    ), row=1, col=1)

    # ── SMC Fair Value Gaps (FVG) ──
    # If historical dataframe has FVG columns, draw rectangles for active ones
    if "Bullish_FVG" in df.columns:
        last_bars = df.tail(10)
        for i, row in last_bars.iterrows():
            if row.get("Bullish_FVG"):
                fig.add_hrect(y0=row["High"], y1=row["Low"], line_width=0, fillcolor="rgba(34,197,94,0.1)", row=1, col=1)
            elif row.get("Bearish_FVG"):
                fig.add_hrect(y0=row["High"], y1=row["Low"], line_width=0, fillcolor="rgba(239,68,68,0.1)", row=1, col=1)

    # SMA overlays
    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_50"], name="SMA 50",
            line=dict(color="#fbbf24", width=1.5)), row=1, col=1)
    if "SMA_200" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_200"], name="SMA 200",
            line=dict(color="#818cf8", width=1.5)), row=1, col=1)
    if "EMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["EMA_20"], name="EMA 20",
            line=dict(color="#f472b6", width=1, dash="dot")), row=1, col=1)

    # ── Fibonacci & Pivots ──
    if fibs:
        for level, val in fibs.items():
            if "Fib_0.5" in level:
                color = "rgba(45,212,191,0.7)"
            else:
                color = "rgba(148,163,184,0.4)"
            fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=level, annotation_font_color=color, row=1, col=1)
            
    if pivots:
        colors = {"R1": "#fca5a5", "R2": "#f87171", "R3": "#ef4444", "S1": "#86efac", "S2": "#4ade80", "S3": "#22c55e", "Pivot": "#93c5fd"}
        for level, val in pivots.items():
            fig.add_hline(y=val, line_dash="dot", line_color=colors.get(level, "#ffffff"), annotation_text=level, annotation_position="left", annotation_font_size=9, row=1, col=1)

    # VWAP
    if show_vwap and "VWAP" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["VWAP"], name="VWAP",
            line=dict(color="#22d3ee", width=1.5, dash="dash")), row=1, col=1)

    # ── Volume bars (color-coded by relative volume) ──
    vol_colors = []
    for i in range(len(df)):
        rv = df["Relative_Volume"].iloc[i] if "Relative_Volume" in df.columns else 1
        close_chg = df["Close"].iloc[i] >= df["Open"].iloc[i]
        if pd.isna(rv):
            rv = 1
        if rv >= 2.5:
            vol_colors.append("#ef4444" if not close_chg else "#22c55e")  # bright = spike
        elif rv >= 1.5:
            vol_colors.append("#f97316" if not close_chg else "#4ade80")
        else:
            vol_colors.append("rgba(239,68,68,0.35)" if not close_chg else "rgba(34,197,94,0.35)")

    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="Volume",
        marker_color=vol_colors, opacity=0.85,
    ), row=2, col=1)
    # Volume SMA overlay
    if "Volume_SMA" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Volume_SMA"], name="Vol SMA",
            line=dict(color="#fbbf24", width=1.2, dash="dot")), row=2, col=1)

    # ── MACD ──
    if "MACD_12_26_9" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_12_26_9"], name="MACD",
            line=dict(color="#22d3ee", width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACDs_12_26_9"], name="Signal",
            line=dict(color="#f472b6", width=1.5)), row=3, col=1)
        hist_colors = ["#22c55e" if v >= 0 else "#ef4444"
                       for v in df["MACDh_12_26_9"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACDh_12_26_9"], name="Histogram",
            marker_color=hist_colors, opacity=0.5), row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#e2e8f0"),
        height=680, margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        xaxis_rangeslider_visible=False,
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)",
                         zerolinecolor="rgba(255,255,255,0.06)", row=i, col=1)
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.04)",
                         zerolinecolor="rgba(255,255,255,0.06)", row=i, col=1)
    return fig


def build_rsi_chart(df):
    fig = go.Figure()
    if "RSI_14" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI_14"], name="RSI 14",
            line=dict(color="#a78bfa", width=2),
            fill="tozeroy", fillcolor="rgba(167,139,250,0.08)"))
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(239,68,68,0.5)",
                      annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(34,197,94,0.5)",
                      annotation_text="Oversold (30)")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#e2e8f0"),
        height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        yaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.04)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
    )
    return fig


def build_obv_chart(df):
    fig = go.Figure()
    if "OBV" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["OBV"], name="OBV",
            line=dict(color="#38bdf8", width=2),
            fill="tozeroy", fillcolor="rgba(56,189,248,0.06)"))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#e2e8f0"),
        height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
    )
    return fig


def build_relative_volume_chart(df):
    fig = go.Figure()
    if "Relative_Volume" in df.columns:
        rv = df["Relative_Volume"].fillna(1)
        colors = ["#ef4444" if v >= 2.5 else "#f97316" if v >= 1.5
                  else "#22c55e" if v >= 0.8 else "#64748b" for v in rv]
        fig.add_trace(go.Bar(
            x=df.index, y=rv, name="Relative Volume",
            marker_color=colors, opacity=0.8))
        fig.add_hline(y=1.0, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                      annotation_text="Avg")
        fig.add_hline(y=2.0, line_dash="dash", line_color="rgba(239,68,68,0.4)",
                      annotation_text="Spike")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#e2e8f0"),
        height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
    )
    return fig


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    # ── Load Nifty 500 ──
    if "nifty500_list" not in st.session_state:
        with st.spinner("Loading Nifty 500 list …"):
            st.session_state["nifty500_list"] = get_nifty500_tickers()

    all_symbols = st.session_state["nifty500_list"]

    # ── Stock Selection ──
    st.markdown("### 🔍 Stock Selection")
    selected_symbols = st.multiselect(
        "Select specific stocks (optional)",
        options=all_symbols,
        default=[],
        help="Leave empty to scan all 500 stocks. Or select specific tickers for instant analysis."
    )
    tickers = add_ns_suffix(selected_symbols) if selected_symbols else add_ns_suffix(all_symbols)
    
    if selected_symbols:
        st.markdown(f"**{len(tickers)}** custom stocks queued")
    else:
        st.markdown(f"**{len(tickers)}** stocks (Full Nifty 500) queued")
    st.markdown("---")

    # ── Scan timeframe (for batch scan) ──
    scan_tf = st.selectbox("📊 Scan Timeframe", list(TIMEFRAMES.keys()), index=4)

    st.markdown("---")
    btn_text = "🚀  Scan Selected" if selected_symbols else "🚀  Scan All Nifty 500"
    scan_btn = st.button(btn_text, width="stretch")

    st.markdown("---")
    st.markdown(
        "<p style='color:#64748b; font-size:0.76rem; text-align:center;'>"
        "⚠️ Not financial advice. Past performance ≠ future results.<br>"
        "Always use strict stop-losses.</p>",
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
st.markdown("""
<div class="header-banner">
    <h1>📈 NSE Stock Agent — Nifty 500</h1>
    <p>Quantitative analysis dashboard with multi-timeframe charting &amp; volume-confirmed signals</p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SCAN
# ──────────────────────────────────────────────
if scan_btn and tickers:
    progress_bar = st.progress(0, text="Initializing scanner …")

    def on_progress(cur, total, ticker):
        progress_bar.progress(cur / total, text=f"Fetching {ticker} ({cur}/{total})")

    with st.spinner(""):
        results = fetch_all_stocks(tickers, timeframe=scan_tf, progress_callback=on_progress)

    progress_bar.empty()
    st.session_state["results"] = results
    st.session_state["scan_tickers"] = tickers
    st.session_state["scan_timeframe"] = scan_tf
    st.toast("✅ Scan complete!", icon="🎉")


# ──────────────────────────────────────────────
# DISPLAY RESULTS
# ──────────────────────────────────────────────
if "results" in st.session_state:
    results = st.session_state["results"]

    valid = {k: v for k, v in results.items() if "error" not in v}
    errors = {k: v for k, v in results.items() if "error" in v}

    buy_count = sum(1 for v in valid.values()
                    if "buy" in v["Signal"]["action"].lower() or "long" in v["Signal"]["action"].lower())
    sell_count = sum(1 for v in valid.values()
                    if "sell" in v["Signal"]["action"].lower() or "avoid" in v["Signal"]["action"].lower())
    watch_count = sum(1 for v in valid.values() if "watch" in v["Signal"]["action"].lower())
    caution_count = sum(1 for v in valid.values() if "caution" in v["Signal"]["action"].lower())
    breakout_count = sum(1 for v in valid.values() if "breakout" in v["Signal"]["action"].lower())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Scanned", len(valid))
    c2.metric("🟢 Buy", buy_count)
    c3.metric("🔴 Sell", sell_count)
    c4.metric("⚡ Breakout", breakout_count)
    c5.metric("🟡 Caution", caution_count)
    c6.metric("👀 Watch", watch_count)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── TABS ──
    tab_overview, tab_analysis, tab_smc, tab_volume, tab_chartink = st.tabs([
        "🌐 Market Scanner", "🔍 Individual Analysis", "🧠 SMC Screener", "📊 Volume", "🎯 Trade Planner"
    ])

    # ═══════════ TAB 1: OVERVIEW ═══════════
    with tab_overview:
        
        st.markdown("### 🎛️ Filter Results")
        filter_col1, filter_col2 = st.columns([1, 3])
        with filter_col1:
            available_signals = ["All", "Buy / Long", "Sell / Avoid", "Watchlist", "Caution", "Breakout"]
            selected_signal = st.selectbox("Filter by Signal Category", available_signals, index=0)
        
        rows = []
        for ticker, data in valid.items():
            t = data["Technicals"]
            f = data["Fundamentals"]
            s = data["Signal"]
            
            sig_action = s["action"].lower()
            if selected_signal != "All":
                if selected_signal == "Buy / Long" and ("buy" not in sig_action and "long" not in sig_action): continue
                if selected_signal == "Sell / Avoid" and ("sell" not in sig_action and "avoid" not in sig_action): continue
                if selected_signal == "Watchlist" and "watch" not in sig_action: continue
                if selected_signal == "Caution" and "caution" not in sig_action: continue
                if selected_signal == "Breakout" and "breakout" not in sig_action: continue

            rows.append({
                "Ticker": ticker.replace(".NS", ""),
                "Chart": f"https://in.tradingview.com/chart/?symbol=NSE:{ticker.replace('.NS', '')}",
                "Price (₹)": t.get("Last Price"),
                "RSI": t.get("RSI_14"),
                "SMA 50": t.get("SMA_50"),
                "Rel Vol": t.get("Relative_Volume"),
                "P/E": f.get("Trailing P/E"),
                "Signal": s["action"],
                "Conf %": s["confidence"],
                "Reason": s.get("reason", ""),
                "SMC": t.get("SMC_Signal", ""),
                "FVG": "Bull" if t.get("Bullish_FVG") else ("Bear" if t.get("Bearish_FVG") else ""),
            })
        summary_df = pd.DataFrame(rows)
        if not summary_df.empty:
            cols = ["Ticker", "Chart", "Price (₹)", "RSI", "SMA 50", "Rel Vol", "P/E", "Signal", "Conf %", "Reason", "SMC", "FVG"]
            summary_df = summary_df[cols]
            st.dataframe(
                summary_df.style.format({
                    "Price (₹)": "₹{:,.2f}", "RSI": "{:.1f}",
                    "SMA 50": "₹{:,.1f}", "SMA 200": "₹{:,.1f}",
                    "MACD H": "{:.2f}", "Rel Vol": "{:.1f}x",
                    "VWAP": "₹{:,.1f}", "P/E": "{:.1f}", "Conf %": "{}%",
                }, na_rep="—").set_properties(**{'text-align': 'left'}),
                column_config={"Chart": st.column_config.LinkColumn("Chart", display_text="📈 View")},
                width="stretch",
                height=min(42 * len(rows) + 40, 600)
            )
        else:
            st.info("No stocks match the selected filter criteria.")

        # Signal cards
        st.markdown("### 🎯 Signal Summary")
        card_cols = st.columns(min(len(valid), 4) if valid else 1)
        for idx, (ticker, data) in enumerate(valid.items()):
            with card_cols[idx % len(card_cols)]:
                sig = data["Signal"]
                st.markdown(
                    f"""<div class="glass-card">
                        <h3>{ticker.replace('.NS','')}</h3>
                        {signal_badge(sig['action'])}
                        &nbsp;{vol_badge(sig.get('volume_note',''))}
                        <p style="margin-top:8px;">{sig['reason']}</p>
                        <p style="font-size:0.76rem; color:#64748b;">Confidence: {sig['confidence']}%</p>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ═══════════ TAB 2: INDIVIDUAL ANALYSIS ═══════════
    with tab_analysis:
        valid_tickers = list(valid.keys())
        if not valid_tickers:
            st.info("Run a scan first.")
        else:
            sel_col, tf_col = st.columns([2, 3])
            with sel_col:
                selected = st.selectbox("Select Stock", valid_tickers,
                                        format_func=lambda x: x.replace(".NS", ""))
            with tf_col:
                detail_tf = st.select_slider(
                    "⏱️ Timeframe",
                    options=list(TIMEFRAMES.keys()),
                    value=st.session_state.get("scan_timeframe", "Daily"),
                )

            # Fetch data using multithread helper signature logic (or direct)
            # We already have data if timeframe matches
            scan_tf_used = st.session_state.get("scan_timeframe", "Daily")
            if detail_tf != scan_tf_used:
                with st.spinner(f"Loading {detail_tf} data for {selected} …"):
                    from fetch_stock_data import fetch_single_stock
                    _, sd = fetch_single_stock(selected, timeframe=detail_tf)
            else:
                sd = valid[selected]

            if "error" in sd:
                st.error("Failed to load requested timeframe.")
            else:
                hist = sd["History"]
                tech = sd["Technicals"]
                fund = sd["Fundamentals"]
                sig = sd["Signal"]
                pivots = sd.get("Pivots", {})
                fibs = sd.get("Fibonacci", {})

                # AI Summary Predictor String Generation
                ai_sum = []
                if tech.get("SMC_Signal"): ai_sum.append(f"Structure shift ({tech['SMC_Signal']}) detected.")
                if fibs and "Fib_0.5" in fibs and tech["Last Price"] > fibs["Fib_0.5"]:
                    ai_sum.append("Price holding above 50% Fib retracement (Bullish).")
                elif fibs and "Fib_0.5" in fibs:
                    ai_sum.append("Price below 50% Fib retracement (Bearish).")
                if tech.get("Relative_Volume", 0) > 1.5: ai_sum.append("Strong volume confirms immediate momentum.")
                ai_text = " ".join(ai_sum) if ai_sum else "Consolidating or trend lacks confirmation."

                # TradingView Link
                clean_ticker = selected.replace('.NS', '')
                tv_url = f"https://in.tradingview.com/chart/?symbol=NSE:{clean_ticker}"

                # Pivot Strategy Recommendation
                trade_plan = ""
                if pivots:
                    p = pivots.get("Pivot", "—")
                    r1, r2, r3 = pivots.get("R1", "—"), pivots.get("R2", "—"), pivots.get("R3", "—")
                    s1, s2, s3 = pivots.get("S1", "—"), pivots.get("S2", "—"), pivots.get("S3", "—")
                    action = sig["action"].lower()
                    
                    levels_html = (
                        f'<div style="display:flex; gap:12px; margin-top:16px; font-size:0.85rem; width:100%;">'
                        f'<div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); padding:10px; border-radius:6px; flex:1;">'
                        f'<span style="color:#fca5a5; font-weight:600;">Resistances (Targets)</span><br><span style="color:#ef4444;">R3:</span> ₹{r3}<br><span style="color:#f87171;">R2:</span> ₹{r2}<br><span style="color:#fca5a5;">R1:</span> ₹{r1}'
                        f'</div>'
                        f'<div style="background:rgba(148,163,184,0.1); border:1px solid rgba(148,163,184,0.2); padding:10px; border-radius:6px; text-align:center; display:flex; flex-direction:column; justify-content:center;">'
                        f'<span style="color:#94a3b8; font-weight:600;">Pivot (Median)</span><br><span style="color:#e2e8f0; font-weight:bold; font-size:1.1rem;">₹{p}</span>'
                        f'</div>'
                        f'<div style="background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.2); padding:10px; border-radius:6px; flex:1;">'
                        f'<span style="color:#86efac; font-weight:600;">Supports (Stops)</span><br><span style="color:#86efac;">S1:</span> ₹{s1}<br><span style="color:#4ade80;">S2:</span> ₹{s2}<br><span style="color:#22c55e;">S3:</span> ₹{s3}'
                        f'</div></div>'
                    )

                    if "buy" in action or "long" in action or "breakout" in action:
                        trade_plan = f"<div><br><span style='color:#4ade80;'>🟢 <strong>Actionable Buy Plan:</strong></span> Wait for entry on dips near Support (S1: <strong>₹{s1}</strong> or Pivot: <strong>₹{p}</strong>). First target zone maps to R1 (<strong>₹{r1}</strong>) and R2 (<strong>₹{r2}</strong>). Keep a strict Stop Loss below S2 (<strong>₹{s2}</strong>).</div>{levels_html}"
                    elif "sell" in action or "avoid" in action:
                        trade_plan = f"<div><br><span style='color:#f87171;'>🔴 <strong>Actionable Sell Plan:</strong></span> Trend is bearish. Ideal short entry is near Resistance (R1: <strong>₹{r1}</strong> or Pivot: <strong>₹{p}</strong>). Target downside to S1 (<strong>₹{s1}</strong>) and S2 (<strong>₹{s2}</strong>). Stop Loss above R2 (<strong>₹{r2}</strong>).</div>{levels_html}"
                    else:
                        trade_plan = f"<div><br><span style='color:#cbd5e1;'>🟡 <strong>Key Levels:</strong></span> Currently neutral. Watch for breakout above R1 (<strong>₹{r1}</strong>) to trigger a buy, or breakdown below S1 (<strong>₹{s1}</strong>) to trigger a short.</div>{levels_html}"

                # ── Header card ──
                st.markdown(
                    f"""<div style="background:linear-gradient(135deg, rgba(13,148,136,0.15) 0%, rgba(30,41,59,0.5) 100%);
                         border: 1px solid rgba(45,212,191,0.2); padding:20px; border-radius:12px; margin-bottom:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <h3 style="font-size:1.5rem; color:#5eead4; margin:0;">
                                    <a href="{tv_url}" target="_blank" style="color:#5eead4; text-decoration:none;">
                                        {fund.get('Company Name', selected)} 📊 <span style="font-size:0.9rem; color:#94a3b8;">(Open in TradingView)</span>
                                    </a>
                                </h3>
                                <p style="color:#94a3b8; font-size:0.9rem; margin-top:4px;">
                                    {fund.get('Sector')} · {fund.get('Industry')}
                                </p>
                            </div>
                            <div style="text-align:right;">
                                {signal_badge(sig['action'])}
                                <div style="font-size:1.4rem; font-weight:700; color:#f8fafc; margin-top:8px;">
                                    ₹{tech.get('Last Price','—')}
                                </div>
                            </div>
                        </div>
                        <div style="margin-top:16px; border-left:3px solid #f59e0b; padding-left:12px;">
                            <span style="font-weight:600; color:#fbbf24;">🤖 AI Analysis:</span> 
                            <span style="color:#cbd5e1;">{ai_text} {sig['reason']}</span>
                            {trade_plan}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # ── Main chart ──
                st.markdown(f"#### 📉 Technical Chart (with Pivots, Fibs, SMC)")
                if not hist.empty:
                    st.plotly_chart(build_candlestick_chart(hist, selected, fibs=fibs, pivots=pivots), width="stretch", key="detail_candle")
                else:
                    st.warning("No chart data.")

    # ═══════════ TAB 3: SMC SCREENER ═══════════
    with tab_smc:
        st.markdown("### 🧠 Smart Money Concepts Scanner")
        with st.expander("📖 Smart Money Glossary (What do these terms mean?)", expanded=False):
            st.markdown("""
            **Smart Money Concepts (SMC)** is an institutional trading framework that maps where heavy volume / institutional liquidity is actively pushing the market.
            
            * **BOS (Break of Structure):** Trend continuation. A Bullish BOS means the price smashed through a recent high, confirming institutions are continuing to push it up.
            * **CHoCH (Change of Character):** Trend reversal. A Bearish CHoCH means an uptrend just violently broke down past its most recent major 'support swing'. It's the first warning sign of a dump.
            * **FVG (Fair Value Gap / Imbalance):** A sudden, massive candle that leaves a literal 'gap' in the price action where normal buyers/sellers couldn't participate. These gaps act like highly radioactive magnets—price almost always gets sucked back into an FVG eventually to 'fill' the imbalance.
            """)
        
        smc_rows = []
        for ticker, data in valid.items():
            t = data["Technicals"]
            sig = t.get("SMC_Signal", "")
            fvg_bull = t.get("Bullish_FVG", False)
            fvg_bear = t.get("Bearish_FVG", False)
            
            if sig or fvg_bull or fvg_bear:
                smc_rows.append({
                    "Ticker": ticker.replace(".NS", ""),
                    "Chart": f"https://in.tradingview.com/chart/?symbol=NSE:{ticker.replace('.NS', '')}",
                    "Struct Shift": sig,
                    "FVG Found": "Bullish FVG" if fvg_bull else ("Bearish FVG" if fvg_bear else "None"),
                    "Volume Spike": "Yes" if t.get("Relative_Volume", 0) >= 1.5 else "No",
                    "Trend State": data["Signal"]["action"],
                })
        
        if smc_rows:
            smc_df = pd.DataFrame(smc_rows)
            st.dataframe(
                smc_df, 
                use_container_width=True,
                column_config={"Chart": st.column_config.LinkColumn("Chart", display_text="📈 View")}
            )
        else:
            st.info("No Smart Money setups detected across the Nifty 500 in this timeframe.")

    # ═══════════ TAB 3: VOLUME ANALYSIS ═══════════
    with tab_volume:
        valid_tickers_v = list(valid.keys())
        if not valid_tickers_v:
            st.info("Run a scan first.")
        else:
            v_selected = st.selectbox("Select Stock for Volume Analysis", valid_tickers_v,
                                      format_func=lambda x: x.replace(".NS", ""), key="vol_select")
            v_data = valid[v_selected]
            v_hist = v_data["History"]
            v_tech = v_data["Technicals"]

            # Volume metrics
            vm1, vm2, vm3, vm4 = st.columns(4)
            vm1.metric("Current Volume", fmt_vol(v_tech.get("Volume")))
            vm2.metric("Avg Volume (SMA)", fmt_vol(v_tech.get("Volume_SMA")))
            vm3.metric("Relative Volume",
                       f"{v_tech.get('Relative_Volume', '—')}x" if v_tech.get('Relative_Volume') else "—")
            vm4.metric("OBV", fmt_vol(v_tech.get("OBV")))

            st.markdown(
                f"""<div class="glass-card">
                    <h3>Volume Assessment for {v_selected.replace('.NS','')}</h3>
                    {vol_badge(v_data['Signal'].get('volume_note',''))}
                    <p style="margin-top:8px;">
                        Relative volume compares current bar's volume to the 20-period average.
                        Values above 2.0x indicate a <strong>volume spike</strong> which significantly
                        increases confidence in the directional signal. Low relative volume (&lt; 0.8x)
                        suggests the move lacks conviction.</p>
                </div>""",
                unsafe_allow_html=True,
            )

            # Charts
            st.markdown("##### 📊 Relative Volume")
            st.plotly_chart(build_relative_volume_chart(v_hist), width="stretch", key="vol_relvol")

            rv1, rv2 = st.columns(2)
            with rv1:
                st.markdown("##### 📈 OBV Trend")
                st.plotly_chart(build_obv_chart(v_hist), width="stretch", key="vol_obv")
            with rv2:
                st.markdown("##### 📉 RSI (14)")
                st.plotly_chart(build_rsi_chart(v_hist), width="stretch", key="vol_rsi")

    # ═══════════ TAB 5: CHARTINK TRADE PLANNER ═══════════
    with tab_chartink:
        st.markdown("### 🎯 Chartink Trade Planner")
        st.write("Paste your raw Chartink copy-paste below. We'll automatically extract the exact stock symbols and generate an actionable trade plan (Entry, Target, Stop Loss) based on technical pivots.")
        
        st.markdown("<hr style='margin-top:10px; margin-bottom:10px'>", unsafe_allow_html=True)
        
        with st.form("trade_planner_form"):
            plan_tf = st.selectbox("⏱️ Select Intraday Timeframe for Trade Planner", ["5m", "15m", "1h", "Daily"], index=1)
            raw_paste = st.text_area("✍️ Paste Chartink Stocks Here", height=100, placeholder="Copy-paste the entire list from Chartink (e.g. DMART, RELIANCE, TCS...)")
            submitted = st.form_submit_button("🚀 Generate Trade Plan", use_container_width=True)
            
        if submitted:
            if raw_paste.strip():
                import re
                words = re.split(r'[\s,]+', raw_paste.strip())
                symbols = []
                for w in words:
                    cw = w.strip()
                    if len(cw) > 1 and re.match(r'^[A-Z\-]+$', cw):
                        if cw not in symbols: symbols.append(cw)
                        
                if symbols:
                    st.success(f"Detected {len(symbols)} symbols: {', '.join(symbols)}")
                    ns_symbols = [f"{s}.NS" for s in symbols]
                    
                    with st.spinner(f"Calculating {plan_tf} trade execution levels..."):
                        # Always strictly fetch fresh data matching the requested timeframe guarantees accurate Intraday Pivots
                        plan_data = fetch_all_stocks(ns_symbols, timeframe=plan_tf)
                             
                        plan_rows = []
                        for sym in ns_symbols:
                            if sym not in plan_data or "error" in plan_data[sym]: continue
                            d = plan_data[sym]
                            t = d["Technicals"]
                            p = d.get("Pivots", {})
                            if not p: continue
                            
                            plan_rows.append({
                                "Symbol": sym.replace(".NS", ""),
                                "Price": f"₹{t.get('Last Price', 0)}",
                                "Trend Bias": d["Signal"]["action"],
                                "Pivot (Entry)": f"₹{p.get('Pivot', 0)}",
                                "Target 1 (R1)": f"₹{p.get('R1', 0)}",
                                "Target 2 (R2)": f"₹{p.get('R2', 0)}",
                                "Support 1 (SL/Buy)": f"₹{p.get('S1', 0)}",
                                "Support 2 (Max SL)": f"₹{p.get('S2', 0)}"
                            })
                            
                        if plan_rows:
                            st.session_state["chartink_df"] = pd.DataFrame(plan_rows)
                        else:
                            st.warning("Could not calculate pivot levels for the extracted symbols.")
                else:
                    st.error("No valid uppercase ticker symbols detected in the pasted text.")
                    
        if "chartink_df" in st.session_state:
            st.dataframe(st.session_state["chartink_df"], use_container_width=True)
            if st.button("🧹 Clear Results"):
                del st.session_state["chartink_df"]
                st.rerun()
        
        st.markdown("<hr style='margin-top:20px; margin-bottom:20px'>", unsafe_allow_html=True)
        st.markdown("### 📈 External Screeners Links")

        with st.expander("📖 How do these Screeners work?", expanded=False):
            st.markdown("""
            ### 1. Capital Growth Screener
            This screener is split into two distinct conditions—one for finding **Bullish** momentum and one for **Bearish** breakdowns.
            - **🟢 Bullish Setup (Top Half):** Filters for stocks where the current 15-minute candle breaks **above the high** of the previous 15-minute green candle. It ensures the previous candle was not unusually massive (body < 2.5% of open price) but was large enough to be significant (body > 0.5% of Daily open).
            - **🔴 Bearish Setup (Bottom Half):** Filters for the exact opposite. It looks for stocks where the latest 15-minute candle is breaking **below the low** of a solid, moderately-sized red candle.

            ### 2. Inside Bar & Narrow CPR
            This screener hunts for highly coiled, explosive day-trade setups by combining two strict conditions:
            - **📦 Inside Bar:** It checks if the 2nd 15-minute candle of the day is an "Inside Bar" (its High and Low are completely contained within the 1st candle's High and Low range). This represents temporary consolidation.
            - **🎯 Narrow CPR:** It calculates the absolute distance between the primary Pivot Point `(H+L+C)/3` and the Bottom Central Pivot `(H+L)/2`. If this gap is `≤ 0.002` (0.2%), the Central Pivot Range (CPR) is extremely narrow. A narrow CPR almost always precedes a huge, one-sided trending day!
            - **Extra Filters:** It restricts the scan to stocks priced between ₹100 and ₹1000, and ensures the previous 15-minute candle wasn't overly stretched (range was < 3% of the close price).
            """)

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(
                """<div class="glass-card" style="text-align:center; padding:35px 20px;">
                    <h3 style="color:#5eead4; margin-bottom:8px;">Capital Growth Screener</h3>
                    <p style="color:#94a3b8; font-size:0.95rem; margin-bottom:24px;">Momentum Setup</p>
                    <a href="https://chartink.com/screener/copy-ravi-capital-growth" target="_blank" 
                       style="display:inline-block; padding:12px 30px; background:linear-gradient(135deg, #0f766e 0%, #064e3b 100%); 
                              color:white; border-radius:8px; text-decoration:none; font-weight:bold; 
                              box-shadow: 0 4px 15px rgba(15, 118, 110, 0.4); transition: transform 0.2s;">
                       Open in Chartink ↗
                    </a>
                   </div>""", unsafe_allow_html=True
            )
            
        with col2:
            st.markdown(
                """<div class="glass-card" style="text-align:center; padding:35px 20px;">
                    <h3 style="color:#fbbf24; margin-bottom:8px;">Inside Bar & Narrow CPR</h3>
                    <p style="color:#94a3b8; font-size:0.95rem; margin-bottom:24px;">1st/2nd 15-Min Inside Bar Scan</p>
                    <a href="https://chartink.com/screener/ravi-research-1st-2nd-15-min-inside-bar-scan-with-narrow-cpr" target="_blank" 
                       style="display:inline-block; padding:12px 30px; background:linear-gradient(135deg, #b45309 0%, #78350f 100%); 
                              color:white; border-radius:8px; text-decoration:none; font-weight:bold; 
                              box-shadow: 0 4px 15px rgba(180, 83, 9, 0.4); transition: transform 0.2s;">
                       Open in Chartink ↗
                    </a>
                   </div>""", unsafe_allow_html=True
            )

    # Errors
    if errors:
        with st.expander(f"⚠️ {len(errors)} ticker(s) failed", expanded=False):
            for t, e in errors.items():
                st.error(f"**{t}**: {e.get('error','Unknown error')}")

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center; padding:70px 20px;">
        <p style="font-size:3.5rem; margin:0;">📊</p>
        <h2 style="color:#5eead4; font-weight:700; margin:12px 0 6px;">Ready to Scan the Nifty 500</h2>
        <p style="color:#64748b; font-size:1rem; max-width:520px; margin:0 auto;">
            Pick stocks from the full Nifty 500 universe in the sidebar, choose your timeframe
            (5m / 15m / 1h / 4h / Daily / Weekly), then hit <strong>🚀 Scan Now</strong>
            to fetch real-time data with volume-confirmed signals.
        </p>
    </div>
    """, unsafe_allow_html=True)
