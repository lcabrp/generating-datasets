"""
Configuration for the retail dataset generator.

The defaults are intentionally modest enough for a laptop, but the CLI in
main.py can override them for larger demo datasets.
"""

from pathlib import Path

DATA_DIR = Path("data")
CUSTOMERS_FILE = "customers.csv"
INVENTORY_FILE = "inventory.csv"
TRANSACTIONS_FILE = "transactions.csv"
DATABASE_FILE_NAME = "retail.db"

CUSTOMERS_CSV = DATA_DIR / CUSTOMERS_FILE
INVENTORY_CSV = DATA_DIR / INVENTORY_FILE
TRANSACTIONS_CSV = DATA_DIR / TRANSACTIONS_FILE
DATABASE_FILE = DATA_DIR / DATABASE_FILE_NAME

DEFAULT_CUSTOMERS = 1_000
DEFAULT_INVENTORY = 500
DEFAULT_TRANSACTIONS = 250_000
MAX_TRANSACTIONS = 5_000_000
DEFAULT_SEED = 42

RETAIL_CATEGORIES = [
    "Electronics",
    "Books",
    "Clothing",
    "Home",
    "Beauty",
    "Sports",
    "Toys",
    "Automotive",
    "Grocery",
    "Office",
]

ORDER_STATUSES = ["delivered", "shipped", "processing", "canceled", "returned"]
PAYMENT_METHODS = ["credit_card", "paypal", "stripe", "bank_transfer"]

CUSTOMERS_COLUMNS = [
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "address",
    "city",
    "state",
    "zip_code",
    "country",
    "date_of_birth",
    "gender",
    "signup_date",
]

INVENTORY_COLUMNS = [
    "product_id",
    "sku",
    "name",
    "category",
    "brand",
    "price",
    "weight",
    "stock_qty",
    "rating",
    "description",
    "created_at",
]

TRANSACTIONS_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "shipping_address",
    "status",
    "total_amount",
    "shipping_cost",
    "payment_method",
    "coupon_code",
    "items",
]
