import csv
import html
import io
import math
import re
import time
from urllib.parse import quote_plus, urlparse

import pandas as pd
import streamlit as st

from connectors.competitor_scanner import (
    scan_competitor_store,
    RateLimitError,
)


# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Shopify Product Hunter",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# STYLING
# --------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --brand: #008060;
    --brand-2: #00A47C;
    --brand-dark: #00352B;
    --brand-soft: #E3F5EF;
    --accent: #F5B83D;
    --ink: #14212B;
    --muted: #667085;
    --line: #E4E9EF;
    --bg: #F3F6F9;
    --card: #FFFFFF;
    --warn-bg: #FFF6DB;
    --warn-ink: #8A6100;
    --err-bg: #FDEBEC;
    --err-ink: #B42318;
    --shadow-sm: 0 1px 2px rgba(16, 24, 40, 0.05);
    --shadow-md: 0 10px 28px rgba(16, 24, 40, 0.10);
}

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}

.stApp {
    background:
        radial-gradient(1200px 500px at 85% -10%, rgba(0, 164, 124, 0.10), transparent 60%),
        var(--bg);
}

/* Hide default Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 1280px;
    animation: ph-fade 0.45s ease both;
}

@keyframes ph-fade {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ---------- Hero ---------- */
.ph-hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(125deg, var(--brand-dark) 0%, #005A46 45%, var(--brand-2) 100%);
    color: #fff;
    padding: 32px 36px 28px 36px;
    border-radius: 20px;
    margin-bottom: 22px;
    box-shadow: 0 14px 34px rgba(0, 53, 43, 0.25);
}
.ph-hero::before {
    content: "";
    position: absolute;
    right: -70px; top: -90px;
    width: 300px; height: 300px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.20), transparent 70%);
}
.ph-hero::after {
    content: "";
    position: absolute;
    right: 140px; bottom: -120px;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(245,184,61,0.28), transparent 70%);
}
.ph-hero h1 {
    position: relative; z-index: 1;
    margin: 0 0 8px 0;
    padding: 0;
    font-size: 2.05rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #fff;
}
.ph-hero p {
    position: relative; z-index: 1;
    margin: 0 0 18px 0;
    max-width: 640px;
    font-size: 1rem;
    line-height: 1.55;
    color: rgba(255, 255, 255, 0.88);
}
.ph-chips { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 8px; }
.ph-chip {
    padding: 6px 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.22);
    color: #fff;
    font-size: 0.82rem;
    font-weight: 600;
    backdrop-filter: blur(4px);
}

/* ---------- Tabs (pill style) ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: var(--card);
    padding: 6px;
    border-radius: 14px;
    border: 1px solid var(--line);
    box-shadow: var(--shadow-sm);
    width: fit-content;
    margin-bottom: 14px;
}
.stTabs [data-baseweb="tab"] {
    height: 42px;
    padding: 0 20px;
    border-radius: 10px;
    font-weight: 600;
    color: var(--muted);
    background: transparent;
}
.stTabs [aria-selected="true"] {
    background: var(--brand-soft) !important;
    color: var(--brand-dark) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ---------- Bordered containers ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; }

/* ---------- Metric cards ---------- */
[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-left: 4px solid var(--brand);
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] p {
    color: var(--muted);
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
[data-testid="stMetricValue"] {
    color: var(--ink);
    font-weight: 800;
}

/* ---------- Inputs ---------- */
.stTextArea textarea, .stTextInput input {
    border-radius: 10px !important;
    border: 1px solid var(--line) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--brand) !important;
    box-shadow: 0 0 0 3px rgba(0, 128, 96, 0.15) !important;
}

/* ---------- Buttons ---------- */
div.stButton > button, div.stDownloadButton > button {
    border-radius: 11px;
    font-weight: 600;
    padding: 0.6rem 1.3rem;
    border: 1px solid var(--line);
    background: var(--card);
    transition: all 0.15s ease;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand) 0%, var(--brand-2) 100%);
    border: none;
    color: #fff;
    box-shadow: 0 6px 16px rgba(0, 128, 96, 0.30);
    padding: 0.7rem 1.8rem;
    font-size: 1rem;
}
div.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(0, 128, 96, 0.38);
    color: #fff;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    border-color: var(--brand);
    color: var(--brand);
}

/* ---------- Section titles ---------- */
.ph-section {
    font-size: 1.08rem;
    font-weight: 700;
    color: var(--ink);
    margin: 2px 0 2px 0;
}
.ph-hint {
    font-size: 0.86rem;
    color: var(--muted);
    margin-bottom: 10px;
}
.ph-step {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--brand), var(--brand-2));
    color: #fff;
    font-size: 0.8rem;
    font-weight: 700;
    margin-right: 10px;
    box-shadow: 0 3px 8px rgba(0, 128, 96, 0.30);
}

/* ---------- Notice ---------- */
.ph-notice {
    background: var(--warn-bg);
    color: var(--warn-ink);
    border: 1px solid #F3DFA3;
    border-radius: 12px;
    padding: 11px 16px;
    font-size: 0.88rem;
    margin-bottom: 16px;
}

/* ---------- Status pills ---------- */
.ph-pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 14px 0; }
.ph-pill {
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
}
.ph-pill.ok { background: var(--brand-soft); color: var(--brand-dark); }
.ph-pill.warn { background: var(--warn-bg); color: var(--warn-ink); }
.ph-pill.err { background: var(--err-bg); color: var(--err-ink); }

/* ---------- How it works / empty state ---------- */
.ph-steps {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-top: 22px;
}
.ph-stepcard {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 22px 22px 20px 22px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.ph-stepcard:hover { box-shadow: var(--shadow-md); transform: translateY(-3px); }
.ph-stepicon {
    width: 46px; height: 46px;
    border-radius: 12px;
    background: var(--brand-soft);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
    margin-bottom: 12px;
}
.ph-stepcard h4 { margin: 0 0 6px 0; padding: 0; font-size: 1rem; font-weight: 700; color: var(--ink); }
.ph-stepcard p { margin: 0; font-size: 0.88rem; line-height: 1.5; color: var(--muted); }
.ph-empty {
    text-align: center;
    background: var(--card);
    border: 2px dashed var(--line);
    border-radius: 18px;
    padding: 46px 20px;
    margin-top: 10px;
}
.ph-empty .big { font-size: 2.6rem; margin-bottom: 6px; }
.ph-empty h3 { margin: 0 0 6px 0; padding: 0; font-size: 1.15rem; color: var(--ink); }
.ph-empty p { margin: 0; color: var(--muted); font-size: 0.92rem; }

/* ---------- Product cards ---------- */
.ph-card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 20px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.ph-card:hover { box-shadow: var(--shadow-md); transform: translateY(-4px); }
.ph-card-img {
    position: relative;
    height: 230px;
    background: linear-gradient(135deg, #EEF1F4, #E4E9EF);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9AA3AE;
    font-size: 0.85rem;
    overflow: hidden;
}
.ph-card-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.35s ease;
}
.ph-card:hover .ph-card-img img { transform: scale(1.05); }
.ph-chip-store {
    position: absolute;
    left: 10px; top: 10px;
    background: rgba(20, 33, 43, 0.78);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
    backdrop-filter: blur(4px);
}
.ph-chip-hot {
    position: absolute;
    right: 10px; top: 10px;
    background: var(--accent);
    color: #4A3200;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    box-shadow: 0 3px 8px rgba(245, 184, 61, 0.45);
}
.ph-card-body { padding: 14px 16px 16px 16px; }
.ph-title {
    font-size: 0.98rem;
    font-weight: 600;
    color: var(--ink);
    line-height: 1.35;
    min-height: 2.7em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.ph-meta { font-size: 0.8rem; color: var(--muted); margin: 6px 0 12px 0; min-height: 1.2em; }
.ph-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
}
.ph-price { font-size: 1.12rem; font-weight: 800; color: var(--brand-dark); }
.ph-link {
    padding: 7px 14px;
    border-radius: 9px;
    background: var(--brand-soft);
    color: var(--brand-dark) !important;
    font-weight: 700;
    font-size: 0.8rem;
    text-decoration: none !important;
    white-space: nowrap;
    transition: all 0.15s ease;
}
.ph-link:hover { background: var(--brand); color: #fff !important; }

/* ---------- Sidebar (dark green) ---------- */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(185deg, #00352B 0%, #004D3C 60%, #006650 100%);
}
[data-testid="stSidebar"] { border-right: none; }
.ph-brand { font-size: 1.2rem; font-weight: 800; color: #fff; margin-bottom: 2px; }
.ph-brand-sub { font-size: 0.82rem; color: rgba(255, 255, 255, 0.68); margin-bottom: 14px; }
.ph-side-title {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.55);
    font-weight: 700;
    margin: 20px 0 8px 0;
}
.ph-side-tip { font-size: 0.86rem; color: rgba(255, 255, 255, 0.88); line-height: 1.65; }
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-left: 4px solid var(--accent);
    box-shadow: none;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p { color: rgba(255, 255, 255, 0.72); }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #fff; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small { color: rgba(255, 255, 255, 0.7); }

/* ---------- Footer ---------- */
.ph-footer {
    text-align: center;
    color: var(--muted);
    font-size: 0.8rem;
    margin-top: 30px;
    padding-top: 16px;
    border-top: 1px solid var(--line);
}

@media (max-width: 900px) {
    .ph-steps { grid-template-columns: 1fr; }
}
/* ---------- Winning-score extras ---------- */
.ph-chip-hot.mid { background: #DCE8FF; color: #1D3F8F; box-shadow: 0 3px 8px rgba(29, 63, 143, 0.25); }
.ph-chip-hot.low { background: #EEF1F4; color: #667085; box-shadow: none; }
.ph-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 10px 0; min-height: 24px; }
.ph-tag {
    font-size: 0.72rem; font-weight: 600; padding: 3px 9px; border-radius: 999px;
    background: var(--brand-soft); color: var(--brand-dark);
}
.ph-tag.ad { background: #E8EEFF; color: #2B4BB5; }
.ph-tag.sale { background: #FDE7EA; color: #B42318; }
.ph-tools { display: flex; gap: 8px; margin-bottom: 12px; }
.ph-tool {
    font-size: 0.76rem; font-weight: 600; color: var(--muted) !important;
    text-decoration: none !important; border: 1px solid var(--line);
    padding: 4px 10px; border-radius: 8px; transition: all 0.15s ease;
}
.ph-tool:hover { border-color: var(--brand); color: var(--brand) !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------
# DISPLAY HELPERS
# --------------------------------------------------

def section(title, hint="", step=None):
    badge = f'<span class="ph-step">{step}</span>' if step else ""
    st.markdown(
        f'<div class="ph-section">{badge}{html.escape(title)}</div>',
        unsafe_allow_html=True,
    )
    if hint:
        st.markdown(
            f'<div class="ph-hint">{html.escape(hint)}</div>',
            unsafe_allow_html=True,
        )


def host_of(url):
    try:
        return urlparse(str(url or "")).netloc.replace("www.", "")
    except ValueError:
        return ""


def safe_url(url):
    """Return an HTML-escaped http(s) URL, or an empty string."""
    url = str(url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return html.escape(url, quote=True)
    return ""


def _num(value):
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


STRONG_SCORE = 65
PROMISING_SCORE = 40


def get_score(product):
    """Winning score 0-100 from a scan, or parsed from saved status text."""
    value = _num(product.get("winning_score"))
    if value is not None:
        return int(value)

    match = re.search(
        r"score\s+(\d+)", str(product.get("popularity_status") or "")
    )
    return int(match.group(1)) if match else None


def signal_tier(score):
    if score is None:
        return "low", "Not scored"
    if score >= STRONG_SCORE:
        return "hot", "Strong signal"
    if score >= PROMISING_SCORE:
        return "mid", "Promising"
    return "low", "Weak signal"


def get_ads(product):
    """Ad pixels found for the store, from the scan or saved evidence."""
    ads = str(product.get("ad_signals") or "").strip()
    if ads and ads.lower() != "nan":
        return ads

    match = re.search(
        r"Store ad pixels:\s*([^;]+)",
        str(product.get("popularity_evidence") or ""),
    )
    return match.group(1).strip() if match else ""


def search_query(title):
    words = re.sub(r"[^\w\s]", " ", str(title or "")).split()
    return " ".join(words[:5])


def ad_library_url(title):
    return (
        "https://www.facebook.com/ads/library/?active_status=active"
        "&ad_type=all&country=ALL&media_type=all"
        "&search_type=keyword_unordered&q=" + quote_plus(search_query(title))
    )


def trends_url(title):
    return (
        "https://trends.google.com/trends/explore?q="
        + quote_plus(search_query(title))
    )


def format_price(product):
    low = _num(product.get("price_min"))
    high = _num(product.get("price_max"))

    if (low in (None, 0)) and (high in (None, 0)):
        return "Price not available"

    if low is None:
        low = high
    if high is None:
        high = low

    currency = str(product.get("currency") or "").strip()
    prefix = (
        "" if currency.lower() in ("", "unknown", "nan") else currency + " "
    )

    def fmt(x):
        return f"{x:,.0f}" if x == int(x) else f"{x:,.2f}"

    if high == low:
        return f"{prefix}{fmt(low)}"
    return f"{prefix}{fmt(low)} – {fmt(high)}"


def product_card_html(product):
    title = html.escape(str(product.get("title") or "Untitled product"))
    vendor = str(product.get("vendor") or "").strip()
    ptype = str(product.get("product_type") or "").strip()
    store = html.escape(
        host_of(product.get("store_url") or product.get("product_url"))
    )
    price = html.escape(format_price(product))
    link = safe_url(product.get("product_url"))
    image = safe_url(product.get("image_url"))

    meta = " · ".join(x for x in (vendor, ptype) if x and x.lower() != "nan")
    meta = html.escape(meta)

    status = str(product.get("popularity_status") or "")
    score = get_score(product)
    tier, _tier_label = signal_tier(score)

    if score is not None:
        icon = "🔥" if tier == "hot" else ("⭐" if tier == "mid" else "•")
        hot_html = f'<span class="ph-chip-hot {tier}">{icon} {score}</span>'
    elif status.startswith("Listed on best"):
        hot_html = '<span class="ph-chip-hot">⭐ Best seller</span>'
    else:
        hot_html = ""

    tags = []

    rank = _num(product.get("best_rank"))
    if rank is not None:
        tags.append(f'<span class="ph-tag">🏆 #{int(rank)} best-selling</span>')

    for ad_name in [a.strip() for a in get_ads(product).split(",") if a.strip()]:
        tags.append(f'<span class="ph-tag ad">📣 {html.escape(ad_name)}</span>')

    discount = _num(product.get("discount_pct"))
    if discount:
        tags.append(f'<span class="ph-tag sale">🏷️ {int(discount)}% off</span>')

    tags_html = '<div class="ph-tags">' + "".join(tags) + "</div>"

    raw_title = str(product.get("title") or "")
    tools_html = (
        '<div class="ph-tools">'
        f'<a class="ph-tool" href="{html.escape(ad_library_url(raw_title), quote=True)}" '
        'target="_blank" rel="noopener noreferrer">Meta Ads ↗</a>'
        f'<a class="ph-tool" href="{html.escape(trends_url(raw_title), quote=True)}" '
        'target="_blank" rel="noopener noreferrer">Trends ↗</a>'
        "</div>"
    )

    image_html = (
        f'<img src="{image}" loading="lazy" alt="">'
        if image
        else "No image"
    )
    link_html = (
        f'<a class="ph-link" href="{link}" target="_blank" '
        f'rel="noopener noreferrer">View ↗</a>'
        if link
        else ""
    )

    return "".join([
        '<div class="ph-card">',
        f'<div class="ph-card-img">{image_html}',
        f'<span class="ph-chip-store">{store}</span>{hot_html}</div>',
        '<div class="ph-card-body">',
        f'<div class="ph-title">{title}</div>',
        f'<div class="ph-meta">{meta}</div>',
        tags_html,
        tools_html,
        f'<div class="ph-foot"><div class="ph-price">{price}</div>'
        f'{link_html}</div>',
        "</div></div>",
    ])


TABLE_COLUMNS = [
    "image_url", "title", "winning_score", "ad_signals", "store_url",
    "vendor", "product_type", "price_min", "price_max", "currency",
    "popularity_status", "product_url",
]


def render_table(products):
    df = pd.DataFrame(products)
    df["winning_score"] = [get_score(p) for p in products]
    df["ad_signals"] = [get_ads(p) for p in products]
    columns = [c for c in TABLE_COLUMNS if c in df.columns]
    df = df[columns]

    config = {
        "image_url": st.column_config.ImageColumn("Image", width="small"),
        "title": st.column_config.TextColumn("Product", width="large"),
        "store_url": st.column_config.TextColumn("Store"),
        "vendor": st.column_config.TextColumn("Vendor"),
        "product_type": st.column_config.TextColumn("Type"),
        "price_min": st.column_config.NumberColumn(
            "Min price", format="%.0f"
        ),
        "price_max": st.column_config.NumberColumn(
            "Max price", format="%.0f"
        ),
        "currency": st.column_config.TextColumn("Currency"),
        "winning_score": st.column_config.ProgressColumn(
            "Winning score", min_value=0, max_value=100, format="%d"
        ),
        "ad_signals": st.column_config.TextColumn("Ads detected"),
        "popularity_status": st.column_config.TextColumn("Signal"),
        "product_url": st.column_config.LinkColumn(
            "Link", display_text="Open"
        ),
    }

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={k: v for k, v in config.items() if k in columns},
    )


def render_products(products, key):
    """Card grid (paged) or table, with a view switch."""

    if not products:
        st.info("No products match your filters.")
        return

    view = st.radio(
        "View",
        ["Cards", "Table"],
        horizontal=True,
        key=f"{key}_view",
        label_visibility="collapsed",
    )

    if view == "Table":
        render_table(products)
        return

    per_page = 12
    total_pages = max(1, math.ceil(len(products) / per_page))
    page = 1

    if total_pages > 1:
        page = st.number_input(
            f"Page (1–{total_pages})",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key=f"{key}_page",
        )

    start = (int(page) - 1) * per_page
    chunk = products[start:start + per_page]

    for row_start in range(0, len(chunk), 3):
        columns = st.columns(3)
        for column, product in zip(columns, chunk[row_start:row_start + 3]):
            column.markdown(
                product_card_html(product), unsafe_allow_html=True
            )


def filter_products(products, key):
    """Search, store filter, sort and best-seller filter."""

    stores = sorted({
        host_of(p.get("store_url") or p.get("product_url"))
        for p in products
        if host_of(p.get("store_url") or p.get("product_url"))
    })

    col_search, col_store, col_sort = st.columns([2, 2, 1.4])

    search = col_search.text_input(
        "Search",
        placeholder="Search by product name, vendor or type…",
        key=f"{key}_search",
        label_visibility="collapsed",
    )
    chosen_stores = col_store.multiselect(
        "Stores",
        stores,
        placeholder="All stores",
        key=f"{key}_stores",
        label_visibility="collapsed",
    )
    sort_by = col_sort.selectbox(
        "Sort",
        [
            "Best signals first",
            "Price: low to high",
            "Price: high to low",
            "Name: A to Z",
        ],
        key=f"{key}_sort",
        label_visibility="collapsed",
    )

    only_best = st.checkbox(
        "Show only strong signals (score 65+)",
        key=f"{key}_best",
    )

    result = list(products)

    if search.strip():
        needle = search.strip().lower()
        result = [
            p for p in result
            if needle in " ".join(
                str(p.get(f) or "")
                for f in ("title", "vendor", "product_type")
            ).lower()
        ]

    if chosen_stores:
        result = [
            p for p in result
            if host_of(p.get("store_url") or p.get("product_url"))
            in chosen_stores
        ]

    if only_best:
        result = [
            p for p in result
            if (get_score(p) or 0) >= STRONG_SCORE
        ]

    def price_key(p):
        value = _num(p.get("price_min"))
        return value if value is not None else float("inf")

    if sort_by == "Best signals first":
        result.sort(
            key=lambda p: get_score(p) if get_score(p) is not None else -1,
            reverse=True,
        )
    elif sort_by == "Price: low to high":
        result.sort(key=price_key)
    elif sort_by == "Price: high to low":
        result.sort(
            key=lambda p: _num(p.get("price_min")) or -1,
            reverse=True,
        )
    elif sort_by == "Name: A to Z":
        result.sort(key=lambda p: str(p.get("title") or "").lower())

    return result


# --------------------------------------------------
# DATABASE FUNCTIONS
# --------------------------------------------------

def get_database_functions():
    try:
        from database.db import save_products, get_products
        return save_products, get_products, None
    except Exception as exc:
        return None, None, str(exc)


def get_store_url(product):
    """Derive the store URL from the product URL if it is missing."""
    store_url = str(product.get("store_url") or "").strip()

    if store_url:
        parsed_store = urlparse(store_url)

        if (
            parsed_store.scheme in ("http", "https")
            and parsed_store.netloc
        ):
            return f"{parsed_store.scheme}://{parsed_store.netloc}"

        raise ValueError(f"Invalid store URL: {store_url}")

    product_url = str(product.get("product_url") or "").strip()
    parsed_product = urlparse(product_url)

    if (
        parsed_product.scheme in ("http", "https")
        and parsed_product.netloc
    ):
        return f"{parsed_product.scheme}://{parsed_product.netloc}"

    raise ValueError(
        f"Product '{product.get('title', 'Unknown')}' needs a valid "
        "store_url or product_url."
    )


def save_to_existing_database(products):
    """
    Use the existing database.db save_products(store_url, products)
    function. The database is never reset.
    """
    save_products, _, error = get_database_functions()

    if error:
        raise RuntimeError("Could not import database.db: " + error)

    if not callable(save_products):
        raise RuntimeError("save_products() is not available.")

    if not products:
        return 0

    grouped_products = {}

    for original_product in products:
        product = dict(original_product)

        title = str(product.get("title") or "").strip()
        product_url = str(product.get("product_url") or "").strip()

        if not title:
            raise ValueError("Every product needs a title.")

        parsed_url = urlparse(product_url)

        if (
            parsed_url.scheme not in ("http", "https")
            or not parsed_url.netloc
        ):
            raise ValueError(
                f"'{title}' needs a valid product_url."
            )

        product["title"] = title
        product["product_url"] = product_url
        product["store_url"] = get_store_url(product)

        grouped_products.setdefault(
            product["store_url"], []
        ).append(product)

    total_processed = 0

    for store_url, store_products in grouped_products.items():
        result = save_products(store_url, store_products)

        if isinstance(result, int):
            total_processed += result
        else:
            total_processed += len(store_products)

    return total_processed


def read_existing_database():
    _, get_products, error = get_database_functions()

    if error:
        raise RuntimeError("Could not import database.db: " + error)

    if not callable(get_products):
        raise RuntimeError("get_products() is not available.")

    result = get_products()

    if result is None:
        return []

    if isinstance(result, pd.DataFrame):
        return result.to_dict(orient="records")

    return list(result)


# --------------------------------------------------
# CSV NORMALIZATION
# --------------------------------------------------

def normalize_csv_columns(df):
    aliases = {
        "product_id": ["product_id", "id", "sku", "handle"],
        "title": ["title", "product", "product_name", "name"],
        "vendor": ["vendor", "brand", "manufacturer"],
        "product_type": ["product_type", "type", "category"],
        "price_min": [
            "price_min", "price", "minimum_price", "selling_price"
        ],
        "price_max": ["price_max", "maximum_price"],
        "currency": ["currency", "currency_code"],
        "description": ["description", "body_html", "details"],
        "product_url": ["product_url", "url", "link"],
        "image_url": ["image_url", "image", "image_src"],
        "store_url": ["store_url", "store", "website"],
        "store_type": ["store_type", "platform"],
        "popularity_status": ["popularity_status", "popularity"],
        "popularity_evidence": ["popularity_evidence", "evidence"],
    }

    original_columns = {
        str(column).strip().lower(): column for column in df.columns
    }

    result = pd.DataFrame(index=df.index)

    for target, candidates in aliases.items():
        for candidate in candidates:
            if candidate in original_columns:
                result[target] = df[original_columns[candidate]]
                break

    if "title" not in result.columns:
        raise ValueError(
            "The CSV needs a title column. Name it title, "
            "product_name or name."
        )

    result["title"] = (
        result["title"].fillna("").astype(str).str.strip()
    )

    result = result[result["title"] != ""].copy()

    if result.empty:
        return []

    if "product_id" not in result.columns:
        result["product_id"] = result["title"]

    if "vendor" not in result.columns:
        result["vendor"] = ""

    if "product_type" not in result.columns:
        result["product_type"] = ""

    if "price_min" not in result.columns:
        result["price_min"] = 0

    if "price_max" not in result.columns:
        result["price_max"] = result["price_min"]

    for column in ("price_min", "price_max"):
        result[column] = pd.to_numeric(
            result[column], errors="coerce"
        ).fillna(0)

    defaults = {
        "currency": "Unknown",
        "description": "",
        "product_url": "",
        "image_url": "",
        "store_url": "",
        "store_type": "CSV Import",
        "popularity_status": "Unverified",
        "popularity_evidence": (
            "Imported from CSV; not independently verified."
        ),
    }

    for column, default in defaults.items():
        if column not in result.columns:
            result[column] = default
        else:
            result[column] = result[column].fillna(default)

    records = result.to_dict(orient="records")

    for product in records:
        product["product_url"] = str(
            product.get("product_url") or ""
        ).strip()

        product["store_url"] = str(
            product.get("store_url") or ""
        ).strip()

        if not product["product_url"]:
            raise ValueError(
                f"CSV product '{product['title']}' is missing a "
                "product_url. Add a valid URL for every product."
            )

        product["store_url"] = get_store_url(product)

    return records


def csv_template_bytes():
    columns = [
        "product_id",
        "title",
        "vendor",
        "product_type",
        "price_min",
        "price_max",
        "currency",
        "description",
        "product_url",
        "image_url",
        "store_url",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    writer.writerow({
        "product_id": "SKU-001",
        "title": "Replace with real product",
        "vendor": "Example brand",
        "product_type": "Fashion",
        "price_min": "2500",
        "price_max": "3000",
        "currency": "PKR",
        "description": "Replace with actual product details",
        "product_url": "https://example.com/products/item",
        "image_url": "",
        "store_url": "https://example.com",
    })

    return output.getvalue().encode("utf-8-sig")


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "hunter_scan_report" not in st.session_state:
    st.session_state["hunter_scan_report"] = []

if "hunter_scan_products" not in st.session_state:
    st.session_state["hunter_scan_products"] = []

if "hunter_scan_saved" not in st.session_state:
    st.session_state["hunter_scan_saved"] = False


# --------------------------------------------------
# HERO
# --------------------------------------------------

st.markdown(
    "".join([
        '<div class="ph-hero">',
        "<h1>🛍️ Shopify Product Hunter</h1>",
        "<p>Scan competitor stores, import your own product lists, and "
        "keep every product you find in one place.</p>",
        '<div class="ph-chips">',
        '<span class="ph-chip">⚡ Multi-store scanning</span>',
        '<span class="ph-chip">📄 CSV import</span>',
        '<span class="ph-chip">🔥 Winning-product score</span>',
        '<span class="ph-chip">🗄️ One database</span>',
        "</div></div>",
    ]),
    unsafe_allow_html=True,
)


# --------------------------------------------------
# TABS
# --------------------------------------------------

tab_scan, tab_csv, tab_db = st.tabs([
    "🌐  Store Scanner",
    "📄  CSV Import",
    "🗄️  Product Database",
])

db_products = []
db_error = None


# --------------------------------------------------
# STORE SCANNER
# --------------------------------------------------

with tab_scan:
    st.markdown(
        '<div class="ph-notice">ℹ️ The <b>Winning score</b> is an estimate '
        "from public signals: best-selling rank, ad pixels on the store, "
        "discounts and stock. It is not real sales data. Open the "
        "<b>Meta Ads</b> link on a product to confirm ads are really "
        "running before you buy stock. If a store answers with HTTP 429, "
        "do not scan it again right away.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2], gap="large")

    with left:
        with st.container(border=True):
            section(
                "Add competitor stores",
                "One store URL per line. Each store is scanned once.",
                step=1,
            )
            store_text = st.text_area(
                "Store URLs",
                value=(
                    "https://www.limelight.pk\n"
                    "https://www.outfitters.com.pk"
                ),
                height=215,
                key="hunter_store_urls",
                label_visibility="collapsed",
            )

    with right:
        with st.container(border=True):
            section(
                "Scan settings",
                "Gentle settings help you avoid rate limits.",
                step=2,
            )
            product_limit = st.slider(
                "Products per store",
                min_value=1,
                max_value=20,
                value=10,
                key="hunter_product_limit",
            )
            delay_seconds = st.slider(
                "Pause between stores (seconds)",
                min_value=2,
                max_value=30,
                value=5,
                key="hunter_delay_seconds",
                help="Waiting between stores lowers the chance of a 429.",
            )
            check_best_sellers = st.checkbox(
                "Rank products by the store's best-selling list",
                value=True,
                key="hunter_rank_best",
                help="Asks the store for its best-selling order. "
                "This is the strongest sales signal.",
            )
            check_ads = st.checkbox(
                "Detect ad pixels (Meta, TikTok, Google)",
                value=True,
                key="hunter_check_ads",
                help="Reads the store homepage once. A store with ad "
                "pixels is very likely running paid ads.",
            )

    start_scan = st.button(
        "🚀  Start scan", type="primary", key="hunter_start_scan"
    )

    if start_scan:
        urls = list(dict.fromkeys(
            line.strip()
            for line in store_text.splitlines()
            if line.strip()
        ))

        if not urls:
            st.error("Please enter at least one store URL.")
        else:
            all_products = []
            report = []

            # Clear old results; the database is never cleared.
            st.session_state["hunter_scan_saved"] = False

            progress = st.progress(0)
            status_text = st.empty()

            for index, url in enumerate(urls):
                if index > 0:
                    status_text.info(
                        f"Pausing {delay_seconds}s before the next store…"
                    )
                    time.sleep(delay_seconds)

                status_text.info(
                    f"Scanning store {index + 1} of {len(urls)}: {url}"
                )

                try:
                    products = scan_competitor_store(
                        url,
                        limit=product_limit,
                        include_best_sellers=check_best_sellers,
                        check_ads=check_ads,
                    )

                    products = list(products or [])
                    all_products.extend(products)

                    report.append({
                        "Store": url,
                        "Status": "Success",
                        "Products": len(products),
                        "Details": "",
                    })

                except Exception as exc:
                    message = str(exc)

                    is_rate_limited = (
                        isinstance(exc, RateLimitError)
                        or "429" in message
                    )

                    report.append({
                        "Store": url,
                        "Status": (
                            "Rate limited"
                            if is_rate_limited
                            else "Failed"
                        ),
                        "Products": 0,
                        "Details": message,
                    })

                progress.progress((index + 1) / len(urls))

            status_text.empty()
            progress.empty()

            st.session_state["hunter_scan_report"] = report
            st.session_state["hunter_scan_products"] = all_products

    # Results are drawn outside the button block so they survive
    # clicks on filters and other widgets.
    report = st.session_state["hunter_scan_report"]
    all_products = st.session_state["hunter_scan_products"]

    if not report and not all_products:
        st.markdown(
            "".join([
                '<div class="ph-steps">',
                '<div class="ph-stepcard"><div class="ph-stepicon">🔗</div>',
                "<h4>1. Add stores</h4>",
                "<p>Paste the URLs of competitor Shopify stores, one per "
                "line.</p></div>",
                '<div class="ph-stepcard"><div class="ph-stepicon">🔍</div>',
                "<h4>2. Scan and review</h4>",
                "<p>Pull public product data and filter it by store, price "
                "or name.</p></div>",
                '<div class="ph-stepcard"><div class="ph-stepicon">💾</div>',
                "<h4>3. Save winners</h4>",
                "<p>Keep the products worth tracking in your database.</p>"
                "</div></div>",
            ]),
            unsafe_allow_html=True,
        )

    if report:
        st.divider()
        section("Scan results")

        succeeded = sum(1 for r in report if r["Status"] == "Success")

        k1, k2, k3 = st.columns(3)
        k1.metric("Stores scanned", len(report))
        k2.metric("Successful", f"{succeeded} / {len(report)}")
        k3.metric("Products found", len(all_products))

        pills = []
        for row in report:
            name = html.escape(host_of(row["Store"]) or row["Store"])
            if row["Status"] == "Success":
                pills.append(
                    f'<span class="ph-pill ok">✓ {name} · '
                    f'{row["Products"]} products</span>'
                )
            elif row["Status"] == "Rate limited":
                pills.append(
                    f'<span class="ph-pill warn">⏳ {name} · '
                    "rate limited</span>"
                )
            else:
                pills.append(
                    f'<span class="ph-pill err">✕ {name} · failed</span>'
                )

        st.markdown(
            '<div class="ph-pills">' + "".join(pills) + "</div>",
            unsafe_allow_html=True,
        )

        for row in report:
            if row["Status"] == "Rate limited":
                st.warning(
                    f'**{row["Store"]}** — {row["Details"].rstrip(".")}. '
                    "Please wait a few minutes before scanning it again."
                )
            elif row["Status"] == "Failed":
                st.error(f'**{row["Store"]}** — {row["Details"]}')

    if all_products:
        st.divider()
        section(
            "Review products",
            "Search, filter and sort before saving anything.",
        )

        top_picks = sorted(
            [p for p in all_products if get_score(p) is not None],
            key=get_score,
            reverse=True,
        )[:5]

        if top_picks:
            st.markdown("**🏆 Top picks from this scan**")
            st.dataframe(
                pd.DataFrame([
                    {
                        "Score": get_score(p),
                        "Product": p.get("title"),
                        "Store": host_of(
                            p.get("store_url") or p.get("product_url")
                        ),
                        "Price": format_price(p),
                        "Why": p.get("popularity_evidence"),
                        "Ads": ad_library_url(p.get("title")),
                        "Trend": trends_url(p.get("title")),
                    }
                    for p in top_picks
                ]),
                width="stretch",
                hide_index=True,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score", min_value=0, max_value=100, format="%d"
                    ),
                    "Why": st.column_config.TextColumn(
                        "Why it scored", width="large"
                    ),
                    "Ads": st.column_config.LinkColumn(
                        "Check ads", display_text="Meta Ad Library ↗"
                    ),
                    "Trend": st.column_config.LinkColumn(
                        "Demand", display_text="Google Trends ↗"
                    ),
                },
            )

        filtered = filter_products(all_products, "scan")
        st.caption(
            f"Showing {len(filtered)} of {len(all_products)} products"
        )
        render_products(filtered, "scan")

        st.divider()

        with st.container(border=True):
            section(
                "Save to database",
                "Products you save are added to (or updated in) your "
                "existing database.",
                step=3,
            )

            csv_bytes = pd.DataFrame(all_products).to_csv(
                index=False
            ).encode("utf-8-sig")

            if st.session_state["hunter_scan_saved"]:
                st.success(
                    "These products were already sent to the database "
                    "in this scan."
                )
            else:
                confirm_save = st.checkbox(
                    "I reviewed these products and want to save them.",
                    key="confirm_save_scanned_products",
                )

                save_col, download_col, _ = st.columns([1.2, 1.4, 3])

                if save_col.button(
                    f"💾  Save {len(all_products)} products",
                    type="primary",
                    key="save_scanned_products",
                ):
                    if not confirm_save:
                        st.warning(
                            "Please tick the confirmation box first."
                        )
                    else:
                        try:
                            count = save_to_existing_database(
                                all_products
                            )
                            st.session_state["hunter_scan_saved"] = True
                            st.success(
                                f"{count} product records were sent to "
                                "the database. Check the Product Database "
                                "tab to confirm."
                            )
                        except Exception as exc:
                            st.error(
                                "Could not save products: " + str(exc)
                            )

                download_col.download_button(
                    "⬇️  Download as CSV",
                    data=csv_bytes,
                    file_name="scanned_products.csv",
                    mime="text/csv",
                    key="download_scanned_products",
                )

    elif report:
        st.info(
            "No products came back from this scan. The store's public "
            "endpoint may be unavailable, or the request was blocked."
        )


# --------------------------------------------------
# CSV IMPORT
# --------------------------------------------------

with tab_csv:
    with st.container(border=True):
        section(
            "Get the template",
            "Fill it with your products. Every row needs a title and a "
            "product_url.",
            step=1,
        )
        st.download_button(
            "⬇️  Download CSV template",
            data=csv_template_bytes(),
            file_name="products_to_hunt_template.csv",
            mime="text/csv",
            key="download_csv_template",
        )

    with st.container(border=True):
        section("Upload your file", step=2)
        uploaded_file = st.file_uploader(
            "CSV file",
            type=["csv"],
            key="hunter_csv_upload",
            label_visibility="collapsed",
        )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            with st.expander("Raw file preview (first 20 rows)"):
                st.dataframe(
                    df.head(20),
                    width="stretch",
                    hide_index=True,
                )

            normalized_products = normalize_csv_columns(df)

            if not normalized_products:
                st.warning(
                    "This CSV has no valid products to import."
                )
            else:
                with st.container(border=True):
                    section(
                        "Review and import",
                        f"{len(normalized_products)} valid product rows "
                        "found.",
                        step=3,
                    )

                    render_products(normalized_products, "csv")

                    st.divider()

                    confirm_csv = st.checkbox(
                        "I reviewed this data and want to import it.",
                        key="confirm_csv_import",
                    )

                    if st.button(
                        f"📥  Import {len(normalized_products)} products",
                        type="primary",
                        key="import_csv_button",
                    ):
                        if not confirm_csv:
                            st.warning(
                                "Please tick the confirmation box first."
                            )
                        else:
                            count = save_to_existing_database(
                                normalized_products
                            )
                            st.success(
                                f"{count} product records were sent to "
                                "the database. Check the Product Database "
                                "tab to confirm."
                            )

        except Exception as exc:
            st.error(
                "Could not read, validate or import the CSV: " + str(exc)
            )


# --------------------------------------------------
# PRODUCT DATABASE
# --------------------------------------------------

with tab_db:
    head_col, refresh_col = st.columns([5, 1])
    with head_col:
        section(
            "Your saved products",
            "Everything you have saved from scans and CSV imports.",
        )
    with refresh_col:
        st.button(
            "🔄  Refresh",
            key="refresh_database_products",
            width="stretch",
        )

    try:
        db_products = read_existing_database()
    except Exception as exc:
        db_error = str(exc)

    if db_error:
        st.error("Could not read the database: " + db_error)
        st.caption(
            "Do not reset the database. Check the error above and "
            "verify the database integration."
        )
    elif not db_products:
        st.markdown(
            '<div class="ph-empty"><div class="big">📦</div>'
            "<h3>Your database is empty</h3>"
            "<p>Run a scan or import a CSV, then save products to see "
            "them here.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        stores_count = len({
            host_of(p.get("store_url") or p.get("product_url"))
            for p in db_products
        })
        best_count = sum(
            1 for p in db_products
            if (get_score(p) or 0) >= STRONG_SCORE
            or str(p.get("popularity_status") or "").startswith(
                "Listed on best"
            )
        )
        last_scan = max(
            (str(p.get("scanned_at") or "") for p in db_products),
            default="",
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Products", len(db_products))
        m2.metric("Stores", stores_count)
        m3.metric("Strong signals", best_count)
        m4.metric("Last update", last_scan[:16] if last_scan else "—")

        st.write("")

        filtered_db = filter_products(db_products, "db")
        st.caption(
            f"Showing {len(filtered_db)} of {len(db_products)} products"
        )
        render_products(filtered_db, "db")

        st.download_button(
            "⬇️  Export all products (CSV)",
            data=pd.DataFrame(db_products).to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="existing_products_export.csv",
            mime="text/csv",
            key="export_existing_products",
        )


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="ph-brand">🛍️ Product Hunter</div>'
        '<div class="ph-brand-sub">Competitor research for your '
        "Shopify store</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ph-side-title">Database</div>',
        unsafe_allow_html=True,
    )
    if db_error:
        st.caption("Database unavailable")
    else:
        st.metric("Saved products", len(db_products))

    st.markdown(
        '<div class="ph-side-title">Quick tips</div>'
        '<div class="ph-side-tip">'
        "1. Add store URLs and press <b>Start scan</b>.<br>"
        "2. Filter and review the products.<br>"
        "3. Save the good ones to your database.<br><br>"
        "Before buying stock, open the <b>Meta Ads</b> link on a product "
        "to see if ads are really running.<br><br>"
        "Keep the pause between stores at 5 seconds or more to avoid "
        "rate limits."
        "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown(
    '<div class="ph-footer">Shopify Product Hunter · Never resets your '
    "database · Verify sales, demand and profit independently before "
    "you list a product.</div>",
    unsafe_allow_html=True,
)