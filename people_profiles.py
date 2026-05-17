#!/usr/bin/env python3
"""Generate synthetic people profile data.

This replaces the useful wrapper idea from `my-db-gen/generate_people_data.py`
without carrying over the old pydbgen fork. The generator uses Faker directly,
keeps row-count and seed behavior explicit, and writes both CSV and SQLite
outputs for Pandas and SQL tutorials.
"""

from __future__ import annotations

import argparse
import random
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from faker import Faker


DEFAULT_AS_OF_DATE = date(2026, 5, 17)
EMPLOYMENT_STATUS_WEIGHTS = {
    "Employed": 0.68,
    "Self-employed": 0.08,
    "Student": 0.07,
    "Unemployed": 0.06,
    "Retired": 0.11,
}
EDUCATION_LEVEL_WEIGHTS = {
    "High School": 0.28,
    "Associate's": 0.14,
    "Bachelor's": 0.34,
    "Master's": 0.19,
    "Doctorate": 0.03,
    "Professional Certification": 0.02,
}
MARITAL_STATUS_WEIGHTS = {
    "Single": 0.34,
    "Married": 0.46,
    "Divorced": 0.12,
    "Widowed": 0.05,
    "Separated": 0.03,
}


def subtract_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        # Handles February 29 when the target year is not a leap year.
        return value.replace(month=2, day=28, year=value.year - years)


def age_on_date(birthdate: date, as_of_date: date) -> int:
    years = as_of_date.year - birthdate.year
    if (as_of_date.month, as_of_date.day) < (birthdate.month, birthdate.day):
        years -= 1
    return years


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def email_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return slug or "person"


def realistic_email(fake: Faker, rng: random.Random, first_name: str, last_name: str) -> str:
    domain = fake.free_email_domain()
    formats = (
        f"{first_name}.{last_name}",
        f"{first_name}_{last_name}",
        f"{first_name[0]}{last_name}",
        f"{last_name}.{first_name}",
        f"{first_name}.{last_name}{rng.randint(10, 99)}",
    )
    return f"{email_slug(rng.choice(formats))}@{domain}"


def annual_income(rng: random.Random, age: int, education: str, employment_status: str) -> int:
    if employment_status == "Student":
        base = rng.randint(8_000, 38_000)
    elif employment_status == "Unemployed":
        base = rng.randint(0, 24_000)
    elif employment_status == "Retired":
        base = rng.randint(18_000, 85_000)
    else:
        base = rng.randint(28_000, 155_000)

    education_multiplier = {
        "High School": 0.86,
        "Associate's": 0.96,
        "Bachelor's": 1.12,
        "Master's": 1.28,
        "Doctorate": 1.42,
        "Professional Certification": 1.08,
    }[education]
    age_multiplier = 0.82 if age < 25 else 1.0 if age < 55 else 0.92
    return int(round(base * education_multiplier * age_multiplier, -2))


def create_people_profiles(
    rows: int = 1_000,
    seed: int = 42,
    locale: str = "en_US",
    min_age: int = 18,
    max_age: int = 85,
    as_of_date: date = DEFAULT_AS_OF_DATE,
) -> pd.DataFrame:
    if rows <= 0:
        raise ValueError("rows must be greater than zero")
    if min_age < 0:
        raise ValueError("min_age must be zero or greater")
    if max_age < min_age:
        raise ValueError("max_age must be greater than or equal to min_age")

    Faker.seed(seed)
    fake = Faker(locale)
    fake.seed_instance(seed)
    fake.unique.clear()
    rng = random.Random(seed)
    earliest_birthdate = subtract_years(as_of_date, max_age + 1)
    latest_birthdate = subtract_years(as_of_date, min_age)

    records = []
    for person_id in range(1, rows + 1):
        first_name = fake.first_name()
        last_name = fake.last_name()
        birthdate = fake.date_between_dates(date_start=earliest_birthdate, date_end=latest_birthdate)
        age = age_on_date(birthdate, as_of_date)
        education = weighted_choice(rng, EDUCATION_LEVEL_WEIGHTS)
        employment_status = weighted_choice(rng, EMPLOYMENT_STATUS_WEIGHTS)
        latitude = float(fake.latitude())
        longitude = float(fake.longitude())

        records.append(
            {
                "person_id": f"P{person_id:07d}",
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "gender": rng.choice(("Female", "Male", "Non-binary")),
                "birthdate": birthdate,
                "age": age,
                "ssn": fake.ssn(),
                "phone_number": fake.phone_number(),
                "email": realistic_email(fake, rng, first_name, last_name),
                "street_address": fake.street_address().replace("\n", " "),
                "city": fake.city(),
                "state": fake.state(),
                "zipcode": fake.zipcode(),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "job_title": fake.job() if employment_status in {"Employed", "Self-employed"} else None,
                "company": fake.company() if employment_status == "Employed" else None,
                "employment_status": employment_status,
                "annual_income": annual_income(rng, age, education, employment_status),
                "education_level": education,
                "marital_status": weighted_choice(rng, MARITAL_STATUS_WEIGHTS),
                "created_at": datetime.combine(as_of_date, datetime.min.time()),
            }
        )
    return pd.DataFrame(records)


def normalize_for_storage(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[column]):
            out[column] = out[column].dt.strftime("%Y-%m-%d")
        elif out[column].dtype == "object":
            out[column] = out[column].map(
                lambda value: value.isoformat()
                if isinstance(value, (date, datetime, pd.Timestamp))
                else value
            )
    return out


def write_outputs(
    profiles: pd.DataFrame,
    output_dir: str | Path = "data/people_profiles",
    csv_name: str = "people_profiles.csv",
    sqlite_name: str = "people_profiles.db",
    table_name: str = "people_profiles",
    write_sqlite: bool = True,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    normalized_profiles = normalize_for_storage(profiles)
    csv_path = output / csv_name
    normalized_profiles.to_csv(csv_path, index=False)

    result = {"csv": csv_path}
    if write_sqlite:
        db_path = output / sqlite_name
        with sqlite3.connect(db_path) as conn:
            normalized_profiles.to_sql(table_name, conn, if_exists="replace", index=False)
        result["database"] = db_path
    return result


def generate_dataset(
    output_dir: str | Path = "data/people_profiles",
    rows: int = 1_000,
    seed: int = 42,
    locale: str = "en_US",
    min_age: int = 18,
    max_age: int = 85,
    as_of_date: date = DEFAULT_AS_OF_DATE,
    sqlite_name: str = "people_profiles.db",
    skip_sqlite: bool = False,
) -> dict[str, int | Path]:
    profiles = create_people_profiles(rows, seed, locale, min_age, max_age, as_of_date)
    paths = write_outputs(profiles, output_dir, sqlite_name=sqlite_name, write_sqlite=not skip_sqlite)
    return {"people_profiles": len(profiles), **paths}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic people profile CSV and SQLite data.")
    parser.add_argument("--rows", type=int, default=1_000, help="Number of people profiles to generate.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/people_profiles"), help="Output directory.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    parser.add_argument("--locale", default="en_US", help="Faker locale to use.")
    parser.add_argument("--min-age", type=int, default=18, help="Minimum generated age.")
    parser.add_argument("--max-age", type=int, default=85, help="Maximum generated age.")
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=DEFAULT_AS_OF_DATE, help="Anchor date in YYYY-MM-DD format.")
    parser.add_argument("--sqlite-name", default="people_profiles.db", help="SQLite database filename.")
    parser.add_argument("--skip-sqlite", action="store_true", help="Only write CSV output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_dataset(
        output_dir=args.output_dir,
        rows=args.rows,
        seed=args.seed,
        locale=args.locale,
        min_age=args.min_age,
        max_age=args.max_age,
        as_of_date=args.as_of_date,
        sqlite_name=args.sqlite_name,
        skip_sqlite=args.skip_sqlite,
    )
    print(f"People profiles dataset created in {args.output_dir}")
    print(f"people_profiles: {result['people_profiles']:,} -> {result['csv']}")
    if "database" in result:
        print(f"database: {result['database']}")


if __name__ == "__main__":
    main()
