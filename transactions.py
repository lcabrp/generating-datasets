"""Generate the transactions/orders CSV."""

import csv
import json
import random
from pathlib import Path
from typing import Sequence

from config import DEFAULT_TRANSACTIONS, TRANSACTIONS_COLUMNS, TRANSACTIONS_CSV
from utils import (
    random_coupon_code,
    random_date,
    random_json_items,
    random_payment_method,
    random_status,
    uuid4_str,
)


def build_transactions(
    customers: Sequence[dict],
    products: Sequence[dict],
    num_records: int = DEFAULT_TRANSACTIONS,
    output_path: str | Path = TRANSACTIONS_CSV,
) -> None:
    if not customers:
        raise ValueError("At least one customer is required to generate transactions")
    if not products:
        raise ValueError("At least one product is required to generate transactions")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=TRANSACTIONS_COLUMNS)
        writer.writeheader()

        for _ in range(num_records):
            customer = random.choice(customers)
            items = random_json_items(products)
            total = sum(
                float(item["unit_price"]) * item["quantity"]
                for item in json.loads(items)
            )
            shipping_cost = round(random.uniform(3, 15), 2)

            writer.writerow(
                {
                    "order_id": uuid4_str(),
                    "order_date": random_date(365, 0),
                    "customer_id": customer["customer_id"],
                    "shipping_address": customer["address"],
                    "status": random_status(),
                    "total_amount": f"{total:.2f}",
                    "shipping_cost": f"{shipping_cost:.2f}",
                    "payment_method": random_payment_method(),
                    "coupon_code": random_coupon_code(),
                    "items": items,
                }
            )
