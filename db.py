"""SQLite helpers for loading generated retail CSV files."""

import csv
import sqlite3
from pathlib import Path
from typing import Iterable

from config import (
    CUSTOMERS_COLUMNS,
    CUSTOMERS_CSV,
    DATABASE_FILE,
    INVENTORY_COLUMNS,
    INVENTORY_CSV,
    TRANSACTIONS_COLUMNS,
    TRANSACTIONS_CSV,
)

TABLE_DEFINITIONS = {
    "customers": (
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            country TEXT,
            date_of_birth TEXT,
            gender TEXT,
            signup_date TEXT
        );
        """,
        CUSTOMERS_COLUMNS,
    ),
    "inventory": (
        """
        CREATE TABLE IF NOT EXISTS inventory (
            product_id TEXT PRIMARY KEY,
            sku TEXT,
            name TEXT,
            category TEXT,
            brand TEXT,
            price REAL,
            weight REAL,
            stock_qty INTEGER,
            rating REAL,
            description TEXT,
            created_at TEXT
        );
        """,
        INVENTORY_COLUMNS,
    ),
    "transactions": (
        """
        CREATE TABLE IF NOT EXISTS transactions (
            order_id TEXT PRIMARY KEY,
            order_date TEXT,
            customer_id TEXT,
            shipping_address TEXT,
            status TEXT,
            total_amount REAL,
            shipping_cost REAL,
            payment_method TEXT,
            coupon_code TEXT,
            items TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        );
        """,
        TRANSACTIONS_COLUMNS,
    ),
}

INDEX_DEFINITIONS = [
    "CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);",
    "CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category);",
]


def _open_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DATABASE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path.as_posix())


def _execute_many(conn: sqlite3.Connection, sql: str, rows: Iterable[tuple]) -> None:
    with conn:
        conn.executemany(sql, rows)


def create_database(db_path: str | Path | None = None, overwrite: bool = True) -> sqlite3.Connection:
    """Create the SQLite database, tables, and indexes."""
    path = Path(db_path) if db_path else DATABASE_FILE
    if overwrite and path.exists():
        path.unlink()

    conn = _open_connection(path)
    cursor = conn.cursor()

    for create_sql, _ in TABLE_DEFINITIONS.values():
        cursor.executescript(create_sql)

    for index_sql in INDEX_DEFINITIONS:
        cursor.executescript(index_sql)

    conn.commit()
    return conn


def import_csv_to_table(
    conn: sqlite3.Connection,
    table_name: str,
    csv_path: str | Path,
    limit: int | None = None,
) -> None:
    """Bulk-load a CSV into a known table."""
    if table_name not in TABLE_DEFINITIONS:
        raise ValueError(f"Unknown table: {table_name}")

    _, columns = TABLE_DEFINITIONS[table_name]
    placeholders = ", ".join("?" for _ in columns)
    insert_sql = (
        f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) "
        f"VALUES ({placeholders})"
    )

    rows = []
    with Path(csv_path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader, start=1):
            rows.append(tuple(row[col] for col in columns))
            if limit and i >= limit:
                break

    if rows:
        _execute_many(conn, insert_sql, rows)


def load_all_csvs(
    conn: sqlite3.Connection,
    customers_csv: str | Path = CUSTOMERS_CSV,
    inventory_csv: str | Path = INVENTORY_CSV,
    transactions_csv: str | Path = TRANSACTIONS_CSV,
) -> None:
    """Import all generated retail CSVs into SQLite."""
    import_csv_to_table(conn, "customers", customers_csv)
    import_csv_to_table(conn, "inventory", inventory_csv)
    import_csv_to_table(conn, "transactions", transactions_csv)
