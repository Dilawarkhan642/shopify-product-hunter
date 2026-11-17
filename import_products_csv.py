
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from connectors.competitor_scanner import normalize_store_url
from database.db import init_db, save_products, get_products


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = BASE_DIR / "products_to_hunt.csv"

TEMPLATE_HEADERS = [
    "Title",
    "Handle",
    "Vendor",
    "Type",
    "Variant Price",
    "Currency",
    "Body (HTML)",
    "Image Src",
    "Product URL",
    "Popularity Status",
    "Popularity Evidence",
]


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalized_headers(row):
    return {
        re.sub(r"[\s_\-]+", " ", str(key or "")).strip().lower(): value
        for key, value in row.items()
        if key is not None
    }


def first_value(row, *names):
    for name in names:
        value = clean(row.get(name.lower()))
        if value:
            return value
    return ""


def parse_price(value):
    """Convert common price formats into a number."""
    value = clean(value)
    if not value:
        return None

    value = value.replace(",", "")
    value = re.sub(r"[^\d.\-]", "", value)

    try:
        price = float(value)
        return price if price >= 0 else None
    except ValueError:
        return None


def create_template():
    if DEFAULT_CSV.exists():
        return

    with DEFAULT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=TEMPLATE_HEADERS)
        writer.writeheader()
        writer.writerow({
            "Title": "Example product - replace this row",
            "Handle": "example-product",
            "Vendor": "Example vendor",
            "Type": "Fashion",
            "Variant Price": "2500",
            "Currency": "PKR",
            "Body (HTML)": "Example description",
            "Image Src": "",
            "Product URL": "",
            "Popularity Status": "Unverified",
            "Popularity Evidence": "No verified sales data",
        })

    print(f"\nCSV template created:\n{DEFAULT_CSV}")
    print("\nOpen this file in Excel or Google Sheets.")
    print("Replace the example row with real product data.")
    print("Save it as CSV UTF-8, then run this script again.")


def calculate_research_score(product):
    """
    Preliminary research-readiness score.
    This is not a sales estimate or profit prediction.
    """
    score = 0

    popularity = clean(product.get("popularity_status")).lower()
    if "best-selling" in popularity or "best selling" in popularity:
        score += 40

    if product.get("price_min") is not None:
        score += 15

    if clean(product.get("description")):
        score += 10

    if clean(product.get("image_url")):
        score += 10

    if clean(product.get("product_type")):
        score += 10

    if clean(product.get("vendor")):
        score += 5

    if clean(product.get("product_url")):
        score += 10

    return score


def load_products_from_csv(csv_path, source_store_url):
    grouped = {}

    try:
        file = csv_path.open("r", newline="", encoding="utf-8-sig")
    except OSError as error:
        raise RuntimeError(f"Cannot open CSV file: {error}") from error

    with file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise RuntimeError("CSV file is empty or has no header row.")

        for row_number, raw_row in enumerate(reader, start=2):
            row = normalized_headers(raw_row)

            title = first_value(
                row, "title", "product title", "name"
            )
            handle = first_value(
                row, "handle", "product handle", "slug"
            )
            vendor = first_value(row, "vendor", "brand", "manufacturer")
            product_type = first_value(
                row, "type", "product type", "category", "product category"
            )
            description = first_value(
                row, "body (html)", "body html", "description",
                "product description", "body"
            )
            image_url = first_value(
                row, "image src", "image url", "image",
                "featured image", "image link"
            )
            product_url = first_value(
                row, "product url", "url", "product link",
                "online store url"
            )
            currency = first_value(row, "currency") or "Unknown"

            price_values = []
            for price_column in (
                "variant price", "price", "price min", "sale price"
            ):
                price = parse_price(row.get(price_column))
                if price is not None:
                    price_values.append(price)

            if not title and not handle and not product_url:
                continue

            if not title:
                # Shopify exports can have blank title cells on variant rows.
                key_handle = handle or product_url
                existing = grouped.get(key_handle)
                if existing:
                    if price_values:
                        existing["_prices"].extend(price_values)
                    if not existing.get("image_url") and image_url:
                        existing["image_url"] = image_url
                    continue
                print(
                    f"Skipping row {row_number}: "
                    "product title is missing."
                )
                continue

            key = handle or product_url or title.lower()
            if key not in grouped:
                if not handle:
                    parsed_path = urlparse(product_url).path
                    match = re.search(r"/products/([^/]+)", parsed_path)
                    handle = match.group(1) if match else ""

                if not product_url and handle:
                    product_url = f"{source_store_url}/products/{handle}"

                if product_url and not product_url.startswith(("https://", "http://")):
                    product_url = f"{source_store_url}/products/{handle}"

                grouped[key] = {
                    "product_id": handle or key,
                    "title": title,
                    "vendor": vendor,
                    "product_type": product_type,
                    "price_min": None,
                    "price_max": None,
                    "currency": currency,
                    "description": description,
                    "product_url": product_url,
                    "image_url": image_url,
                    "store_url": source_store_url,
                    "store_type": product_type or "Unclassified",
                    "popularity_status": first_value(
                        row, "popularity status"
                    ) or "Unverified",
                    "popularity_evidence": first_value(
                        row, "popularity evidence"
                    ) or "No verified sales data",
                    "_prices": [],
                }

            product = grouped[key]
            if price_values:
                product["_prices"].extend(price_values)

            # Fill missing details from later variant/image rows.
            for field, value in (
                ("vendor", vendor),
                ("product_type", product_type),
                ("description", description),
                ("image_url", image_url),
                ("product_url", product_url),
            ):
                if not product.get(field) and value:
                    product[field] = value

    products = []

    for product in grouped.values():
        prices = product.pop("_prices", [])
        if prices:
            product["price_min"] = min(prices)
            product["price_max"] = max(prices)

        product["research_score"] = calculate_research_score(product)
        products.append(product)

    return products


def main():
    init_db()

    if not DEFAULT_CSV.exists():
        create_template()
        return

    csv_input = input(
        f"CSV file path (press Enter for {DEFAULT_CSV.name}): "
    ).strip()

    csv_path = Path(csv_input).expanduser() if csv_input else DEFAULT_CSV

    if not csv_path.is_absolute():
        csv_path = BASE_DIR / csv_path

    if not csv_path.is_file():
        print(f"CSV file not found: {csv_path}")
        return

    source_input = input(
        "Source store URL (example https://www.limelight.pk): "
    ).strip()

    try:
        source_store_url = normalize_store_url(source_input)
        products = load_products_from_csv(
            csv_path, source_store_url
        )

        if not products:
            print("No usable products found in the CSV.")
            print("Check that the file contains a Title or Product Title column.")
            return

        saved = save_products(source_store_url, products)

        print("\nPRODUCT HUNTING REPORT")
        print("=" * 60)
        print(f"Products read: {len(products)}")
        print(f"Products saved/updated: {saved}")

        ranked = sorted(
            products,
            key=lambda item: item.get("research_score", 0),
            reverse=True,
        )

        for rank, product in enumerate(ranked, start=1):
            print(f"\n{rank}. {product.get('title', 'Untitled')}")
            print(f"   Research score: {product['research_score']}/100")
            print(f"   Category: {product.get('product_type') or 'Unknown'}")
            print(
                f"   Price range: {product.get('price_min')} - "
                f"{product.get('price_max')} {product.get('currency', '')}"
            )
            print(
                f"   Popularity: "
                f"{product.get('popularity_status', 'Unverified')}"
            )
            print(
                f"   Evidence: "
                f"{product.get('popularity_evidence', 'None')}"
            )
            print(f"   URL: {product.get('product_url') or 'Not provided'}")

        print("\nExisting database products:", len(get_products()))
        print(
            "\nImportant: Research score measures available evidence and "
            "product-data completeness. It does not prove sales, demand, "
            "or profitability."
        )

    except (ValueError, RuntimeError) as error:
        print("\nImport stopped:", error)
    except Exception as error:
        print("\nUnexpected error:", error)


if __name__ == "__main__":
    main()
