import sqlite3
from contextlib import contextmanager
from pathlib import Path
 
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "product_hunter.db"
 
 
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
@contextmanager
def db_session():
    """Commit on success, roll back on error, and always close."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
 
 
def init_db():
    with db_session() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_url TEXT NOT NULL,
                product_id TEXT,
                title TEXT NOT NULL,
                vendor TEXT,
                product_type TEXT,
                price_min REAL,
                price_max REAL,
                currency TEXT DEFAULT 'Unknown',
                description TEXT,
                product_url TEXT NOT NULL,
                image_url TEXT,
                store_type TEXT DEFAULT 'Unclassified',
                popularity_status TEXT DEFAULT 'Unverified',
                popularity_evidence TEXT DEFAULT 'No sales data verified',
                scanned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(store_url, product_url)
            )
        """)
 
        # Safely add new columns to an existing database.
        # Existing products and rows are preserved.
        existing_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }
 
        new_columns = {
            "store_type": "TEXT DEFAULT 'Unclassified'",
            "popularity_status": "TEXT DEFAULT 'Unverified'",
            "popularity_evidence": "TEXT DEFAULT 'No sales data verified'",
        }
 
        for column, definition in new_columns.items():
            if column not in existing_columns:
                conn.execute(
                    f"ALTER TABLE products ADD COLUMN {column} {definition}"
                )
 
 
def save_products(store_url, products):
    init_db()
    saved = 0
 
    # Prefer the normalized URL returned by the scanner.
    if products:
        store_url = products[0].get("store_url") or store_url
 
    with db_session() as conn:
        for product in products:
            conn.execute("""
                INSERT INTO products (
                    store_url,
                    product_id,
                    title,
                    vendor,
                    product_type,
                    price_min,
                    price_max,
                    currency,
                    description,
                    product_url,
                    image_url,
                    store_type,
                    popularity_status,
                    popularity_evidence,
                    scanned_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP)
                ON CONFLICT(store_url, product_url)
                DO UPDATE SET
                    product_id = excluded.product_id,
                    title = excluded.title,
                    vendor = excluded.vendor,
                    product_type = excluded.product_type,
                    price_min = excluded.price_min,
                    price_max = excluded.price_max,
                    currency = excluded.currency,
                    description = excluded.description,
                    image_url = excluded.image_url,
                    store_type = excluded.store_type,
                    -- A re-scan without the best-seller check must not
                    -- wipe a status that an earlier scan found.
                    popularity_status = CASE
                        WHEN excluded.popularity_status = 'Unverified'
                        THEN products.popularity_status
                        ELSE excluded.popularity_status
                    END,
                    popularity_evidence = CASE
                        WHEN excluded.popularity_status = 'Unverified'
                        THEN products.popularity_evidence
                        ELSE excluded.popularity_evidence
                    END,
                    scanned_at = CURRENT_TIMESTAMP
            """, (
                store_url,
                str(product.get("product_id") or ""),
                product.get("title", ""),
                product.get("vendor", ""),
                product.get("product_type", ""),
                product.get("price_min"),
                product.get("price_max"),
                product.get("currency", "Unknown"),
                product.get("description", ""),
                product.get("product_url", ""),
                product.get("image_url", ""),
                product.get("store_type", "Unclassified"),
                product.get("popularity_status", "Unverified"),
                product.get(
                    "popularity_evidence",
                    "No sales data verified"
                ),
            ))
            saved += 1
 
    return saved
 
 
def get_products():
    init_db()
 
    with db_session() as conn:
        rows = conn.execute("""
            SELECT *
            FROM products
            ORDER BY scanned_at DESC, title ASC
        """).fetchall()
 
        return [dict(row) for row in rows]
 