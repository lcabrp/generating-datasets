#!/usr/bin/env python3
"""Generate a synthetic warehouse operations SQLite database.

This is the source-of-truth version of the older WMS demo generator from
`data-wrangling` and the enhanced generator used by `warehouse-ai-assistant`.
It keeps the useful operational story while making the output path, seed, and
dataset size explicit so other projects can reuse it safely.
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker


WAREHOUSES = [
    (1, "SDF1", "Louisville Hub", "Louisville", "KY", "EST", 1),
    (2, "DFW1", "Dallas Fulfillment", "Dallas", "TX", "CST", 1),
    (3, "RNO1", "Reno Distribution", "Reno", "NV", "PST", 1),
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the normalized warehouse schema from a clean database state."""
    conn.executescript(
        """
        DROP TABLE IF EXISTS labor_metrics;
        DROP TABLE IF EXISTS shipments;
        DROP TABLE IF EXISTS exceptions;
        DROP TABLE IF EXISTS order_lines;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS inventory;
        DROP TABLE IF EXISTS items;
        DROP TABLE IF EXISTS locations;
        DROP TABLE IF EXISTS warehouses;

        CREATE TABLE warehouses (
            warehouse_id INTEGER PRIMARY KEY,
            warehouse_code TEXT UNIQUE,
            warehouse_name TEXT,
            city TEXT,
            state TEXT,
            timezone TEXT,
            is_active INTEGER
        );

        CREATE TABLE locations (
            location_id INTEGER PRIMARY KEY,
            warehouse_id INTEGER,
            zone TEXT,
            aisle TEXT,
            bay TEXT,
            level TEXT,
            bin_code TEXT,
            location_type TEXT,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
        );

        CREATE TABLE items (
            item_id INTEGER PRIMARY KEY,
            sku TEXT UNIQUE,
            item_name TEXT,
            category TEXT,
            unit_cost REAL,
            reorder_point INTEGER,
            safety_stock INTEGER,
            supplier_name TEXT,
            is_active INTEGER
        );

        CREATE TABLE inventory (
            inventory_id INTEGER PRIMARY KEY,
            snapshot_date TEXT,
            warehouse_id INTEGER,
            location_id INTEGER,
            item_id INTEGER,
            on_hand_qty INTEGER,
            allocated_qty INTEGER,
            available_qty INTEGER,
            inbound_qty INTEGER,
            inventory_status TEXT,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
            FOREIGN KEY (location_id) REFERENCES locations(location_id),
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            order_number TEXT UNIQUE,
            warehouse_id INTEGER,
            order_date TEXT,
            promised_ship_date TEXT,
            actual_ship_date TEXT,
            customer_region TEXT,
            priority TEXT,
            order_status TEXT,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
        );

        CREATE TABLE order_lines (
            order_line_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            item_id INTEGER,
            ordered_qty INTEGER,
            shipped_qty INTEGER,
            backordered_qty INTEGER,
            line_status TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        );

        CREATE TABLE exceptions (
            exception_id INTEGER PRIMARY KEY,
            warehouse_id INTEGER,
            item_id INTEGER,
            order_id INTEGER,
            exception_type TEXT,
            severity TEXT,
            created_at TEXT,
            resolved_at TEXT,
            exception_status TEXT,
            notes TEXT,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
            FOREIGN KEY (item_id) REFERENCES items(item_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );

        CREATE TABLE labor_metrics (
            metric_id INTEGER PRIMARY KEY,
            employee_name TEXT,
            task_type TEXT,
            warehouse_id INTEGER,
            units_processed INTEGER,
            start_time TEXT,
            end_time TEXT,
            error_count INTEGER,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
        );

        CREATE TABLE shipments (
            shipment_id INTEGER PRIMARY KEY,
            tracking_number TEXT UNIQUE,
            order_id INTEGER,
            carrier TEXT,
            planned_date TEXT,
            actual_date TEXT,
            delay_flag INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        """
    )


def generate_locations(rng: random.Random, locations_per_warehouse: int) -> tuple[list[tuple], dict[int, list[tuple]]]:
    zones = ["A", "BULK", "PACK", "PICK", "STAGE"]
    location_types = ["PICK", "BULK", "STAGE", "PACK"]
    locations = []
    locations_by_warehouse = {warehouse[0]: [] for warehouse in WAREHOUSES}
    location_id = 1

    for warehouse in WAREHOUSES:
        warehouse_id = warehouse[0]
        for _ in range(locations_per_warehouse):
            zone = rng.choice(zones)
            if zone == "PICK":
                location_type = "PICK"
            elif zone == "BULK":
                location_type = "BULK"
            else:
                location_type = rng.choice(location_types)
            aisle = f"{rng.randint(1, 40):02d}"
            bay = f"{rng.randint(1, 50):02d}"
            level = f"{rng.randint(1, 8):02d}"
            bin_code = f"{zone}-{aisle}-{bay}-{level}"
            row = (location_id, warehouse_id, zone, aisle, bay, level, bin_code, location_type)
            locations.append(row)
            locations_by_warehouse[warehouse_id].append(row)
            location_id += 1
    return locations, locations_by_warehouse


def generate_items(fake: Faker, rng: random.Random, count: int) -> list[tuple]:
    categories = ["Apparel", "Footwear", "Accessories", "Packing Supplies"]
    suppliers = [fake.company() for _ in range(20)]
    items = []

    for item_id in range(1, count + 1):
        category = rng.choice(categories)
        sku = f"{category[:3].upper()}-{10000 + item_id}"
        item_name = f"{fake.catch_phrase().title()} {category}"
        unit_cost = round(rng.uniform(5.50, 150.00), 2)
        reorder_point = rng.randint(10, 150)
        safety_stock = int(reorder_point * 1.5)
        supplier = rng.choice(suppliers)
        items.append((item_id, sku, item_name, category, unit_cost, reorder_point, safety_stock, supplier, 1))
    return items


def generate_inventory(
    rng: random.Random,
    items: list[tuple],
    locations_by_warehouse: dict[int, list[tuple]],
    snapshot_date: datetime,
) -> list[tuple]:
    inventory = []
    inventory_id = 1

    for item in items:
        item_id = item[0]
        reorder_point = item[5]
        for warehouse_id in locations_by_warehouse:
            location = rng.choice(locations_by_warehouse[warehouse_id])
            on_hand = rng.randint(0, 500)
            allocated = rng.randint(0, min(50, on_hand))
            available = on_hand - allocated
            inbound = rng.choice([0, 0, 0, 50, 100, 250])
            status = (
                "CRITICAL"
                if on_hand == 0
                else "LOW"
                if on_hand < reorder_point
                else "OVERSTOCK"
                if on_hand > 400
                else "OK"
            )
            inventory.append(
                (
                    inventory_id,
                    snapshot_date.strftime("%Y-%m-%d"),
                    warehouse_id,
                    location[0],
                    item_id,
                    on_hand,
                    allocated,
                    available,
                    inbound,
                    status,
                )
            )
            inventory_id += 1
    return inventory


def generate_orders(
    fake: Faker,
    rng: random.Random,
    num_items: int,
    num_orders: int,
    now: datetime,
) -> tuple[list[tuple], list[tuple], list[tuple], list[tuple]]:
    regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
    priorities = ["Standard", "Standard", "Standard", "Rush", "VIP"]
    order_statuses = ["Open", "Released", "Shipped", "Shipped", "Delayed", "Backorder"]
    carriers = ["UPS", "FedEx", "USPS", "DHL", "LaserShip"]
    employees = [fake.name() for _ in range(50)]

    orders = []
    order_lines = []
    shipments = []
    labor_metrics = []
    order_line_id = 1
    shipment_id = 1
    metric_id = 1

    for order_id in range(1, num_orders + 1):
        order_number = f"ORD-{100000 + order_id}"
        warehouse_id = rng.randint(1, len(WAREHOUSES))
        order_status = rng.choice(order_statuses)
        order_date = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23))
        promised_date = order_date + timedelta(days=rng.choice([2, 3, 5]))
        actual_date = None

        if order_status == "Shipped":
            picker = rng.choice(employees)
            start_pick = order_date + timedelta(hours=rng.randint(1, 12))
            total_ordered_qty = 0
            lines_to_create = rng.randint(1, 5)

            for _ in range(lines_to_create):
                item_id = rng.randint(1, num_items)
                ordered_qty = rng.randint(1, 15)
                total_ordered_qty += ordered_qty
                order_lines.append((order_line_id, order_id, item_id, ordered_qty, ordered_qty, 0, "Shipped"))
                order_line_id += 1

            end_pick = start_pick + timedelta(minutes=rng.randint(5, 45) * lines_to_create)
            errors = 1 if rng.random() < 0.05 else 0
            labor_metrics.append(
                (
                    metric_id,
                    picker,
                    "Picking",
                    warehouse_id,
                    total_ordered_qty,
                    start_pick.strftime("%Y-%m-%d %H:%M:%S"),
                    end_pick.strftime("%Y-%m-%d %H:%M:%S"),
                    errors,
                )
            )
            metric_id += 1

            actual_dt = end_pick + timedelta(hours=rng.randint(2, 24))
            actual_date = actual_dt.strftime("%Y-%m-%d %H:%M:%S")
            delay_flag = 1 if actual_dt > promised_date else 0
            carrier = rng.choice(carriers)
            # Use a deterministic local pattern instead of Faker.unique so large
            # reruns do not depend on shared unique state.
            tracking = f"{carrier[:2].upper()}{order_id:010d}{rng.randint(1000, 9999)}"
            shipments.append(
                (
                    shipment_id,
                    tracking,
                    order_id,
                    carrier,
                    promised_date.strftime("%Y-%m-%d %H:%M:%S"),
                    actual_date,
                    delay_flag,
                )
            )
            shipment_id += 1
        else:
            for _ in range(rng.randint(1, 5)):
                item_id = rng.randint(1, num_items)
                ordered_qty = rng.randint(1, 15)
                if order_status == "Backorder":
                    shipped_qty = rng.randint(0, ordered_qty - 1)
                    backordered_qty = ordered_qty - shipped_qty
                    line_status = "Backorder"
                else:
                    shipped_qty = 0
                    backordered_qty = 0
                    line_status = "Open" if order_status in ("Open", "Delayed") else "Allocated"
                order_lines.append((order_line_id, order_id, item_id, ordered_qty, shipped_qty, backordered_qty, line_status))
                order_line_id += 1

        orders.append(
            (
                order_id,
                order_number,
                warehouse_id,
                order_date.strftime("%Y-%m-%d %H:%M:%S"),
                promised_date.strftime("%Y-%m-%d %H:%M:%S"),
                actual_date,
                rng.choice(regions),
                rng.choice(priorities),
                order_status,
            )
        )

    return orders, order_lines, shipments, labor_metrics


def generate_exceptions(rng: random.Random, num_items: int, num_orders: int, count: int, now: datetime) -> list[tuple]:
    exception_types = [
        "Low Stock",
        "Delayed Shipment",
        "Scanner Issue",
        "Inventory Discrepancy",
        "Damaged Goods",
        "Cycle Count Variance",
    ]
    severities = ["Low", "Medium", "High", "Critical"]
    statuses = ["Open", "In Progress", "Resolved", "Resolved"]
    exceptions = []

    for exception_id in range(1, count + 1):
        status = rng.choice(statuses)
        created_at = now - timedelta(days=rng.randint(0, 30))
        resolved_at = created_at + timedelta(hours=rng.randint(1, 72)) if status == "Resolved" else None
        exception_type = rng.choice(exception_types)
        exceptions.append(
            (
                exception_id,
                rng.randint(1, len(WAREHOUSES)),
                rng.randint(1, num_items) if rng.random() > 0.3 else None,
                rng.randint(1, num_orders) if rng.random() > 0.5 else None,
                exception_type,
                rng.choice(severities),
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                resolved_at.strftime("%Y-%m-%d %H:%M:%S") if resolved_at else None,
                status,
                f"System generated {exception_type} exception",
            )
        )
    return exceptions


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "warehouses",
        "locations",
        "items",
        "inventory",
        "orders",
        "order_lines",
        "shipments",
        "labor_metrics",
        "exceptions",
    ]
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def generate_database(
    db_path: str | Path = "data/warehouse.db",
    num_items: int = 2_000,
    locations_per_warehouse: int = 2_000,
    num_orders: int = 10_000,
    num_exceptions: int = 500,
    seed: int = 42,
) -> dict[str, int]:
    """Generate the warehouse SQLite database and return table row counts."""
    if min(num_items, locations_per_warehouse, num_orders, num_exceptions) < 0:
        raise ValueError("dataset size arguments must be non-negative")
    if num_items == 0 and (num_orders > 0 or num_exceptions > 0):
        raise ValueError("num_items must be greater than zero when generating orders or exceptions")

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    fake = Faker("en_US")
    fake.seed_instance(seed)
    now = datetime(2026, 4, 1, 8, 0, 0)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        create_schema(conn)
        conn.executemany("INSERT INTO warehouses VALUES (?, ?, ?, ?, ?, ?, ?)", WAREHOUSES)

        locations, locations_by_warehouse = generate_locations(rng, locations_per_warehouse)
        conn.executemany("INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", locations)

        items = generate_items(fake, rng, num_items)
        conn.executemany("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", items)

        inventory = generate_inventory(rng, items, locations_by_warehouse, now)
        conn.executemany("INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", inventory)

        orders, order_lines, shipments, labor_metrics = generate_orders(fake, rng, num_items, num_orders, now)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", orders)
        conn.executemany("INSERT INTO order_lines VALUES (?, ?, ?, ?, ?, ?, ?)", order_lines)
        conn.executemany("INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?)", shipments)
        conn.executemany("INSERT INTO labor_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?)", labor_metrics)

        exceptions = generate_exceptions(rng, num_items, num_orders, num_exceptions, now)
        conn.executemany("INSERT INTO exceptions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", exceptions)

        conn.commit()
        return table_counts(conn)
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a synthetic warehouse operations SQLite database.")
    parser.add_argument("--output", type=Path, default=Path("data/warehouse.db"), help="SQLite database output path.")
    parser.add_argument("--items", type=int, default=2_000, help="Number of item master rows.")
    parser.add_argument("--locations-per-warehouse", type=int, default=2_000, help="Locations to create for each warehouse.")
    parser.add_argument("--orders", type=int, default=10_000, help="Number of orders to generate.")
    parser.add_argument("--exceptions", type=int, default=500, help="Number of operational exception rows.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = generate_database(
        db_path=args.output,
        num_items=args.items,
        locations_per_warehouse=args.locations_per_warehouse,
        num_orders=args.orders,
        num_exceptions=args.exceptions,
        seed=args.seed,
    )
    print(f"Warehouse operations database created: {args.output}")
    for table, count in counts.items():
        print(f"{table}: {count:,}")


if __name__ == "__main__":
    main()
