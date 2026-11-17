import ipaddress
import re
import time
from html import unescape
from urllib.parse import urlparse

import requests


# A normal browser-style identity. Many Shopify stores sit behind a CDN that
# rate-limits or throttles clients that identify as bots or send bare headers.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# One shared session: reuses the connection and keeps any cookies the store
# sets, which looks like a single normal visitor rather than a fresh client
# on every request.
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

MAX_PRODUCTS_PER_SCAN = 20
REQUEST_TIMEOUT = 20

# Pause between the requests made to the same store
# (product list first, then the homepage for the ad-pixel check).
BEST_SELLER_DELAY = 2.0

# On HTTP 429 we honor Retry-After and retry ONCE, but only if the store asks
# us to wait no longer than this many seconds. Longer waits fail fast so the
# UI never hangs.
DEFAULT_RETRY_WAIT = 60
MAX_RETRY_WAIT = 90

# Winning-score thresholds (0-100).
STRONG_SCORE = 65
PROMISING_SCORE = 40


class RateLimitError(RuntimeError):
    """Raised when a store answers HTTP 429. Still a RuntimeError, so
    existing `except RuntimeError` code keeps working."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


def normalize_store_url(store_url: str) -> str:
    """Validate and normalize a public HTTPS store URL."""

    if not isinstance(store_url, str) or not store_url.strip():
        raise ValueError("Please enter a store URL.")

    store_url = store_url.strip()

    if "://" not in store_url:
        store_url = "https://" + store_url

    try:
        parsed = urlparse(store_url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("Please enter a valid store URL.") from error

    if parsed.scheme.lower() != "https":
        raise ValueError("Please use an HTTPS store URL.")

    if not host:
        raise ValueError("Please enter a valid store URL.")

    if parsed.username or parsed.password:
        raise ValueError("Store URLs must not contain credentials.")

    if port not in (None, 443):
        raise ValueError("Custom ports are not supported.")

    host = host.rstrip(".").lower()

    if (
        host == "localhost"
        or host.endswith(
            (
                ".localhost",
                ".local",
                ".internal",
                ".test",
                ".invalid",
                ".example",
            )
        )
        or "." not in host
    ):
        raise ValueError("Please enter a public store domain.")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        hostname_pattern = (
            r"(?=.{1,253}$)"
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
            r"[a-z]{2,63}"
        )
        if not re.fullmatch(hostname_pattern, host):
            raise ValueError("Please enter a valid public store domain.")
    else:
        if not address.is_global:
            raise ValueError("Please enter a public store domain.")

    return f"https://{host}"


def _parse_retry_after(value):
    """Return Retry-After as seconds, or None if missing/not a number."""

    if not value:
        return None
    try:
        return max(0.0, float(value.strip()))
    except ValueError:
        # Could be an HTTP date; treat as unknown and use the default.
        return None


def safe_get(url, params=None, timeout=REQUEST_TIMEOUT, max_retries=0):
    """Make a request; never follow redirects automatically.

    On HTTP 429, wait for Retry-After (capped at MAX_RETRY_WAIT) and retry up
    to `max_retries` times. With max_retries=0 (the default) behavior is the
    same as before: stop immediately and raise RateLimitError.
    """

    attempt = 0

    while True:
        try:
            response = SESSION.get(
                url,
                params=params,
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.RequestException as error:
            raise RuntimeError(
                f"Could not fetch public store data: {error}"
            ) from error

        if response.status_code != 429:
            break

        retry_after_header = response.headers.get("Retry-After")
        response.close()

        wait = _parse_retry_after(retry_after_header)
        if wait is None:
            wait = DEFAULT_RETRY_WAIT

        if attempt < max_retries and wait <= MAX_RETRY_WAIT:
            time.sleep(wait + 1)
            attempt += 1
            continue

        message = (
            "Store returned HTTP 429 (rate limited). "
            "The scan stopped safely."
        )
        if retry_after_header:
            message += f" Retry-After: {retry_after_header}s."
        message += " Wait a few minutes before scanning this store again."

        raise RateLimitError(message, retry_after_header)

    if 300 <= response.status_code < 400:
        location = response.headers.get("Location", "")
        response.close()
        raise RuntimeError(
            "Store redirected this request. Use its final HTTPS URL. "
            f"Redirect destination: {location or 'not provided'}"
        )

    try:
        response.raise_for_status()
    except requests.RequestException as error:
        status = response.status_code
        response.close()
        raise RuntimeError(
            f"Store request failed: HTTP {status}"
        ) from error

    return response


def get_store_type(products):
    """Estimate a broad store category from public product information."""

    text = " ".join(
        f"{product.get('title', '')} "
        f"{product.get('product_type', '')} "
        f"{product.get('description', '')}"
        for product in products
    ).lower()

    categories = {
        "Electronics": [
            "electronic", "charger", "headphone", "speaker",
            "phone", "wireless", "gadget", "laptop",
        ],
        "Home & Living": [
            "lamp", "decor", "furniture", "organizer",
            "kitchen", "humidifier", "home", "lighting",
        ],
        "Fashion & Jewelry": [
            "jewelry", "jewellery", "necklace", "earring",
            "bracelet", "ring", "clothing", "fashion",
            "dress", "shirt", "abaya", "kurta", "lawn",
        ],
        "Beauty & Personal Care": [
            "beauty", "skincare", "skin care", "cosmetic",
            "serum", "makeup", "hair care", "shampoo",
        ],
        "Sports & Outdoors": [
            "fitness", "sport", "camping", "outdoor",
            "exercise", "yoga",
        ],
        "Pet Supplies": ["pet", "dog", "cat", "animal"],
        "Food & Grocery": [
            "grocery", "snack", "coffee", "tea", "food",
            "spice", "chocolate",
        ],
    }

    counts = {
        category: sum(text.count(word) for word in keywords)
        for category, keywords in categories.items()
    }

    best_category = max(counts, key=counts.get)
    return best_category if counts[best_category] else "Unclassified"


# --------------------------------------------------
# WINNING-PRODUCT SIGNALS
# --------------------------------------------------

# Tracking pixels in a store's homepage HTML. A store that installs ad pixels
# is very likely running paid ads on that platform. Absence proves nothing:
# some stores load pixels in ways that do not show up in the page source.
AD_PIXEL_PATTERNS = {
    "Meta Pixel": [
        r"connect\.facebook\.net",
        r"\bfbq\s*\(",
        r"facebook\.com/tr\?",
    ],
    "TikTok Pixel": [
        r"analytics\.tiktok\.com",
        r"\bttq\.(?:load|track|page)\b",
    ],
    "Google Ads": [
        r"googleadservices\.com",
        r"google_conversion",
        r"""gtag\(\s*['"]config['"]\s*,\s*['"]AW-""",
    ],
    "Snapchat Pixel": [
        r"sc-static\.net/scevent",
        r"\bsnaptr\s*\(",
    ],
    "Pinterest Tag": [
        r"\bpintrk\s*\(",
        r"s\.pinimg\.com/ct/core\.js",
    ],
}

AD_PIXEL_POINTS = {
    "Meta Pixel": 12,
    "TikTok Pixel": 8,
    "Google Ads": 5,
    "Snapchat Pixel": 2,
    "Pinterest Tag": 2,
}
AD_POINTS_CAP = 25


def detect_ad_signals(store_url):
    """Return the ad pixels found on the store homepage.

    Returns a list (empty if none were found) or None if the homepage could
    not be read. This never raises, so it cannot break a scan.
    """

    try:
        response = safe_get(f"{store_url}/", timeout=15, max_retries=0)
    except RuntimeError:
        return None

    try:
        page_html = response.text
    finally:
        response.close()

    found = []
    for name, patterns in AD_PIXEL_PATTERNS.items():
        if any(re.search(p, page_html, flags=re.IGNORECASE) for p in patterns):
            found.append(name)

    return found


def fetch_best_selling_products(store_url, limit):
    """Ask the store for its products sorted by best-selling.

    Returns the raw product list, or None if the store does not offer it.
    A rate limit is re-raised so the caller stops instead of hammering the
    store with a second request.
    """

    try:
        response = safe_get(
            f"{store_url}/collections/all/products.json",
            params={"sort_by": "best-selling", "limit": limit},
            timeout=REQUEST_TIMEOUT,
            max_retries=1,
        )
    except RateLimitError:
        raise
    except RuntimeError:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None
    finally:
        response.close()

    if not isinstance(payload, dict):
        return None

    products = payload.get("products")
    if not isinstance(products, list) or not products:
        return None

    return products


def _discount_percent(variants):
    """Largest 'compare at' discount across variants, in percent."""

    best = 0.0

    for variant in variants:
        if not isinstance(variant, dict):
            continue

        try:
            price = float(variant.get("price"))
            compare = float(variant.get("compare_at_price"))
        except (TypeError, ValueError):
            continue

        if compare > price > 0:
            best = max(best, (compare - price) / compare * 100)

    return round(best)


def score_product(rank, ranked, store_ads, discount_pct, in_stock,
                  variant_count):
    """Estimate how likely a product is a 'winner' from public signals.

    Returns (score 0-100, label, list of reasons). This is an estimate. It
    is NOT real sales data.
    """

    score = 0
    reasons = []

    if ranked and rank is not None:
        if rank <= 3:
            score += 40
        elif rank <= 10:
            score += 30
        else:
            score += 20
        reasons.append(f"#{rank} on the store's best-selling list")

    if store_ads:
        ad_points = min(
            AD_POINTS_CAP,
            sum(AD_PIXEL_POINTS.get(name, 0) for name in store_ads),
        )
        score += ad_points
        reasons.append("Store ad pixels: " + ", ".join(store_ads))

    if discount_pct >= 30:
        score += 12
    elif discount_pct >= 15:
        score += 8
    elif discount_pct > 0:
        score += 4

    if discount_pct > 0:
        reasons.append(f"{discount_pct}% off compare-at price")

    if in_stock:
        score += 8
    else:
        reasons.append("Sold out right now")

    if variant_count >= 4:
        score += 5
        reasons.append(f"{variant_count} variants")

    score = max(0, min(100, score))

    if score >= STRONG_SCORE:
        label = "Strong signal"
    elif score >= PROMISING_SCORE:
        label = "Promising"
    else:
        label = "Weak signal"

    return score, label, reasons


def get_public_best_sellers(store_url):
    """Read a public best-selling page if available (HTML fallback)."""

    endpoint = f"{store_url}/collections/all"

    # No retries here: this request is optional, so fail fast.
    response = safe_get(
        endpoint,
        params={"sort_by": "best-selling"},
        timeout=15,
        max_retries=0,
    )

    try:
        page_html = response.text
    finally:
        response.close()

    handles = re.findall(
        r"""(?:https?://[^/"'\s]+)?/products/([^"'?#/\s]+)""",
        page_html,
        flags=re.IGNORECASE,
    )

    return list(dict.fromkeys(handles))


def _fetch_default_products(store_url, actual_limit):
    """Fallback: the store's normal product list (no best-selling order)."""

    endpoint = f"{store_url}/products.json"

    try:
        response = safe_get(
            endpoint,
            params={"limit": actual_limit},
            timeout=REQUEST_TIMEOUT,
            max_retries=1,
        )
    except RuntimeError as error:
        if "HTTP 404" in str(error):
            raise RuntimeError(
                "Store request failed: HTTP 404. This site is probably "
                "not a Shopify store, or it has disabled its public "
                "/products.json endpoint."
            ) from error
        raise

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError(
            "The store did not return valid JSON product data. "
            "Its public product endpoint may be unavailable."
        ) from error
    finally:
        response.close()

    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected product data format.")

    raw_products = payload.get("products", [])
    if not isinstance(raw_products, list):
        raise RuntimeError("Unexpected product data format.")

    return raw_products


def scan_competitor_store(
    store_url: str,
    limit: int = 10,
    include_best_sellers: bool = True,
    check_ads: bool = True,
):
    """
    Read publicly accessible Shopify product JSON and score each product.

    include_best_sellers: ask the store for its best-selling order (one
        request). If the store does not offer it, the normal product list
        is used instead and no rank is given.
    check_ads: read the store homepage once and look for ad pixels.

    The score is an ESTIMATE from public signals. It is not real sales data.
    """

    store_url = normalize_store_url(store_url)

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Limit must be an integer.")

    if not 1 <= limit <= 250:
        raise ValueError("Limit must be between 1 and 250.")

    actual_limit = min(limit, MAX_PRODUCTS_PER_SCAN)

    raw_products = None
    ranked = False

    if include_best_sellers:
        raw_products = fetch_best_selling_products(store_url, actual_limit)
        ranked = raw_products is not None

    if raw_products is None:
        raw_products = _fetch_default_products(store_url, actual_limit)

    products = []

    for item in raw_products[:actual_limit]:
        if not isinstance(item, dict):
            continue

        handle = str(item.get("handle") or "").strip()
        if not handle:
            continue

        variants = item.get("variants") or []
        images = item.get("images") or []

        if not isinstance(variants, list):
            variants = []
        if not isinstance(images, list):
            images = []

        all_prices = []
        available_prices = []

        for variant in variants:
            if not isinstance(variant, dict):
                continue

            try:
                price = float(variant.get("price"))
            except (TypeError, ValueError):
                continue

            if price < 0:
                continue

            all_prices.append(price)

            if variant.get("available") is True:
                available_prices.append(price)

        prices = available_prices or all_prices

        image_url = ""
        if images and isinstance(images[0], dict):
            image_url = str(images[0].get("src") or "")

        title = unescape(str(item.get("title") or "")).strip()

        products.append({
            "product_id": item.get("id"),
            "title": title or "Untitled product",
            "vendor": str(item.get("vendor") or ""),
            "product_type": str(item.get("product_type") or ""),
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "currency": "Unknown",
            "description": unescape(str(item.get("body_html") or "")),
            "product_url": f"{store_url}/products/{handle}",
            "image_url": image_url,
            "store_url": store_url,
            "store_type": "Unclassified",
            "popularity_status": "Unverified",
            "popularity_evidence": "Actual sales not verified",
            # Internal signals used for scoring below.
            "_variants": variants,
            "_in_stock": bool(available_prices),
            "_rank": len(products) + 1,
        })

    if not products:
        return []

    store_type = get_store_type(products)

    store_ads = None
    if check_ads:
        # Be polite: pause before the second request to the same store.
        time.sleep(BEST_SELLER_DELAY)
        store_ads = detect_ad_signals(store_url)

    for product in products:
        variants = product.pop("_variants")
        in_stock = product.pop("_in_stock")
        rank = product.pop("_rank")

        discount = _discount_percent(variants)

        score, label, reasons = score_product(
            rank=rank,
            ranked=ranked,
            store_ads=store_ads or [],
            discount_pct=discount,
            in_stock=in_stock,
            variant_count=len(variants),
        )

        if check_ads and store_ads is None:
            reasons.append("Ad pixel check failed (homepage not readable)")
        elif check_ads and not store_ads:
            reasons.append("No ad pixels found on homepage")

        product["store_type"] = store_type
        product["winning_score"] = score
        product["signal_label"] = label
        product["ad_signals"] = ", ".join(store_ads or [])
        product["best_rank"] = rank if ranked else None
        product["discount_pct"] = discount
        product["popularity_status"] = f"{label} (score {score})"
        product["popularity_evidence"] = (
            "; ".join(reasons)
            + ". Estimate from public signals; actual sales not verified."
        )

    return products