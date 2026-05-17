"""Command line entrypoint for the credit card transaction generator."""

from __future__ import annotations

import argparse
from pathlib import Path

from .generator import generate_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate normalized synthetic credit card customers and transactions."
    )
    parser.add_argument("--customers", type=int, default=1_000, help="Number of customer rows to generate.")
    parser.add_argument("--start-date", default="2020-01-01", help="Inclusive start date. Prefer YYYY-MM-DD.")
    parser.add_argument("--end-date", default="2020-12-31", help="Inclusive end date. Prefer YYYY-MM-DD.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/credit_card_transactions"), help="Output directory.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    parser.add_argument(
        "--fraud-rate",
        type=float,
        default=0.002,
        help="Approximate transaction-level fraud probability. 0.002 is about 0.2%%.",
    )
    parser.add_argument(
        "--delimiter",
        default="|",
        help="CSV delimiter. Pipe is the default to stay compatible with the Sparkov-derived capstone data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_dataset(
        output_dir=args.output_dir,
        customers=args.customers,
        start_date=args.start_date,
        end_date=args.end_date,
        seed=args.seed,
        fraud_rate=args.fraud_rate,
        delimiter=args.delimiter,
    )
    print("Credit card transaction dataset generation complete.")
    print(f"Customers:    {result['customers']:,} -> {result['customers_csv']}")
    print(f"Transactions: {result['transactions']:,} -> {result['transactions_csv']}")


if __name__ == "__main__":
    main()
