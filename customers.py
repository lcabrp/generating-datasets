"""Generate the customers CSV."""

import csv
from pathlib import Path

from faker import Faker

from config import CUSTOMERS_COLUMNS, CUSTOMERS_CSV, DEFAULT_CUSTOMERS
from utils import random_date, uuid4_str

fake = Faker()


def build_customer() -> dict:
    return {
        "customer_id": uuid4_str(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "address": fake.street_address(),
        "city": fake.city(),
        "state": fake.state(),
        "zip_code": fake.postcode(),
        "country": fake.country(),
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
        "gender": fake.random_element(elements=("Male", "Female", "Non-binary")),
        "signup_date": random_date(365, 0),
    }


def generate_customers_csv(
    num_rows: int = DEFAULT_CUSTOMERS,
    output_path: str | Path = CUSTOMERS_CSV,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CUSTOMERS_COLUMNS)
        writer.writeheader()
        for _ in range(num_rows):
            writer.writerow(build_customer())
