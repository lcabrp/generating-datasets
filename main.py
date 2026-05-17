#!/usr/bin/env python3
"""Generate related retail CSV datasets and optionally load them into SQLite."""

import argparse
import csv
from pathlib import Path

from config import (
    CUSTOMERS_FILE,
    DATABASE_FILE_NAME,
    DEFAULT_CUSTOMERS,
    DEFAULT_INVENTORY,
    DEFAULT_SEED,
    DEFAULT_TRANSACTIONS,
    INVENTORY_FILE,
    MAX_TRANSACTIONS,
    TRANSACTIONS_FILE,
)
from customers import generate_customers_csv
from db import create_database, load_all_csvs
from inventory import generate_inventory_csv
from transactions import build_transactions
from utils import set_seed


def read_customers(customers_csv: str | Path) -> list[dict]:
    with Path(customers_csv).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate related retail customers, inventory, and transactions datasets."
    )
    parser.add_argument("customers_pos", nargs="?", type=int, help="Backward-compatible customer count positional argument.")
    parser.add_argument("--customers", type=int, default=None, help="Number of customer rows to generate.")
    parser.add_argument("--inventory", "--products", dest="inventory", type=int, default=DEFAULT_INVENTORY, help="Number of inventory/product rows to generate.")
    parser.add_argument("--transactions", type=int, default=DEFAULT_TRANSACTIONS, help="Number of transaction rows to generate.")
    parser.add_argument("--max-transactions", type=int, default=MAX_TRANSACTIONS, help="Upper bound for transaction rows.")
    parser.add_argument("--output-dir", type=Path, default=Path("data"), help="Directory for generated CSV and SQLite files.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for reproducible datasets.")
    parser.add_argument("--skip-db", action="store_true", help="Only write CSV files; do not create SQLite database.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    customer_count = args.customers if args.customers is not None else args.customers_pos
    if customer_count is None:
        customer_count = DEFAULT_CUSTOMERS

    transaction_count = min(args.transactions, args.max_transactions)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    customers_csv = output_dir / CUSTOMERS_FILE
    inventory_csv = output_dir / INVENTORY_FILE
    transactions_csv = output_dir / TRANSACTIONS_FILE
    database_path = output_dir / DATABASE_FILE_NAME

    set_seed(args.seed)

    print(f"Generating {customer_count:,} customers -> {customers_csv}")
    generate_customers_csv(customer_count, customers_csv)

    print(f"Generating {args.inventory:,} inventory items -> {inventory_csv}")
    products = generate_inventory_csv(args.inventory, inventory_csv)

    print(f"Generating {transaction_count:,} transactions -> {transactions_csv}")
    customers = read_customers(customers_csv)
    build_transactions(customers, products, transaction_count, transactions_csv)

    if not args.skip_db:
        print(f"Loading CSV files into SQLite -> {database_path}")
        conn = create_database(database_path)
        load_all_csvs(conn, customers_csv, inventory_csv, transactions_csv)
        conn.close()

    print("\nRetail dataset generation complete.")
    print(f"Customers:    {customers_csv}")
    print(f"Inventory:    {inventory_csv}")
    print(f"Transactions: {transactions_csv}")
    if not args.skip_db:
        print(f"Database:     {database_path}")


if __name__ == "__main__":
    main()
