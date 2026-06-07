"""RRG web app — US sectors + crypto ETFs vs SPY (Streamlit, read-only).

Reads precomputed RS-Ratio / RS-Momentum from Supabase (anon key, RLS-protected
read-only) and renders a Relative Rotation Graph. It performs NO data-provider
calls and NO RRG math — only DB reads, tail sampling, and Plotly drawing.

Run locally:  streamlit run app.py
Deploy:       Streamlit Community Cloud (set secrets, see .streamlit/secrets.toml.example)
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rrg import config, curve
from rrg.sampling import DEFAULT_PRESET, MIN_POINTS, PRESET_ORDER, PRESETS, sample_tail

# ── public connection defaults (anon key is publishable; RLS keeps it read-only)
DEFAULT_URL = "https://mptecsecdhdoxqocubuv.supabase.co"
DEFAULT_ANON = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1wdGVjc2VjZGhkb3hxb2N1YnV2Iiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODA3OTkyMTMsImV4cCI6MjA5NjM3NTIxM30."
    "2MxTb4z9UZWjE4P_ZABZPNkHQPhMuafbO8lISNdEPAg"
)

# Per-ticker colours (crypto get their brand hues).
COLORS = {
    "XLK": "#1f77b4", "XLV": "#ff7f0e", "XLY": "#2ca02c", "XLP": "#d62728",
    "XLRE": "#9467bd", "XLF": "#8c564b", "XLI": "#e377c2", "XLB": "#7f7f7f",
    "XLE": "#bcbd22", "XLU": "#17becf", "XLC": "#393b79",
    "IBIT": "#f7931a", "ETHA": "#627eea",
}
QUADRANTS = {  # (x_side, y_side) -> (fill, label, label_xy_factor)
    "Leading":   "rgba(0,170,0,0.10)",
    "Weakening": "rgba(230,195,0,0.13)",
    "Lagging":   "rgba(220,0,0,0.10)",
    "Improving": "rgba(0,120,220,0.10)",
}


# ── config / secrets ────────────────────────────────────────────────────────
def _secret(name: str, default: str) -> str:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, default)


# ── data access (read-only REST, cached) ────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="데이터 불러오는 중…")
def load_rrg() -> dict[str, pd.DataFrame]:
    """Fetch all rrg_values for the universe and split per ticker (date-sorted)."""
    base = _secret("SUPABASE_URL", DEFAULT_URL).rstrip("/")
    key = _secret("SUPABASE_ANON_KEY", DEFAULT_ANON)
    in_list = ",".join(config.UNIVERSE.keys())
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    recs: list[dict] = []
    page, offset = 1000, 0
    while True:
        url = (
            f"{base}/rest/v1/rrg_values?select=ticker,bar_date,rs_ratio,rs_mom"
            f"&benchmark=eq.{config.BENCHMARK}&interval=eq.D"
            f"&param_hash=eq.{config.PARAM_HASH}&ticker=in.({in_list})"
            f"&order=ticker.asc,bar_date.asc&limit={page}&offset={offset}"
        )
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            chunk = json.loads(resp.read().decode())
        recs.extend(chunk)
        if len(chunk) < page:
            break
        offset += page

    out: dict[str, pd.DataFrame] = {}
    if not recs:
        return out
    df = pd.DataFrame(recs).drop_duplicates(["ticker", "bar_date"])
    df["bar_date"] = pd.to_datetime(df["bar_date"])
    for ticker, g in df.groupby("ticker"):
        out[ticker] = (
            g.sort_values("bar_date").set_index("bar_date")[["rs_ratio", "rs_mom"]]
        )
    return out


# ── figure ──────────────────────────────────────────────────────────────────
def build_figure(tails: dict[str, pd.DataFrame], highlight: str | None) -> go.Figure:
    fig = go.Figure()

    # axis range from all points, padded, with 100 guaranteed visible
    xs = pd.concat([t["rs_ratio"] for t in tails.values()]) if tails else pd.Series([100])
    ys = pd.concat([t["rs_mom"] for t in tails.values()]) if tails else pd.Series([100])
    pad_x = max(0.5, (xs.max() - xs.min()) * 0.12)
    pad_y = max(0.5, (ys.max() - ys.min()) * 0.12)
    x0, x1 = min(xs.min() - pad_x, 99.0), max(xs.max() + pad_x, 101.0)
    y0, y1 = min(ys.min() - pad_y, 99.0), max(ys.max() + pad_y, 101.0)

    # quadrant backgrounds
    rects = {
        "Leading":   (100, x1, 100, y1),
        "Weakening": (100, x1, y0, 100),
        "Lagging":   (x0, 100, y0, 100),
        "Improving": (x0, 100, 100, y1),
    }
    for name, (rx0, rx1, ry0, ry1) in rects.items():
        fig.add_shape(type="rect", x0=rx0, x1=rx1, y0=ry0, y1=ry1,
                      fillcolor=QUADRANTS[name], line_width=0, layer="below")
    fig.add_annotation(x=x1, y=y1, text="Leading", showarrow=False,
                       xanchor="right", yanchor="top", font=dict(color="green", size=12))
    fig.add_annotation(x=x1, y=y0, text="Weakening", showarrow=False,
                       xanchor="right", yanchor="bottom", font=dict(color="#b59000", size=12))
    fig.add_annotation(x=x0, y=y0, text="Lagging", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(color="red", size=12))
    fig.add_annotation(x=x0, y=y1, text="Improving", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(color="#0a78dc", size=12))

    # 100 cross
    fig.add_hline(y=100, line=dict(color="black", width=1.5))
    fig.add_vline(x=100, line=dict(color="black", width=1.5))

    for ticker, tail in tails.items():
        color = COLORS.get(ticker, "#444")
        label = config.label(ticker)
        op = 1.0 if (highlight is None or highlight == ticker) else 0.15

        pts = tail[["rs_ratio", "rs_mom"]].to_numpy()
        smooth = curve.catmull_rom(pts)
        dates = tail.index.strftime("%Y-%m-%d").tolist()

        # ① smooth curve
        fig.add_trace(go.Scatter(
            x=smooth[:, 0], y=smooth[:, 1], mode="lines",
            line=dict(color=color, width=2.6), opacity=op,
            name=label, legendgroup=ticker, hoverinfo="skip",
        ))
        # ② mid nodes (all but the last point)
        fig.add_trace(go.Scatter(
            x=pts[:-1, 0], y=pts[:-1, 1], mode="markers",
            marker=dict(color=color, size=6), opacity=op,
            legendgroup=ticker, showlegend=False,
            customdata=dates[:-1],
            hovertemplate=(f"<b>{label}</b><br>날짜=%{{customdata}}"
                           "<br>RS-Ratio=%{x:.2f}<br>RS-Mom=%{y:.2f}<extra></extra>"),
        ))
        # ③ endpoint (big marker + Korean label)
        fig.add_trace(go.Scatter(
            x=[pts[-1, 0]], y=[pts[-1, 1]], mode="markers+text",
            marker=dict(color=color, size=14, line=dict(color="white", width=1.5)),
            opacity=op, text=[label], textposition="top center",
            textfont=dict(size=12, color=color),
            legendgroup=ticker, showlegend=False,
            customdata=[dates[-1]],
            hovertemplate=(f"<b>{label}</b> (최신)<br>날짜=%{{customdata}}"
                           "<br>RS-Ratio=%{x:.2f}<br>RS-Mom=%{y:.2f}<extra></extra>"),
        ))

    fig.update_layout(
        height=720, margin=dict(l=40, r=20, t=30, b=40),
        xaxis=dict(title="RS-Ratio", range=[x0, x1], zeroline=False,
                   showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        yaxis=dict(title="RS-Momentum", range=[y0, y1], zeroline=False,
                   showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(groupclick="togglegroup", orientation="v",
                    yanchor="top", y=1, xanchor="left", x=1.01),
        plot_bgcolor="white", hovermode="closest",
    )
    return fig


# ── app ─────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(page_title="RRG — 섹터 & 크립토", layout="wide")
    st.title("📈 Relative Rotation Graph — 미국 섹터 & 크립토 ETF")
    st.caption(f"벤치마크: {config.BENCHMARK} · 모든 종목 RS = 100 × (종가 ÷ SPY종가)")

    data = load_rrg()
    if not data:
        st.error("데이터를 불러오지 못했습니다. Supabase 연결/시크릿을 확인하세요.")
        st.stop()

    # timeframe presets
    preset = st.radio(
        "타임프레임", PRESET_ORDER, index=PRESET_ORDER.index(DEFAULT_PRESET),
        horizontal=True,
    )

    # sample tails; collect insufficient names
    tails: dict[str, pd.DataFrame] = {}
    insufficient: list[str] = []
    for ticker in config.UNIVERSE:
        df = data.get(ticker)
        if df is None or df.empty:
            insufficient.append(config.label(ticker))
            continue
        s = sample_tail(df, preset)
        if len(s) < MIN_POINTS:
            insufficient.append(config.label(ticker))
            continue
        tails[ticker] = s

    # highlight selector
    options = ["전체"] + [config.label(t) for t in tails]
    pick = st.selectbox("강조할 종목 (나머지는 흐리게)", options, index=0)
    label_to_ticker = {config.label(t): t for t in tails}
    highlight = None if pick == "전체" else label_to_ticker.get(pick)

    if not tails:
        st.warning("표시할 데이터가 부족합니다.")
        st.stop()

    st.plotly_chart(build_figure(tails, highlight), width="stretch")

    # footer: data freshness + insufficient notice
    latest = max(t.index.max() for t in tails.values()).strftime("%Y-%m-%d")
    rng, step = PRESETS[preset]
    st.caption(
        f"최신 데이터: **{latest}** · 프리셋 {preset} (최근 {rng}거래일, ~{step}일 간격) · "
        f"표시 종목 {len(tails)}개 · 범례 클릭으로 개별 토글"
    )
    if insufficient:
        st.caption("⚠️ 데이터 부족: " + ", ".join(insufficient))


if __name__ == "__main__":
    main()
