"""Dashboard theme and reusable UI components."""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

# Palette — high-contrast for dark backgrounds (WCAG-friendly muted text)
BG = "#0a0e13"
PANEL = "#121820"
PANEL_2 = "#0f151d"
BORDER = "#2a3544"
TEXT = "#f0f4f8"
MUTED = "#b8c4d0"  # was ~#8b97a4 / #5b6672 — too dark on charcoal
CAPTION = "#a8b4c0"
GREEN = "#22c55e"
GREEN_SOFT = "#3dde8a"
RED = "#ff6b6f"
BLUE = "#5b9bff"
PURPLE = "#c084fc"
AMBER = "#fbbf24"
TEAL = "#2dd4bf"

THEME_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

    .stApp {{ background: {BG}; color: {TEXT}; }}
    .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1500px; }}

    /* Streamlit widgets: readable labels & captions on dark bg */
    label, [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p {{
        color: {TEXT} !important;
    }}
    [data-testid="stCaption"], .stCaption, small {{ color: {CAPTION} !important; }}
    .stAlert p {{ color: {TEXT} !important; }}
    div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input {{
        color: {TEXT} !important; background: {PANEL_2} !important; border-color: {BORDER} !important;
    }}
    .stSlider label, [data-testid="stSlider"] p {{ color: {MUTED} !important; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {PANEL_2} !important;
        border-right: 1px solid {BORDER};
    }}
    [data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}

    .hc-logo {{ display:flex; align-items:center; gap:.6rem; padding:.2rem .2rem 1rem .2rem; }}
    .hc-logo .mark {{
        width:30px; height:30px; border-radius:9px;
        background: linear-gradient(135deg, {GREEN}, #15803d);
        display:flex; align-items:center; justify-content:center; font-size:16px;
    }}
    .hc-logo .name {{ color:{TEXT}; font-weight:800; letter-spacing:.02em; font-size:1.02rem; }}
    .hc-logo .name span {{ color:{GREEN}; }}

    .hc-nav-label {{
        color:{CAPTION}; font-size:.7rem; font-weight:700; letter-spacing:.12em;
        text-transform:uppercase; margin:1.1rem .3rem .35rem .3rem;
    }}

    /* Sidebar nav buttons: secondary = idle row, primary = active row */
    [data-testid="stSidebar"] .stButton > button {{
        width:100%; text-align:left; justify-content:flex-start;
        border:none; border-radius:9px; padding:.5rem .7rem; margin:.05rem 0;
        font-weight:500; font-size:.9rem; box-shadow:none;
    }}
    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
        background:transparent !important; color:{MUTED} !important;
    }}
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
        background:#161d27 !important; color:{TEXT} !important;
    }}
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background:rgba(34,197,94,.12) !important; color:{GREEN_SOFT} !important;
        box-shadow: inset 3px 0 0 {GREEN};
    }}

    .hc-bankroll {{
        border:1px solid {BORDER}; border-radius:14px; padding:.9rem 1rem;
        background: linear-gradient(160deg, #10171f, #0d131a); margin-top:1rem;
    }}
    .hc-bankroll .cap {{ color:{CAPTION}; font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }}
    .hc-bankroll .amt {{ color:{GREEN}; font-size:1.5rem; font-weight:800; margin:.15rem 0; }}
    .hc-bankroll .day {{ color:{MUTED}; font-size:.8rem; }}
    .hc-bankroll .day b {{ color:{GREEN_SOFT}; }}

    /* Headings */
    .hc-greet {{ color:{TEXT}; font-size:1.5rem; font-weight:800; margin:0; }}
    .hc-greet-sub {{ color:{MUTED}; font-size:.95rem; margin:.15rem 0 0 0; }}
    .hc-chip {{
        display:inline-flex; align-items:center; gap:.4rem; border:1px solid {BORDER};
        background:{PANEL}; color:{MUTED}; border-radius:9px; padding:.4rem .7rem; font-size:.82rem;
    }}
    .hc-updated {{ color:{CAPTION}; font-size:.82rem; text-align:right; }}

    /* Stat cards */
    .hc-stat {{
        border:1px solid {BORDER}; border-radius:14px; padding:1rem 1.05rem;
        background: linear-gradient(160deg, {PANEL}, {PANEL_2}); min-height:132px;
    }}
    .hc-stat .top {{ display:flex; justify-content:space-between; align-items:flex-start; }}
    .hc-stat .lbl {{ color:{MUTED}; font-size:.8rem; font-weight:500; }}
    .hc-stat .badge {{
        width:30px; height:30px; border-radius:9px; display:flex; align-items:center;
        justify-content:center; font-size:15px;
    }}
    .hc-stat .val {{ font-size:1.7rem; font-weight:800; margin:.35rem 0 .1rem 0; color:{TEXT}; }}
    .hc-stat .sub {{ color:{MUTED}; font-size:.8rem; }}
    .hc-stat .spark {{ margin-top:.4rem; }}
    .pos {{ color:{GREEN_SOFT}; }} .neg {{ color:{RED}; }} .txt {{ color:{TEXT}; }}

    /* Panels */
    .hc-panel {{
        border:1px solid {BORDER}; border-radius:14px; padding:1.1rem 1.15rem;
        background:{PANEL}; margin-bottom:1rem;
    }}
    .hc-panel-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:.8rem; }}
    .hc-panel-title {{ color:{TEXT}; font-weight:700; font-size:1.02rem; }}
    .hc-panel-link {{ color:{GREEN_SOFT}; font-size:.85rem; }}

    /* Tables */
    table.hc-tbl {{ width:100%; border-collapse:collapse; }}
    table.hc-tbl th {{
        color:{CAPTION}; font-size:.72rem; text-transform:uppercase; letter-spacing:.06em;
        text-align:left; padding:.5rem .5rem; border-bottom:1px solid {BORDER}; font-weight:600;
    }}
    table.hc-tbl td {{ padding:.6rem .5rem; border-bottom:1px solid #151b23; font-size:.86rem; color:{TEXT}; }}
    table.hc-tbl tr:last-child td {{ border-bottom:none; }}
    table.hc-tbl .evt {{ font-weight:600; }}
    table.hc-tbl .evt small {{ display:block; color:{MUTED}; font-weight:400; font-size:.75rem; }}
    .cell-muted {{ color:{MUTED}; }}

    /* Source status strip */
    .hc-sources {{
        display:flex; flex-wrap:wrap; gap:.5rem; margin:.4rem 0 1rem 0;
    }}
    .hc-source-pill {{
        border:1px solid {BORDER}; border-radius:999px; padding:.35rem .75rem;
        font-size:.78rem; font-weight:600; background:{PANEL};
    }}
    .hc-source-pill.live {{ color:{GREEN_SOFT}; border-color:rgba(34,197,94,.35); }}
    .hc-source-pill.stale {{ color:{AMBER}; border-color:rgba(251,191,36,.35); }}
    .hc-source-pill.off {{ color:{MUTED}; }}
    .hc-source-pill.err {{ color:{RED}; border-color:rgba(255,107,111,.35); }}

    /* Parlay */
    .hc-leg {{
        display:flex; justify-content:space-between; align-items:center; gap:.5rem;
        border:1px solid {BORDER}; border-radius:10px; padding:.55rem .7rem; margin-bottom:.45rem; background:{PANEL_2};
    }}
    .hc-leg .n {{ color:{TEXT}; font-size:.86rem; font-weight:600; }}
    .hc-leg .n small {{ display:block; color:{MUTED}; font-weight:400; font-size:.75rem; }}
    .hc-leg .o {{ color:{RED}; font-weight:700; font-size:.86rem; }}
    .hc-summary {{ display:flex; justify-content:space-between; padding:.5rem 0; font-size:.86rem; }}
    .hc-summary .k {{ color:{MUTED}; }} .hc-summary .v {{ color:{TEXT}; font-weight:700; }}

    /* Segmented band tabs (buttons) */
    .hc-band .stButton > button {{ border-radius:9px; font-size:.8rem; font-weight:600; padding:.4rem .2rem; }}

    /* Ticker */
    .hc-ticker {{
        display:flex; gap:1.4rem; align-items:center; overflow-x:auto; border:1px solid {BORDER};
        border-radius:12px; padding:.6rem 1rem; background:{PANEL}; white-space:nowrap;
    }}
    .hc-ticker .lead {{ color:{CAPTION}; font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }}
    .hc-ticker .item {{ color:{TEXT}; font-size:.84rem; }}
    .hc-ticker .item b {{ color:{GREEN_SOFT}; }}

    /* Legend */
    .hc-legend {{ font-size:.82rem; color:{MUTED}; }}
    .hc-legend .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:.4rem; }}
    .hc-legend .row {{ display:flex; justify-content:space-between; margin:.25rem 0; }}

    /* Buttons — dark everywhere, never white */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button,
    [data-testid="stPopoverButton"], button[data-testid="stBaseButton-secondary"],
    button[data-testid="stBaseButton-primary"] {{
        border-radius:10px !important; font-weight:600 !important;
        transition: background .15s ease, border-color .15s ease;
    }}
    .block-container .stButton > button[kind="secondary"],
    .block-container .stDownloadButton > button,
    .block-container [data-testid="stPopoverButton"] {{
        background:{PANEL_2} !important; color:{TEXT} !important;
        border:1px solid {BORDER} !important;
    }}
    .block-container .stButton > button[kind="secondary"]:hover,
    .block-container .stDownloadButton > button:hover {{
        background:#1a2330 !important; border-color:#3d4b5e !important; color:{TEXT} !important;
    }}
    .block-container .stButton > button[kind="primary"],
    .block-container .stFormSubmitButton > button {{
        background: linear-gradient(135deg, {GREEN}, #16a34a) !important; border:none !important;
        color:#04180c !important; font-weight:700 !important;
    }}
    .block-container .stButton > button[kind="primary"]:hover,
    .block-container .stFormSubmitButton > button:hover {{
        background: linear-gradient(135deg, {GREEN_SOFT}, {GREEN}) !important; color:#04180c !important;
    }}
    .stButton > button:focus, .stButton > button:active {{
        box-shadow: 0 0 0 2px rgba(34,197,94,.35) !important; outline:none !important;
    }}
    .stButton > button:disabled {{
        background:{PANEL_2} !important; color:#5b6672 !important; border:1px solid {BORDER} !important;
    }}

    /* Tabs, expanders, popovers on dark */
    .stTabs [data-baseweb="tab-list"] {{ gap:.35rem; border-bottom:1px solid {BORDER}; }}
    .stTabs [data-baseweb="tab"] {{
        background:transparent; color:{MUTED}; border-radius:9px 9px 0 0; padding:.45rem .9rem;
    }}
    .stTabs [aria-selected="true"] {{ color:{GREEN_SOFT} !important; }}
    .stTabs [data-baseweb="tab-highlight"] {{ background:{GREEN} !important; }}
    [data-testid="stExpander"] details {{
        background:{PANEL} !important; border:1px solid {BORDER} !important; border-radius:12px !important;
    }}
    [data-testid="stExpander"] summary {{ color:{TEXT} !important; }}
    [data-testid="stPopoverBody"] {{ background:{PANEL} !important; border:1px solid {BORDER} !important; }}

    /* Selects, radio, checkbox, multiselect chips */
    div[data-baseweb="popover"] ul, div[data-baseweb="menu"] {{
        background:{PANEL} !important; border:1px solid {BORDER} !important;
    }}
    div[data-baseweb="menu"] li {{ color:{TEXT} !important; }}
    div[data-baseweb="menu"] li:hover {{ background:#1a2330 !important; }}
    .stMultiSelect [data-baseweb="tag"] {{
        background:rgba(34,197,94,.14) !important; color:{GREEN_SOFT} !important;
    }}
    .stRadio label span, .stCheckbox label span {{ color:{TEXT} !important; }}

    .hc-status {{ padding:.15rem .5rem; border-radius:6px; font-size:.72rem; font-weight:700; }}
    .hc-status.on {{ background:rgba(34,197,94,.14); color:{GREEN_SOFT}; }}

    /* Interactive bordered container styled as a panel */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background:{PANEL}; border:1px solid {BORDER} !important; border-radius:14px; padding:.35rem .4rem;
    }}
    [data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {{ background:transparent; }}

    @media (max-width: 900px) {{
        .block-container {{ padding-left:1rem; padding-right:1rem; }}
        .hc-greet {{ font-size:1.25rem; }}
        .hc-stat .val {{ font-size:1.35rem; }}
    }}

    #MainMenu, footer, header {{ visibility:hidden; }}
    [data-testid="stSidebarNav"] {{ display:none; }}
</style>
"""


def inject_theme() -> None:
    if st is not None:
        st.markdown(THEME_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# SVG chart helpers
# --------------------------------------------------------------------------- #
def sparkline_svg(series: Sequence[float], color: str = GREEN, width: int = 150, height: int = 34) -> str:
    pts = [float(v) for v in series if v is not None]
    if len(pts) < 2:
        pts = [0.0, 0.0]
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    step = width / (len(pts) - 1)
    coords = [
        (i * step, height - 3 - ((v - lo) / rng) * (height - 6))
        for i, v in enumerate(pts)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"0,{height} " + line + f" {width},{height}"
    gid = f"g{abs(hash((tuple(pts), color))) % 100000}"
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none">'
        f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.28"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#{gid})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


def line_chart_svg(series: Sequence[float], color: str = GREEN, width: int = 460, height: int = 150) -> str:
    pts = [float(v) for v in series if v is not None]
    if len(pts) < 2:
        pts = [0.0, 0.0]
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    pad = 8
    step = (width - pad * 2) / (len(pts) - 1)
    coords = [
        (pad + i * step, pad + (1 - (v - lo) / rng) * (height - pad * 2 - 14))
        for i, v in enumerate(pts)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{pad},{height - 16} " + line + f" {width - pad},{height - 16}"
    grid = "".join(
        f'<line x1="{pad}" x2="{width - pad}" y1="{pad + i * (height - pad * 2 - 14) / 3:.0f}" '
        f'y2="{pad + i * (height - pad * 2 - 14) / 3:.0f}" stroke="{BORDER}" stroke-width="1"/>'
        for i in range(4)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}">'
        f'<defs><linearGradient id="lc" x1="0" x2="0" y1="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.30"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f"{grid}"
        f'<polygon points="{area}" fill="url(#lc)"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


def donut_svg(segments: Sequence[tuple[str, float, str]], center_top: str, center_sub: str, size: int = 150) -> str:
    total = sum(max(0.0, v) for _, v, _ in segments) or 1.0
    r = size / 2 - 12
    cx = cy = size / 2
    circ = 2 * 3.14159265 * r
    offset = 0.0
    arcs = ""
    for _, value, color in segments:
        frac = max(0.0, value) / total
        dash = frac * circ
        arcs += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="16" stroke-dasharray="{dash:.2f} {circ - dash:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += dash
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="16"/>'
        f"{arcs}"
        f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" fill="{TEXT}" '
        f'font-size="24" font-weight="800">{center_top}</text>'
        f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" fill="{MUTED}" font-size="10">{center_sub}</text>'
        f"</svg>"
    )


def fmt_odds(value: int | float) -> str:
    v = int(round(float(value)))
    return f"+{v}" if v > 0 else str(v)


# --------------------------------------------------------------------------- #
# Component wrappers
# --------------------------------------------------------------------------- #
def stat_card(label: str, value: str, badge: str, badge_bg: str, sub_html: str, spark: str) -> None:
    st.markdown(
        f'<div class="hc-stat"><div class="top"><div class="lbl">{label}</div>'
        f'<div class="badge" style="background:{badge_bg}">{badge}</div></div>'
        f'<div class="val">{value}</div><div class="sub">{sub_html}</div>'
        f'<div class="spark">{spark}</div></div>',
        unsafe_allow_html=True,
    )


def _panel_head(title: str, link: str | None = None) -> str:
    link_html = f'<span class="hc-panel-link">{link}</span>' if link else ""
    return (
        f'<div class="hc-panel-head"><span class="hc-panel-title">{title}</span>{link_html}</div>'
    )


def html_panel(title: str, inner_html: str, link: str | None = None) -> None:
    """Render a complete panel (title + HTML body) as one block."""
    st.markdown(
        f'<div class="hc-panel">{_panel_head(title, link)}{inner_html}</div>',
        unsafe_allow_html=True,
    )


def panel_title(title: str, link: str | None = None) -> None:
    """Title row for use inside an interactive bordered container."""
    st.markdown(_panel_head(title, link), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Backwards-compatible helpers used by other pages
# --------------------------------------------------------------------------- #
def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div style="margin-bottom:1rem"><div class="hc-greet">{title}</div>'
        f'<div class="hc-greet-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def metric_row(metrics: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value, sub) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="hc-stat" style="min-height:96px"><div class="lbl">{label}</div>'
                f'<div class="val" style="font-size:1.4rem">{value}</div>'
                f'<div class="sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )


def section(title: str) -> None:
    st.markdown(
        f'<div style="color:{TEXT};font-weight:700;font-size:1.05rem;margin:1.3rem 0 .6rem 0;'
        f'padding-bottom:.35rem;border-bottom:1px solid {BORDER}">{title}</div>',
        unsafe_allow_html=True,
    )


def pick_card(title: str, verdict: str, body: str, tag_class: str = "hc-tag") -> None:
    color = {"hc-tag": GREEN_SOFT, "hc-tag-skip": RED, "hc-tag-warn": AMBER}.get(tag_class, GREEN_SOFT)
    st.markdown(
        f'<div class="hc-panel" style="margin-bottom:.6rem">'
        f'<span style="color:{color};font-size:.74rem;font-weight:700">{verdict}</span>'
        f'<div style="color:{TEXT};font-weight:700;margin:.15rem 0">{title}</div>'
        f'<div style="color:{MUTED};font-size:.85rem">{body}</div></div>',
        unsafe_allow_html=True,
    )


def dataframe_compact(df: pd.DataFrame, height: int = 360) -> None:
    st.dataframe(df, use_container_width=True, hide_index=True, height=height)


def source_status_strip(sources: Sequence[dict[str, str]]) -> None:
    """Render freshness pills. Each dict: name, status (live|stale|off|err), detail."""
    pills = []
    for src in sources:
        status = src.get("status", "off")
        name = src.get("name", "Source")
        detail = src.get("detail", "")
        pills.append(
            f'<span class="hc-source-pill {status}" title="{detail}">{name}: {detail or status}</span>'
        )
    st.markdown(f'<div class="hc-sources">{"".join(pills)}</div>', unsafe_allow_html=True)


def verdict_tag_class(verdict: str) -> str:
    if "Strong" in verdict or "Good" in verdict:
        return "hc-tag"
    if "Skip" in verdict or "Bad" in verdict:
        return "hc-tag-skip"
    return "hc-tag-warn"
