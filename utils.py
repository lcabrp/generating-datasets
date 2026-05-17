"""Common helper functions used by multiple generators."""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Sequence

from faker import Faker

from config import ORDER_STATUSES, PAYMENT_METHODS

fake = Faker()


def set_seed(seed: int) -> None:
    """Seed Python random and Faker for reproducible generated datasets."""
    random.seed(seed)
    Faker.seed(seed)
    fake.seed_instance(seed)


def uuid4_str() -> str:
    return str(uuid.uuid4())


def random_price(low: float = 5.0, high: float = 500.0) -> str:
    return f"{random.uniform(low, high):.2f}"


def random_weight(low: float = 0.1, high: float = 10.0) -> str:
    return f"{random.uniform(low, high):.1f}"


def random_stock_qty() -> int:
    return random.randint(0, 1_000)


def random_rating() -> float:
    return round(random.uniform(1.0, 5.0), 1)


def random_status() -> str:
    return random.choice(ORDER_STATUSES)


def random_payment_method() -> str:
    return random.choice(PAYMENT_METHODS)


def random_coupon_code() -> str:
    return fake.bothify(text="????-####") if random.random() < 0.2 else ""


def random_date(start_days_ago: int = 365, end_days_ago: int = 0) -> str:
    end_date = datetime.now() - timedelta(days=end_days_ago)
    start_date = datetime.now() - timedelta(days=start_days_ago)
    return fake.date_between(start_date=start_date, end_date=end_date).isoformat()


def random_json_items(products: Sequence[dict], max_items: int = 5) -> str:
    """Build a JSON string containing transaction line items."""
    if not products:
        raise ValueError("At least one product is required to generate transaction items")

    num_items = min(random.randint(1, max_items), len(products))
    chosen = random.sample(list(products), k=num_items)
    items = []
    for product in chosen:
        items.append(
            {
                "product_id": product["product_id"],
                "quantity": random.randint(1, 5),
                "unit_price": product["price"],
            }
        )
    return json.dumps(items)
