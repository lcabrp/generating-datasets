#!/usr/bin/env python3
"""Small tutorial datasets that demonstrate conditional and simulation logic.

These generators replace `simp_data_gen.py` from `data-wrangling`. They are
kept separate from the larger retail and warehouse generators because their
purpose is teaching: each output is intentionally small and easy to inspect.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


PLANS = ["Free", "Basic", "Pro", "Enterprise"]
PLAN_WEIGHTS = [0.45, 0.30, 0.18, 0.07]


def monthly_spend(plan: str, age: int, rng: random.Random) -> float:
    if plan == "Free":
        base = rng.uniform(0, 10)
    elif plan == "Basic":
        base = rng.uniform(10, 60)
    elif plan == "Pro":
        base = rng.uniform(50, 180)
    else:
        base = rng.uniform(150, 500)
    # The age multiplier is the lesson: synthetic fields should have plausible
    # relationships, not independent random values.
    if age >= 40:
        base *= 1.15
    return round(base, 2)


def customer_rows(count: int, seed: int = 42) -> list[dict[str, object]]:
    rng = random.Random(seed)
    rows = []
    for customer_id in range(1, count + 1):
        age = rng.randint(18, 75)
        plan = rng.choices(PLANS, weights=PLAN_WEIGHTS, k=1)[0]
        rows.append(
            {
                "customer_id": f"CUST{customer_id:05d}",
                "age": age,
                "plan": plan,
                "monthly_spend": monthly_spend(plan, age, rng),
            }
        )
    return rows


def warehouse_log_rows(days: int = 30, seed: int = 42, start: datetime | None = None) -> list[dict[str, object]]:
    rng = random.Random(seed)
    inventory = {"Product_A": 100, "Product_B": 100}
    current_time = start or datetime(2026, 1, 1, 9, 0, 0)
    rows = []

    for _ in range(days):
        for product in list(inventory):
            for _ in range(rng.randint(1, 5)):
                qty = rng.randint(1, 10)
                before = inventory[product]
                if inventory[product] >= qty:
                    inventory[product] -= qty
                    status = "fulfilled"
                else:
                    status = "backorder"
                rows.append(
                    {
                        "timestamp": current_time.isoformat(),
                        "product": product,
                        "qty": qty,
                        "stock_before": before,
                        "stock_after": inventory[product],
                        "status": status,
                    }
                )

            if inventory[product] < 20:
                restock_amount = 50
                before = inventory[product]
                inventory[product] += restock_amount
                rows.append(
                    {
                        "timestamp": current_time.isoformat(),
                        "product": product,
                        "qty": restock_amount,
                        "stock_before": before,
                        "stock_after": inventory[product],
                        "status": "restock",
                    }
                )
        current_time += timedelta(days=1)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> int:
    if not rows:
        raise ValueError("rows must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def generate_tutorial_datasets(
    output_dir: str | Path = "data/tutorial",
    customers: int = 1_000,
    warehouse_days: int = 30,
    seed: int = 42,
) -> dict[str, int | Path]:
    output = Path(output_dir)
    customer_path = output / "synthetic_customers.csv"
    warehouse_path = output / "warehouse_sim.csv"
    customer_count = write_csv(customer_path, customer_rows(customers, seed))
    warehouse_count = write_csv(warehouse_path, warehouse_log_rows(warehouse_days, seed))
    return {
        "customers_csv": customer_path,
        "warehouse_log_csv": warehouse_path,
        "customers": customer_count,
        "warehouse_events": warehouse_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate small tutorial datasets.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/tutorial"), help="Output directory.")
    parser.add_argument("--customers", type=int, default=1_000, help="Number of customer rows.")
    parser.add_argument("--warehouse-days", type=int, default=30, help="Number of warehouse simulation days.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_tutorial_datasets(args.output_dir, args.customers, args.warehouse_days, args.seed)
    print(f"Tutorial datasets created in {args.output_dir}")
    print(f"customers: {result['customers']:,} -> {result['customers_csv']}")
    print(f"warehouse_events: {result['warehouse_events']:,} -> {result['warehouse_log_csv']}")


if __name__ == "__main__":
    main()
