"""Load generated retail CSV files into SQLite."""

import argparse
from pathlib import Path

from config import CUSTOMERS_FILE, DATABASE_FILE_NAME, INVENTORY_FILE, TRANSACTIONS_FILE
from db import create_database, load_all_csvs


def main() -> None:
    parser = argparse.ArgumentParser(description="Load retail CSV files into SQLite.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    data_dir = args.data_dir
    db_path = data_dir / DATABASE_FILE_NAME
    conn = create_database(db_path)
    load_all_csvs(
        conn,
        data_dir / CUSTOMERS_FILE,
        data_dir / INVENTORY_FILE,
        data_dir / TRANSACTIONS_FILE,
    )
    conn.close()
    print(f"Database ready: {db_path}")


if __name__ == "__main__":
    main()
