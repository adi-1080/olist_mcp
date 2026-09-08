"""
Olist Dataset Loader & SQLite Database Generator.
Reads raw CSV files from data/ directory (or generates structured realistic Olist dataset if CSVs are missing)
and loads them into SQLite database with optimized indexes.
"""

import os
import sqlite3
import zipfile
import subprocess
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "olist.db"

CSV_TABLE_MAPPING = {
    "olist_orders_dataset.csv": "olist_orders",
    "olist_order_items_dataset.csv": "olist_order_items",
    "olist_order_payments_dataset.csv": "olist_order_payments",
    "olist_order_reviews_dataset.csv": "olist_order_reviews",
    "olist_products_dataset.csv": "olist_products",
    "olist_sellers_dataset.csv": "olist_sellers",
    "olist_order_customer_dataset.csv": "olist_customers",
    "olist_geolocation_dataset.csv": "olist_geolocation",
    "product_category_name_translation.csv": "product_category_name_translation",
}

def ensure_data_directory():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_kaggle_dataset():
    """Try downloading the Olist dataset from Kaggle if missing."""
    zip_path = DATA_DIR / "brazilian-ecommerce.zip"
    if any(DATA_DIR.glob("*.csv")):
        logger.info("Found existing CSV files in data/.")
        return True

    logger.info("Attempting to download Olist dataset via kaggle CLI...")
    try:
        res = subprocess.run(
            ["kaggle", "datasets", "download", "-d", "olistbr/brazilian-ecommerce", "-p", str(DATA_DIR)],
            capture_output=True,
            text=True
        )
        if res.returncode == 0 and zip_path.exists():
            logger.info("Dataset downloaded successfully. Unzipping...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(DATA_DIR)
            return True
        else:
            logger.warning(f"Kaggle download failed or kaggle CLI not configured: {res.stderr}")
    except Exception as e:
        logger.warning(f"Kaggle download exception: {e}")

    return False

def generate_sample_olist_data():
    """Generates realistic synthetic Olist dataset (2016-2018) if CSVs are missing."""
    logger.info("Generating realistic Olist sample dataset...")
    ensure_data_directory()

    np.random.seed(42)
    num_orders = 5000
    num_customers = 3500
    num_sellers = 300
    num_products = 400

    # 1. Translation
    categories = [
        ("cama_mesa_banho", "bed_bath_table"),
        ("beleza_saude", "health_beauty"),
        ("esporte_lazer", "sports_leisure"),
        ("informatica_acessorios", "computers_accessories"),
        ("moveis_decoracao", "furniture_decor"),
        ("utilidades_domesticas", "housewares"),
        ("relogios_presentes", "watches_gifts"),
        ("telefonia", "telephony"),
        ("automotivo", "automotive"),
        ("eletronicos", "electronics"),
    ]
    df_trans = pd.DataFrame(categories, columns=["product_category_name", "product_category_name_english"])
    df_trans.to_csv(DATA_DIR / "product_category_name_translation.csv", index=False)

    # 2. Customers
    states = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "DF", "CE"]
    cust_ids = [f"cust_{i:05d}" for i in range(num_customers)]
    df_cust = pd.DataFrame({
        "customer_id": cust_ids,
        "customer_unique_id": [f"unique_{i:05d}" for i in range(num_customers)],
        "customer_zip_code_prefix": np.random.randint(1000, 99999, size=num_customers),
        "customer_city": np.random.choice(["sao paulo", "rio de janeiro", "belo horizonte", "curitiba", "porto alegre"], size=num_customers),
        "customer_state": np.random.choice(states, size=num_customers, p=[0.4, 0.15, 0.12, 0.08, 0.07, 0.05, 0.04, 0.03, 0.03, 0.03])
    })
    df_cust.to_csv(DATA_DIR / "olist_order_customer_dataset.csv", index=False)

    # 3. Sellers
    seller_ids = [f"seller_{i:04d}" for i in range(num_sellers)]
    df_sellers = pd.DataFrame({
        "seller_id": seller_ids,
        "seller_zip_code_prefix": np.random.randint(1000, 99999, size=num_sellers),
        "seller_city": np.random.choice(["sao paulo", "rio de janeiro", "campinas", "curitiba"], size=num_sellers),
        "seller_state": np.random.choice(states[:5], size=num_sellers, p=[0.5, 0.2, 0.15, 0.1, 0.05])
    })
    df_sellers.to_csv(DATA_DIR / "olist_sellers_dataset.csv", index=False)

    # 4. Products
    product_ids = [f"prod_{i:04d}" for i in range(num_products)]
    prod_cats = [c[0] for c in categories]
    df_products = pd.DataFrame({
        "product_id": product_ids,
        "product_category_name": np.random.choice(prod_cats, size=num_products),
        "product_name_lenght": np.random.randint(20, 60, size=num_products),
        "product_description_lenght": np.random.randint(100, 1000, size=num_products),
        "product_photos_qty": np.random.randint(1, 6, size=num_products),
        "product_weight_g": np.random.randint(100, 5000, size=num_products),
        "product_length_cm": np.random.randint(10, 50, size=num_products),
        "product_height_cm": np.random.randint(5, 40, size=num_products),
        "product_width_cm": np.random.randint(10, 40, size=num_products)
    })
    df_products.to_csv(DATA_DIR / "olist_products_dataset.csv", index=False)

    # 5. Orders (2016-2018)
    order_ids = [f"order_{i:06d}" for i in range(num_orders)]
    start_date = pd.Timestamp("2016-09-01")
    end_date = pd.Timestamp("2018-09-30")
    random_dates = start_date + (end_date - start_date) * np.random.rand(num_orders)
    
    order_statuses = np.random.choice(["delivered", "shipped", "canceled"], size=num_orders, p=[0.96, 0.03, 0.01])
    assigned_custs = np.random.choice(cust_ids, size=num_orders)

    purchase_ts = pd.to_datetime(random_dates)
    approved_ts = purchase_ts + pd.to_timedelta(np.random.randint(1, 24, size=num_orders), unit='h')
    delivered_carrier_ts = approved_ts + pd.to_timedelta(np.random.randint(12, 72, size=num_orders), unit='h')
    
    # Delivery delay calculation logic: 85% delivered on time, 15% delayed
    delivery_days = np.random.randint(3, 20, size=num_orders)
    estimated_days = delivery_days + np.random.choice([-2, -1, 0, 1, 3, 5], size=num_orders, p=[0.1, 0.15, 0.5, 0.15, 0.07, 0.03])
    
    delivered_cust_ts = purchase_ts + pd.to_timedelta(delivery_days, unit='D')
    estimated_ts = purchase_ts + pd.to_timedelta(estimated_days, unit='D')

    df_orders = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": assigned_custs,
        "order_status": order_statuses,
        "order_purchase_timestamp": purchase_ts.strftime('%Y-%m-%d %H:%M:%S'),
        "order_approved_at": approved_ts.strftime('%Y-%m-%d %H:%M:%S'),
        "order_delivered_carrier_date": delivered_carrier_ts.strftime('%Y-%m-%d %H:%M:%S'),
        "order_delivered_customer_date": delivered_cust_ts.strftime('%Y-%m-%d %H:%M:%S'),
        "order_estimated_delivery_date": estimated_ts.strftime('%Y-%m-%d %H:%M:%S')
    })
    df_orders.to_csv(DATA_DIR / "olist_orders_dataset.csv", index=False)

    # 6. Order Items
    items_list = []
    for order_id in order_ids:
        n_items = np.random.choice([1, 2, 3], p=[0.8, 0.15, 0.05])
        for item_idx in range(1, n_items + 1):
            items_list.append({
                "order_id": order_id,
                "order_item_id": item_idx,
                "product_id": np.random.choice(product_ids),
                "seller_id": np.random.choice(seller_ids),
                "shipping_limit_date": (pd.Timestamp("2018-01-01") + pd.Timedelta(days=int(np.random.randint(0, 300)))).strftime('%Y-%m-%d %H:%M:%S'),
                "price": round(float(np.random.exponential(scale=80.0) + 10.0), 2),
                "freight_value": round(float(np.random.uniform(5.0, 35.0)), 2)
            })
    df_items = pd.DataFrame(items_list)
    df_items.to_csv(DATA_DIR / "olist_order_items_dataset.csv", index=False)

    # 7. Payments
    pay_types = ["credit_card", "boleto", "voucher", "debit_card"]
    pay_probs = [0.74, 0.19, 0.05, 0.02]
    pay_list = []
    for order_id in order_ids:
        # Sum order items
        order_total = df_items[df_items["order_id"] == order_id][["price", "freight_value"]].sum().sum()
        ptype = np.random.choice(pay_types, p=pay_probs)
        installments = np.random.randint(1, 10) if ptype == "credit_card" else 1
        pay_list.append({
            "order_id": order_id,
            "payment_sequential": 1,
            "payment_type": ptype,
            "payment_installments": installments,
            "payment_value": round(float(order_total), 2)
        })
    df_pay = pd.DataFrame(pay_list)
    df_pay.to_csv(DATA_DIR / "olist_order_payments_dataset.csv", index=False)

    # 8. Reviews
    review_list = []
    for i, order_id in enumerate(order_ids):
        # Correlate review score slightly with delivery speed
        score = int(np.random.choice([1, 2, 3, 4, 5], p=[0.1, 0.05, 0.1, 0.25, 0.5]))
        review_list.append({
            "review_id": f"rev_{i:06d}",
            "order_id": order_id,
            "review_score": score,
            "review_comment_title": "Good" if score >= 4 else "Bad",
            "review_comment_message": "Satisfied" if score >= 4 else "Delayed delivery",
            "review_creation_date": (pd.Timestamp("2017-06-01") + pd.Timedelta(days=int(np.random.randint(0, 400)))).strftime('%Y-%m-%d %H:%M:%S'),
            "review_answer_timestamp": (pd.Timestamp("2017-06-02") + pd.Timedelta(days=int(np.random.randint(0, 400)))).strftime('%Y-%m-%d %H:%M:%S')
        })
    df_reviews = pd.DataFrame(review_list)
    df_reviews.to_csv(DATA_DIR / "olist_order_reviews_dataset.csv", index=False)

    # 9. Geolocation
    df_geo = pd.DataFrame({
        "geolocation_zip_code_prefix": np.random.randint(1000, 99999, size=1000),
        "geolocation_lat": np.random.uniform(-30.0, -5.0, size=1000),
        "geolocation_lng": np.random.uniform(-60.0, -35.0, size=1000),
        "geolocation_city": np.random.choice(["sao paulo", "rio de janeiro", "curitiba"], size=1000),
        "geolocation_state": np.random.choice(states, size=1000)
    })
    df_geo.to_csv(DATA_DIR / "olist_geolocation_dataset.csv", index=False)

    logger.info("Sample Olist dataset generated successfully.")

def build_sqlite_database():
    """Loads all CSV files from data/ into data/olist.db SQLite database."""
    ensure_data_directory()

    # Check if download or generation is needed
    has_csvs = any(DATA_DIR.glob("*.csv"))
    if not has_csvs:
        downloaded = download_kaggle_dataset()
        if not downloaded:
            generate_sample_olist_data()

    logger.info(f"Building SQLite database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)

    for csv_file, table_name in CSV_TABLE_MAPPING.items():
        file_path = DATA_DIR / csv_file
        if file_path.exists():
            logger.info(f"Loading {csv_file} -> table '{table_name}'...")
            # Load in chunks if file is large
            chunk_list = []
            for chunk in pd.read_csv(file_path, chunksize=50000, low_memory=False):
                chunk_list.append(chunk)
            df = pd.concat(chunk_list, ignore_index=True)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        else:
            logger.warning(f"File {csv_file} not found. Skipping table '{table_name}'.")

    # Create Indexes
    logger.info("Creating indexes for fast join performance...")
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_orders_order_id ON olist_orders (order_id);
        CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON olist_orders (customer_id);
        CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts ON olist_orders (order_purchase_timestamp);
        
        CREATE INDEX IF NOT EXISTS idx_items_order_id ON olist_order_items (order_id);
        CREATE INDEX IF NOT EXISTS idx_items_product_id ON olist_order_items (product_id);
        CREATE INDEX IF NOT EXISTS idx_items_seller_id ON olist_order_items (seller_id);
        
        CREATE INDEX IF NOT EXISTS idx_payments_order_id ON olist_order_payments (order_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_order_id ON olist_order_reviews (order_id);
        
        CREATE INDEX IF NOT EXISTS idx_products_prod_id ON olist_products (product_id);
        CREATE INDEX IF NOT EXISTS idx_products_cat_name ON olist_products (product_category_name);
        
        CREATE INDEX IF NOT EXISTS idx_sellers_seller_id ON olist_sellers (seller_id);
        CREATE INDEX IF NOT EXISTS idx_customers_cust_id ON olist_customers (customer_id);
        
        CREATE INDEX IF NOT EXISTS idx_trans_pt ON product_category_name_translation (product_category_name);
        CREATE INDEX IF NOT EXISTS idx_trans_en ON product_category_name_translation (product_category_name_english);
    """)
    conn.commit()
    conn.close()
    logger.info("SQLite database built successfully!")

def get_db_connection():
    """Returns a connection to the SQLite database."""
    if not DB_PATH.exists():
        build_sqlite_database()
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    build_sqlite_database()
