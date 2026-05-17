"""Generate normalized synthetic credit card transaction datasets.

This module keeps the strongest ideas from the Sparkov generator used by the
card-transactions-analysis capstone: customer profiles, weighted categories,
seasonal/date behavior, merchant locations, and fraud-aware transactions. The
implementation writes normalized CSV files directly so large runs do not need
to hold every transaction in memory.
"""

from __future__ import annotations

import csv
import hashlib
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
from faker import Faker


CUSTOMER_COLUMNS = [
    "ssn",
    "cc_num",
    "first",
    "last",
    "gender",
    "street",
    "city",
    "state",
    "zip",
    "lat",
    "long",
    "city_pop",
    "job",
    "dob",
    "acct_num",
    "profile",
]

TRANSACTION_COLUMNS = [
    "ssn",
    "trans_num",
    "trans_date",
    "trans_time",
    "unix_time",
    "category",
    "amt",
    "is_fraud",
    "merchant",
    "merch_lat",
    "merch_long",
]

CATEGORIES = [
    "gas_transport",
    "grocery_net",
    "grocery_pos",
    "misc_net",
    "misc_pos",
    "shopping_net",
    "shopping_pos",
    "entertainment",
    "food_dining",
    "health_fitness",
    "home",
    "kids_pets",
    "personal_care",
    "travel",
]

MERCHANT_SUFFIXES = [
    "LLC",
    "Inc",
    "Group",
    "Market",
    "Stores",
    "Services",
    "Partners",
    "Co",
]


@dataclass(frozen=True)
class Profile:
    """A compact demographic spending profile.

    Profiles are intentionally explicit instead of inferred from code. Future
    reviewers can tune behavior by changing weights here without touching the
    generation algorithm.
    """

    name: str
    gender: str
    min_age: int
    max_age: int | None
    urban: bool
    avg_transactions_per_day: tuple[int, int]
    category_weights: dict[str, int]
    amount_specs: dict[str, tuple[float, float]]
    shopping_time_weights: dict[str, int]
    travel_pct: float
    travel_max_miles: int


BASE_CATEGORY_WEIGHTS = {
    "gas_transport": 120,
    "grocery_net": 80,
    "grocery_pos": 140,
    "misc_net": 75,
    "misc_pos": 90,
    "shopping_net": 100,
    "shopping_pos": 125,
    "entertainment": 100,
    "food_dining": 110,
    "health_fitness": 85,
    "home": 115,
    "kids_pets": 90,
    "personal_care": 75,
    "travel": 45,
}

BASE_AMOUNT_SPECS = {
    "gas_transport": (70, 15),
    "grocery_net": (50, 20),
    "grocery_pos": (60, 20),
    "misc_net": (50, 150),
    "misc_pos": (60, 150),
    "shopping_net": (65, 300),
    "shopping_pos": (60, 300),
    "entertainment": (60, 75),
    "food_dining": (40, 50),
    "health_fitness": (60, 50),
    "home": (60, 50),
    "kids_pets": (60, 50),
    "personal_care": (35, 50),
    "travel": (120, 600),
}

FRAUD_CATEGORY_WEIGHTS = {
    "gas_transport": 40,
    "grocery_net": 20,
    "grocery_pos": 25,
    "misc_net": 190,
    "misc_pos": 80,
    "shopping_net": 260,
    "shopping_pos": 210,
    "entertainment": 45,
    "food_dining": 30,
    "health_fitness": 20,
    "home": 85,
    "kids_pets": 15,
    "personal_care": 25,
    "travel": 120,
}

FRAUD_AMOUNT_SPECS = {
    **BASE_AMOUNT_SPECS,
    "misc_net": (650, 300),
    "misc_pos": (350, 180),
    "shopping_net": (900, 350),
    "shopping_pos": (800, 300),
    "travel": (1200, 600),
}


def _profile(name: str, gender: str, min_age: int, max_age: int | None, urban: bool) -> Profile:
    is_young = max_age == 25
    is_older = min_age >= 50
    category_weights = dict(BASE_CATEGORY_WEIGHTS)
    if is_young:
        category_weights["entertainment"] += 55
        category_weights["shopping_net"] += 35
    if is_older:
        category_weights["health_fitness"] += 35
        category_weights["home"] += 35
    if not urban:
        category_weights["gas_transport"] += 50
        category_weights["grocery_pos"] += 30

    # Keep transaction volume close to the Sparkov profiles while still making
    # demo runs affordable. Users can reduce customers/date range for tiny tests.
    avg = (1, 4) if is_young else (1, 5)
    return Profile(
        name=name,
        gender=gender,
        min_age=min_age,
        max_age=max_age,
        urban=urban,
        avg_transactions_per_day=avg,
        category_weights=category_weights,
        amount_specs=BASE_AMOUNT_SPECS,
        shopping_time_weights={"AM": 35 if is_older else 30, "PM": 65 if is_older else 70},
        travel_pct=0.20 if not urban else 0.35,
        travel_max_miles=450 if not urban else 850,
    )


PROFILES = [
    _profile("young_adults_male_urban", "M", 18, 25, True),
    _profile("young_adults_female_urban", "F", 18, 25, True),
    _profile("young_adults_male_rural", "M", 18, 25, False),
    _profile("young_adults_female_rural", "F", 18, 25, False),
    _profile("adults_2550_male_urban", "M", 25, 50, True),
    _profile("adults_2550_female_urban", "F", 25, 50, True),
    _profile("adults_2550_male_rural", "M", 25, 50, False),
    _profile("adults_2550_female_rural", "F", 25, 50, False),
    _profile("adults_50up_male_urban", "M", 50, None, True),
    _profile("adults_50up_female_urban", "F", 50, None, True),
    _profile("adults_50up_male_rural", "M", 50, None, False),
    _profile("adults_50up_female_rural", "F", 50, None, False),
]

PROFILE_BY_NAME = {profile.name: profile for profile in PROFILES}


def parse_date(value: str) -> date:
    """Parse common date formats while documenting the canonical one."""
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date '{value}' must use YYYY-MM-DD, MM-DD-YYYY, or MM/DD/YYYY")


def weighted_choice(rng: random.Random, weights: dict[str, int]) -> str:
    choices = list(weights)
    return rng.choices(choices, weights=[weights[item] for item in choices], k=1)[0]


def date_range(start_date: date, end_date: date) -> list[date]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(days)]


def date_weights(dates: Iterable[date]) -> np.ndarray:
    weights = []
    for current in dates:
        weight = 1.0
        if current.weekday() >= 5:
            weight *= 1.45
        if (current.month, current.day) >= (11, 30) or (current.month, current.day) <= (1, 5):
            weight *= 1.75
        elif (current.month, current.day) >= (5, 24) and (current.month, current.day) <= (9, 1):
            weight *= 1.20
        weights.append(weight)
    arr = np.array(weights, dtype=float)
    return arr / arr.sum()


def gamma_amount(rng: np.random.Generator, specs: dict[str, tuple[float, float]], category: str) -> float:
    mean, stdev = specs[category]
    shape = mean**2 / stdev**2
    scale = stdev**2 / mean
    amount = rng.gamma(shape, scale)
    if amount < 1:
        amount = rng.uniform(1, 10)
    return round(float(amount), 2)


def sample_time(rng: random.Random, daypart_weights: dict[str, int], is_fraud: bool) -> time:
    daypart = weighted_choice(rng, daypart_weights)
    if is_fraud and rng.random() > 0.20:
        hour = rng.choice([0, 1, 2, 3, 22, 23])
    elif daypart == "AM":
        hour = rng.randrange(0, 12)
    else:
        hour = rng.randrange(12, 24)
    return time(hour=hour, minute=rng.randrange(60), second=rng.randrange(60))


def choose_profile(gender: str, age: int, city_pop: int) -> Profile:
    urban = city_pop >= 2_500
    for profile in PROFILES:
        if profile.gender != gender or profile.urban != urban:
            continue
        if age < profile.min_age:
            continue
        if profile.max_age is not None and age >= profile.max_age:
            continue
        return profile
    return PROFILE_BY_NAME[f"adults_2550_{'male' if gender == 'M' else 'female'}_{'urban' if urban else 'rural'}"]


def generate_customers(count: int, seed: int) -> list[dict[str, str]]:
    faker = Faker("en_US")
    Faker.seed(seed)
    rng = random.Random(seed)
    customers = []
    today = date.today()

    for _ in range(count):
        gender = rng.choice(["M", "F"])
        age = int(np.clip(rng.normalvariate(42, 17), 18, 85))
        # Build DOB from generated age instead of relying on Faker's age mix, so
        # profile assignment remains reproducible and easy to reason about.
        dob = date(today.year - age, rng.randint(1, 12), rng.randint(1, 28))
        city_pop = rng.choice([
            rng.randint(300, 2_499),
            rng.randint(2_500, 1_500_000),
        ])
        profile = choose_profile(gender, age, city_pop)
        first = faker.first_name_male() if gender == "M" else faker.first_name_female()
        lat = float(faker.latitude())
        lon = float(faker.longitude())
        customers.append(
            {
                "ssn": faker.ssn(),
                "cc_num": faker.credit_card_number(),
                "first": first,
                "last": faker.last_name(),
                "gender": gender,
                "street": faker.street_address().replace("\n", " "),
                "city": faker.city(),
                "state": faker.state_abbr(),
                "zip": faker.postcode(),
                "lat": f"{lat:.6f}",
                "long": f"{lon:.6f}",
                "city_pop": str(city_pop),
                "job": faker.job(),
                "dob": dob.isoformat(),
                "acct_num": faker.bban(),
                "profile": profile.name,
            }
        )
    return customers


def merchant_name(rng: random.Random, category: str, is_fraud: bool) -> str:
    prefix = "fraud_" if is_fraud else ""
    stem = category.replace("_", " ").title().replace(" ", "")
    return f"{prefix}{stem} {rng.choice(MERCHANT_SUFFIXES)}"


def merchant_location(rng: random.Random, customer: dict[str, str], profile: Profile) -> tuple[str, str]:
    lat = float(customer["lat"])
    lon = float(customer["long"])
    traveling = rng.random() < profile.travel_pct
    radius = 1.0
    if traveling:
        # Sparkov approximated distance using degrees. Keep that convention for
        # compatibility with downstream distance-analysis notebooks.
        radius = (profile.travel_max_miles / 100) * 1.43
    return f"{lat + rng.uniform(-radius, radius):.6f}", f"{lon + rng.uniform(-radius, radius):.6f}"


def transaction_rows(
    customers: list[dict[str, str]],
    start_date: date,
    end_date: date,
    seed: int,
    fraud_rate: float,
) -> Iterable[dict[str, str]]:
    rng = random.Random(seed + 1)
    np_rng = np.random.default_rng(seed + 1)
    dates = date_range(start_date, end_date)
    probabilities = date_weights(dates)

    for customer in customers:
        profile = PROFILE_BY_NAME[customer["profile"]]
        days = len(dates)
        per_day = np_rng.integers(
            profile.avg_transactions_per_day[0],
            profile.avg_transactions_per_day[1] + 1,
        )
        transaction_count = int(days * per_day)
        sampled_dates = np_rng.choice(dates, size=transaction_count, p=probabilities)

        for current_date in sampled_dates:
            is_fraud = rng.random() < fraud_rate
            weights = FRAUD_CATEGORY_WEIGHTS if is_fraud else profile.category_weights
            specs = FRAUD_AMOUNT_SPECS if is_fraud else profile.amount_specs
            category = weighted_choice(rng, weights)
            tx_time = sample_time(rng, profile.shopping_time_weights, is_fraud)
            tx_datetime = datetime.combine(current_date, tx_time)
            merch_lat, merch_long = merchant_location(rng, customer, profile)
            yield {
                "ssn": customer["ssn"],
                "trans_num": hashlib.md5(f"{seed}:{customer['ssn']}:{tx_datetime}:{rng.random()}".encode()).hexdigest(),
                "trans_date": current_date.isoformat(),
                "trans_time": tx_time.isoformat(),
                "unix_time": str(int(tx_datetime.timestamp())),
                "category": category,
                "amt": f"{gamma_amount(np_rng, specs, category):.2f}",
                "is_fraud": "1" if is_fraud else "0",
                "merchant": merchant_name(rng, category, is_fraud),
                "merch_lat": merch_lat,
                "merch_long": merch_long,
            }


def write_csv(path: Path, rows: Iterable[dict[str, str]], columns: list[str], delimiter: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def generate_dataset(
    output_dir: str | Path,
    customers: int = 1_000,
    start_date: str | date = "2020-01-01",
    end_date: str | date = "2020-12-31",
    seed: int = 42,
    fraud_rate: float = 0.002,
    delimiter: str = "|",
) -> dict[str, Path | int]:
    """Generate normalized customer and transaction CSVs.

    The return value is intentionally simple so notebooks and scripts can print
    or assert generated counts without reparsing the files.
    """
    if customers <= 0:
        raise ValueError("customers must be greater than zero")
    if not 0 <= fraud_rate <= 1:
        raise ValueError("fraud_rate must be between 0 and 1")

    start = parse_date(start_date) if isinstance(start_date, str) else start_date
    end = parse_date(end_date) if isinstance(end_date, str) else end_date
    output_path = Path(output_dir)
    customer_path = output_path / "customers.csv"
    transaction_path = output_path / "transactions.csv"

    customer_rows = generate_customers(customers, seed)
    customer_count = write_csv(customer_path, customer_rows, CUSTOMER_COLUMNS, delimiter)
    transaction_count = write_csv(
        transaction_path,
        transaction_rows(customer_rows, start, end, seed, fraud_rate),
        TRANSACTION_COLUMNS,
        delimiter,
    )

    return {
        "customers_csv": customer_path,
        "transactions_csv": transaction_path,
        "customers": customer_count,
        "transactions": transaction_count,
    }
