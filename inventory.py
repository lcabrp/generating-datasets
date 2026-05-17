"""Generate the inventory/products CSV."""

import csv
import random
from pathlib import Path

from faker import Faker

from config import (
    DEFAULT_INVENTORY,
    INVENTORY_COLUMNS,
    INVENTORY_CSV,
    RETAIL_CATEGORIES,
)
from utils import random_price, random_rating, random_stock_qty, random_weight

fake = Faker()


def build_product() -> dict:
    category = random.choice(RETAIL_CATEGORIES)
    product_id = fake.uuid4()
    return {
        "product_id": product_id,
        "sku": fake.bothify(text="???-####").upper(),
        "name": f"{fake.catch_phrase()} {category}",
        "category": category,
        "brand": fake.company(),
        "price": random_price(5.0, 499.99),
        "weight": random_weight(0.1, 10.0),
        "stock_qty": random_stock_qty(),
        "rating": random_rating(),
        "description": fake.text(max_nb_chars=200).replace("\n", " "),
        "created_at": fake.date_between(start_date="-2y", end_date="today").isoformat(),
    }


def generate_inventory_csv(
    num_rows: int = DEFAULT_INVENTORY,
    output_path: str | Path = INVENTORY_CSV,
) -> list[dict]:
    """Write products to CSV and return them for transaction generation."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    products = []
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=INVENTORY_COLUMNS)
        writer.writeheader()
        for _ in range(num_rows):
            product = build_product()
            writer.writerow(product)
            products.append(product)
    return products
