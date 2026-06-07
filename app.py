"""RRG web app — US sectors + crypto ETFs vs SPY (Streamlit, read-only).

Reads precomputed RS-Ratio / RS-Momentum from Supabase (anon key, RLS-protected
read-only) and renders a Relative Rotation Graph. It performs NO data-provider
calls and NO RRG math — only DB reads, tail sampling, and Plotly drawing.

Run locally:  streamlit run app.py
Deploy:       Streamlit Community Cloud (defaults baked in; no secrets needed)
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rrg import config, curve
from rrg.sampling import (
    DEFAULT_PRESET, MIN_POINTS, PRESET_ORDER, PRESETS,
    sample_by_dates, sample_tail,
)

# ── public connection defaults (anon key is publishable; RLS keeps it read-only)
DEFAULT_URL = "https://mptecsecdhdoxqocubuv.supabase.co"
DEFAULT_ANON = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1wdGVjc2VjZGhkb3hxb2N1YnV2Iiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODA3OTkyMTMsImV4cCI6MjA5NjM3NTIxM30."
    "2MxTb4z9UZWjE4P_ZABZPNkHQPhMuafbO8lISNdEPAg"
)

CUSTOM = "사용자 지정"
# Newcomer-friendly default view: a few flagship names.
DEFAULT_SHOWN = ["XLK", "XLV", "IBIT", "MAGS"]   # 기술 · 헬스케어 · 비트코인 · 빅테크M7

# Per-ticker colours — vivid on the dark canvas; crypto keep brand-ish hues.
COLORS = {
    # 기본 섹터
    "XLK": "#5b9bd5", "XLV": "#41c9c9", "XLY": "#70ad47", "XLP": "#ff5b5b",
    "XLRE": "#b18cff", "XLF": "#c49a6c", "XLI": "#ff86c8", "XLB": "#9aa6b2",
    "XLE": "#ffd34d", "XLU": "#2dd4a7", "XLC": "#d8b4fe",
    # 크립토
    "IBIT": "#f7931a", "ETHA": "#8f9bff",
    # 세부섹터
    "ARKG": "#ff7847", "THNR": "#2dd4bf", "NLR": "#a3e635", "ITA": "#38bdf8",
    "SOXX": "#e879f9", "MAGS": "#fb7185", "QTUM": "#c084fc", "DRAM": "#fbbf24",
}

# Wall-Street palette
BG = "#0a0f1c"          # page / paper
PLOT_BG = "#0d1426"     # plot area
GRID = "rgba(255,255,255,0.045)"
AXIS_FG = "#9aa6bd"
GOLD = "#c9a227"

# Quadrant fills (subtle) + accent colour + Korean guide line.
QUAD = {
    "Leading":   ("rgba(46,200,130,0.08)",  "#2ec882", "선도",  "강세 · 모멘텀↑ — 시장 주도"),
    "Weakening": ("rgba(230,190,60,0.08)",  "#e6be3c", "약화",  "강세지만 모멘텀↓ — 동력 둔화"),
    "Lagging":   ("rgba(230,80,80,0.08)",   "#e65050", "후행",  "약세 · 모멘텀↓ — 시장 열위"),
    "Improving": ("rgba(80,150,230,0.08)",  "#5096e6", "개선",  "약세지만 모멘텀↑ — 회복 신호"),
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
def build_figure(tails: dict[str, pd.DataFrame], highlight: str | None,
                 mobile: bool = False) -> go.Figure:
    fig = go.Figure()
    # Screen-aware sizing — mobile gets thinner lines & smaller text/markers so
    # a narrow screen doesn't look heavy/cramped.
    line_w = 1.5 if mobile else 2.4
    mid_sz = 4 if mobile else 6
    end_sz = 9 if mobile else 14
    lbl_sz = 9 if mobile else 12
    corner_sz = 9 if mobile else 12
    axis_sz = 9 if mobile else 12
    base_sz = 11 if mobile else 13
    legend_sz = 9 if mobile else 12
    cross_w = 1.0 if mobile else 1.2

    xs = pd.concat([t["rs_ratio"] for t in tails.values()]) if tails else pd.Series([100])
    ys = pd.concat([t["rs_mom"] for t in tails.values()]) if tails else pd.Series([100])
    # Symmetric, 100-centred range -> the cross sits dead-centre and the view is
    # always balanced regardless of which tickers are shown. A floor keeps it
    # from zooming in too tightly when everything sits near 100.
    dev = max(float((xs - 100).abs().max()), float((ys - 100).abs().max()), 1.5)
    R = dev * 1.18 + 0.4
    x0, x1 = 100 - R, 100 + R
    y0, y1 = 100 - R, 100 + R

    rects = {
        "Leading":   (100, x1, 100, y1),
        "Weakening": (100, x1, y0, 100),
        "Lagging":   (x0, 100, y0, 100),
        "Improving": (x0, 100, 100, y1),
    }
    for name, (rx0, rx1, ry0, ry1) in rects.items():
        fig.add_shape(type="rect", x0=rx0, x1=rx1, y0=ry0, y1=ry1,
                      fillcolor=QUAD[name][0], line_width=0, layer="below")
    corners = {"Leading": (x1, y1, "right", "top"), "Weakening": (x1, y0, "right", "bottom"),
               "Lagging": (x0, y0, "left", "bottom"), "Improving": (x0, y1, "left", "top")}
    for name, (ax, ay, xa, ya) in corners.items():
        fig.add_annotation(x=ax, y=ay, text=name, showarrow=False, xanchor=xa, yanchor=ya,
                           font=dict(color=QUAD[name][1], size=corner_sz), opacity=0.65)

    # 100 cross — muted gold
    fig.add_hline(y=100, line=dict(color=GOLD, width=cross_w))
    fig.add_vline(x=100, line=dict(color=GOLD, width=cross_w))

    for ticker, tail in tails.items():
        color = COLORS.get(ticker, "#ccc")
        label = config.label(ticker)
        op = 1.0 if (highlight is None or highlight == ticker) else 0.12

        pts = tail[["rs_ratio", "rs_mom"]].to_numpy()
        smooth = curve.catmull_rom(pts)
        dates = tail.index.strftime("%Y-%m-%d").tolist()

        fig.add_trace(go.Scatter(
            x=smooth[:, 0], y=smooth[:, 1], mode="lines",
            line=dict(color=color, width=line_w), opacity=op,
            name=label, legendgroup=ticker, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=pts[:-1, 0], y=pts[:-1, 1], mode="markers",
            marker=dict(color=color, size=mid_sz), opacity=op,
            legendgroup=ticker, showlegend=False, customdata=dates[:-1],
            hovertemplate=(f"<b>{label}</b><br>날짜=%{{customdata}}"
                           "<br>RS-Ratio=%{x:.2f}<br>RS-Mom=%{y:.2f}<extra></extra>"),
        ))
        fig.add_trace(go.Scatter(
            x=[pts[-1, 0]], y=[pts[-1, 1]], mode="markers+text",
            marker=dict(color=color, size=end_sz, line=dict(color=BG, width=1.5)),
            opacity=op, text=[label], textposition="top center",
            textfont=dict(size=lbl_sz, color=color),
            legendgroup=ticker, showlegend=False, customdata=[dates[-1]],
            hovertemplate=(f"<b>{label}</b> (최신)<br>날짜=%{{customdata}}"
                           "<br>RS-Ratio=%{x:.2f}<br>RS-Mom=%{y:.2f}<extra></extra>"),
        ))

    # Mobile: square-ish chart, legend wraps under the plot (touch-friendly).
    # Desktop: taller chart, vertical legend on the right.
    if mobile:
        legend = dict(groupclick="togglegroup", orientation="h", yanchor="top",
                      y=-0.12, xanchor="left", x=0, font=dict(color="#cdd5e3", size=legend_sz))
        layout_extra = dict(height=520, margin=dict(l=6, r=6, t=6, b=6))
    else:
        legend = dict(groupclick="togglegroup", orientation="v", yanchor="top",
                      y=1, xanchor="left", x=1.01, font=dict(color="#cdd5e3", size=legend_sz))
        layout_extra = dict(height=720, margin=dict(l=40, r=20, t=20, b=40))

    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=PLOT_BG, dragmode=False,
        font=dict(color=AXIS_FG, family="Inter, 'Noto Sans KR', sans-serif", size=base_sz),
        xaxis=dict(title=dict(text="RS-Ratio", font=dict(size=axis_sz)),
                   tickfont=dict(size=axis_sz), range=[x0, x1], zeroline=False,
                   fixedrange=True, showgrid=True, gridcolor=GRID, color=AXIS_FG),
        yaxis=dict(title=dict(text="RS-Momentum", font=dict(size=axis_sz)),
                   tickfont=dict(size=axis_sz), range=[y0, y1], zeroline=False,
                   fixedrange=True, showgrid=True, gridcolor=GRID, color=AXIS_FG),
        legend=legend, hovermode="closest", **layout_extra,
    )
    return fig


# ── small UI helpers ────────────────────────────────────────────────────────
def quadrant_guide() -> None:
    """Four colour-chipped one-liners explaining each quadrant.

    Rendered as a flex-wrap row so it shows 4-across on wide screens and folds
    to 2-across (or 1) on phones — no fixed column count.
    """
    chips = []
    for name in ["Leading", "Weakening", "Lagging", "Improving"]:
        _, accent, kr, desc = QUAD[name]
        chips.append(
            f"<div style='flex:1 1 150px;min-width:150px;line-height:1.35'>"
            f"<span style='display:inline-block;width:11px;height:11px;background:{accent};"
            f"border-radius:2px;margin-right:7px'></span>"
            f"<b style='color:{accent}'>{name}</b> "
            f"<span style='color:#cdd5e3'>{kr}</span><br>"
            f"<span style='color:#8893a8;font-size:0.85em'>{desc}</span></div>"
        )
    st.markdown(
        "<div style='display:flex;flex-wrap:wrap;gap:10px 18px'>" + "".join(chips) + "</div>",
        unsafe_allow_html=True,
    )


# ── app ─────────────────────────────────────────────────────────────────────
FONT_STACK = "'Inter','Pretendard','Noto Sans KR',-apple-system,sans-serif"


def detect_mobile_default() -> bool:
    """Best-effort phone detection from the request User-Agent (override-able)."""
    try:
        ua = st.context.headers.get("User-Agent", "")
    except Exception:
        return False
    return any(k in ua for k in ("Mobi", "Android", "iPhone", "iPod", "iPad"))


def main() -> None:
    st.set_page_config(page_title="RRG — 섹터 & 크립토", layout="wide")
    # Soft modern type (Inter + Korean Noto) + tighter padding on small screens.
    st.markdown(
        "<style>"
        "@import url('https://fonts.googleapis.com/css2?"
        "family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;700&display=swap');"
        f"html,body,[class*='css'],.stApp{{font-family:{FONT_STACK};"
        "-webkit-font-smoothing:antialiased;letter-spacing:-0.01em}}"
        "@media (max-width:640px){.block-container{padding:0.7rem 0.6rem !important}}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h2 style='margin-bottom:0;color:{GOLD};font-family:{FONT_STACK};"
        "font-weight:700;letter-spacing:-0.02em'>Relative Rotation Graph</h2>"
        "<div style='color:#8893a8;margin-bottom:10px'>미국 섹터 &amp; 크립토 ETF · "
        f"벤치마크 {config.BENCHMARK} · RS = 100 × (종가 ÷ SPY)</div>",
        unsafe_allow_html=True,
    )

    data = load_rrg()
    if not data:
        st.error("데이터를 불러오지 못했습니다. Supabase 연결/시크릿을 확인하세요.")
        st.stop()

    # ── all controls live in the sidebar (clean first screen) ───────────────
    all_tk = list(config.UNIVERSE)
    SHOWN = "shown_tickers"
    if SHOWN not in st.session_state:
        st.session_state[SHOWN] = [t for t in DEFAULT_SHOWN if t in all_tk]

    def _add_group(tickers: list[str]) -> None:
        cur = set(st.session_state.get(SHOWN, [])) | set(tickers)
        st.session_state[SHOWN] = [t for t in config.UNIVERSE if t in cur]

    with st.sidebar:
        st.markdown("#### 종목 선택")
        mc = st.columns(2)
        mc[0].button("전체 켜기", use_container_width=True,
                     on_click=lambda: st.session_state.__setitem__(SHOWN, all_tk))
        mc[1].button("전체 끄기", use_container_width=True,
                     on_click=lambda: st.session_state.__setitem__(SHOWN, []))
        with st.expander("그룹으로 추가"):
            for gname, gtk in config.GROUPS.items():
                st.button(f"＋ {gname}", key=f"add::{gname}", use_container_width=True,
                          on_click=_add_group, args=(list(gtk),))
        shown = st.multiselect("표시 종목", all_tk, key=SHOWN, format_func=config.label)
        st.divider()
        hi_pick = st.selectbox("강조 (나머지 흐리게)",
                               ["전체"] + [config.label(t) for t in shown])
        st.divider()
        mobile = st.toggle("📱 모바일 모드", value=detect_mobile_default(),
                           help="범례를 차트 하단으로 옮기고 화면 폭에 맞춥니다")

    if not shown:
        st.info("왼쪽 사이드바에서 종목을 선택하거나 ‘전체 켜기’를 누르세요.")
        st.stop()

    # timeframe: presets + custom date range
    preset = st.radio("타임프레임", PRESET_ORDER + [CUSTOM],
                      index=PRESET_ORDER.index(DEFAULT_PRESET), horizontal=True)

    custom_start = custom_end = None
    target_pts = 13
    if preset == CUSTOM:
        dmin = min(df.index.min() for df in data.values()).date()
        dmax = max(df.index.max() for df in data.values()).date()
        default_start = max(dmin, dmax - timedelta(days=90))
        c1, c2 = st.columns([3, 1])
        rng = c1.date_input("기간 선택", value=(default_start, dmax),
                            min_value=dmin, max_value=dmax)
        target_pts = c2.slider("곡선 점 수", 5, 20, 13)
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            custom_start, custom_end = rng
        else:  # user mid-selection (single date) -> wait
            st.info("기간의 시작과 종료 날짜를 모두 선택하세요.")
            st.stop()

    # build tails; collect insufficient names (only among shown tickers)
    tails: dict[str, pd.DataFrame] = {}
    insufficient: list[str] = []
    for ticker in shown:
        df = data.get(ticker)
        if df is None or df.empty:
            insufficient.append(config.label(ticker))
            continue
        s = (sample_by_dates(df, custom_start, custom_end, target_pts)
             if preset == CUSTOM else sample_tail(df, preset))
        if len(s) < MIN_POINTS:
            insufficient.append(config.label(ticker))
            continue
        tails[ticker] = s

    if not tails:
        st.warning("선택한 기간에 표시할 데이터가 부족합니다.")
        st.stop()

    label_to_ticker = {config.label(t): t for t in tails}
    highlight = None if hi_pick == "전체" else label_to_ticker.get(hi_pick)

    # Locked view: no zoom/pan/drag, no modebar — the scale stays put.
    st.plotly_chart(
        build_figure(tails, highlight, mobile=mobile), width="stretch",
        config={"responsive": True, "displaylogo": False,
                "displayModeBar": False, "scrollZoom": False,
                "doubleClick": False, "staticPlot": False},
    )

    # footer: quadrant guide + freshness + insufficient notice
    st.divider()
    quadrant_guide()
    st.divider()
    latest = max(t.index.max() for t in tails.values()).strftime("%Y-%m-%d")
    if preset == CUSTOM:
        span = f"사용자 지정 {custom_start}~{custom_end} (~{target_pts}점)"
    else:
        rng_td, step = PRESETS[preset]
        span = f"{preset} (최근 {rng_td}거래일, ~{step}일 간격)"
    st.caption(f"최신 데이터 **{latest}** · {span} · 표시 종목 {len(tails)}개 · "
               "종목 선택은 왼쪽 사이드바 ☰")
    if insufficient:
        st.caption("⚠️ 데이터 부족: " + ", ".join(insufficient))


if __name__ == "__main__":
    main()
