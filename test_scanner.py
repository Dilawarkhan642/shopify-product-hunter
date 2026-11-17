
from connectors.competitor_scanner import scan_competitor_store
from database.db import save_products, get_products, init_db


def main():
    init_db()

    store_url = input(
        "Enter a public competitor store URL: "
    ).strip().rstrip("/")

    if not store_url:
        print("Please enter a store URL.")
        return

    try:
        print("\nStarting product scan...")
        print("The scanner respects the store's request limits.")

        products = scan_competitor_store(store_url, limit=10)

        print(f"\nProducts found: {len(products)}")

        if not products:
            print("No public products were returned.")
        else:
            saved = save_products(store_url, products)
            print(f"Products saved/updated: {saved}")

            print("\nPRODUCT RESEARCH REPORT")
            print("=" * 60)

            for index, product in enumerate(products, start=1):
                print(f"\n{index}. {product.get('title', 'Untitled')}")
                print("-" * 40)
                print("Store:", product.get("store_url", store_url))
                print("Category:", product.get("store_type", "Unclassified"))
                print("Vendor:", product.get("vendor") or "Unknown")
                print("Price min:", product.get("price_min"))
                print("Price max:", product.get("price_max"))
                print(
                    "Popularity:",
                    product.get("popularity_status", "Unverified"),
                )
                print(
                    "Evidence:",
                    product.get(
                        "popularity_evidence",
                        "No verified sales data",
                    ),
                )
                print("Product URL:", product.get("product_url", ""))

            print("\nNote: Public ranking evidence does not confirm actual sales.")

        all_products = get_products()
        print(
            f"\nTotal unique products in database: {len(all_products)}"
        )

    except KeyboardInterrupt:
        print("\nScan cancelled by user.")

    except Exception as error:
        message = str(error)
        print("\nSCAN STATUS: STOPPED")
        print("Reason:", message)

        if "429" in message or "rate limit" in message.lower():
            print(
                "\nThe store is limiting requests. Respect its Retry-After "
                "instruction and do not keep retrying."
            )
            print("No new products were saved by this failed scan.")
        else:
            print(
                "\nCheck the URL and error message. "
                "Previously saved database records have not been deleted."
            )


if __name__ == "__main__":
    main()
