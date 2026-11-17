
import streamlit as st
import pandas as pd

from database.db import init_db, get_products
from connectors.competitor_scanner import scan_competitor_store
from database.db import save_products

st.set_page_config(
    page_title="Shopify Product Hunter",
    page_icon="🛍️",
    layout="wide"
)

init_db()

st.title("🛍️ Shopify Product Hunting AI Agent")
st.caption("Competitor research • Product discovery • Market intelligence")

st.sidebar.header("Research Settings")

market = st.sidebar.selectbox(
    "Target Market",
    ["Global", "USA", "UK", "Europe", "Pakistan", "Canada", "Australia"]
)

mode = st.sidebar.selectbox(
    "Research Mode",
    ["Competitor Stores", "My Shopify Store", "Both"]
)

st.sidebar.info(
    "Competitor scanning is available. "
    "Your own Shopify integration will be added next."
)

products = get_products()

col1, col2, col3 = st.columns(3)

col1.metric("Products Discovered", len(products))
col2.metric(
    "Stores Scanned",
    len(set(p["store_url"] for p in products))
)
col3.metric(
    "Product Categories",
    len(set(
        p["product_type"] for p in products
        if p["product_type"]
    ))
)

st.divider()
st.subheader("🔎 Scan a Competitor Store")

store_url = st.text_input(
    "Store URL",
    placeholder="https://example.com"
)

if st.button("Start Product Scan", type="primary"):
    if mode == "My Shopify Store":
        st.warning(
            "Connect your Shopify store in the next development stage."
        )
    elif not store_url.strip():
        st.warning("Please enter a store URL.")
    else:
        try:
            with st.spinner("Scanning public product listings..."):
                found = scan_competitor_store(
                    store_url.strip(),
                    limit=50
                )

                saved = save_products(
                    store_url.strip().rstrip("/"),
                    found
                )

            st.success(
                f"Scan complete: {len(found)} products found "
                f"and {saved} records saved or updated."
            )
            st.rerun()

        except Exception as error:
            st.error(f"Scan failed: {error}")

st.divider()
st.subheader("📦 Discovered Products")

products = get_products()

if products:
    df = pd.DataFrame(products)

    search = st.text_input(
        "Search products",
        placeholder="Search by product name..."
    )

    if search:
        df = df[
            df["title"].str.contains(
                search,
                case=False,
                na=False
            )
        ]

    display_columns = [
        "title",
        "vendor",
        "price_min",
        "currency",
        "product_type",
        "store_url",
        "product_url"
    ]

    available_columns = [
        c for c in display_columns if c in df.columns
    ]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "product_url": st.column_config.LinkColumn(
                "Product Link"
            ),
            "store_url": st.column_config.LinkColumn(
                "Store"
            ),
            "price_min": st.column_config.NumberColumn(
                "Price",
                format="%.2f"
            )
        }
    )

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download CSV Report",
        data=csv,
        file_name="shopify_products.csv",
        mime="text/csv"
    )
else:
    st.info(
        "No products saved yet. Scan a public competitor store "
        "to populate this table."
    )

st.caption(
    f"Selected market: {market} | "
    "Prices may have unknown currency. "
    "No sales or demand estimates are verified yet."
)
