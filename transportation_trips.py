#!/usr/bin/env python3
"""Generate synthetic public-transportation trip data.

This is the reusable source-of-truth version of the sample-data generator from
`transportation-data-analysis`. It preserves the statistical modeling choices
from the dashboard project, but removes Streamlit coupling and makes size,
seed, date range, and output explicit for repeatable reuse.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


VEHICLE_TYPES = ["Bus", "Subway", "Light Rail", "Ferry"]
VEHICLE_TYPE_WEIGHTS = [0.60, 0.20, 0.15, 0.05]
WEATHER_CONDITIONS = ["Clear", "Rain", "Snow", "Fog"]
WEATHER_WEIGHTS = [0.60, 0.25, 0.10, 0.05]
PEAK_HOURS = {7, 8, 9, 17, 18, 19}


def parse_date(value: str) -> date:
    """Parse CLI dates as ISO strings to keep run commands unambiguous."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Date must use YYYY-MM-DD: {value}") from exc


def season_for_date(value: date) -> str:
    month = value.month
    if month in {12, 1, 2}:
        return "Winter"
    if month in {3, 4, 5}:
        return "Spring"
    if month in {6, 7, 8}:
        return "Summer"
    return "Fall"


def route_ids(route_count: int) -> list[str]:
    if route_count <= 0:
        raise ValueError("route_count must be greater than zero")
    return [f"R{i:03d}" for i in range(1, route_count + 1)]


def efficiency_score(df: pd.DataFrame) -> pd.Series:
    """Calculate the same composite efficiency metric used by the dashboard."""
    on_time_score = df["on_time"].astype(int)
    occupancy_score = df["occupancy_rate"]
    revenue_efficiency = df["revenue"] / df["trip_duration_minutes"]
    revenue_efficiency_norm = (revenue_efficiency - revenue_efficiency.min()) / (
        revenue_efficiency.max() - revenue_efficiency.min() + 1e-8
    )
    return 0.4 * on_time_score + 0.3 * occupancy_score + 0.3 * revenue_efficiency_norm


def generate_transportation_trips(
    days: int = 120,
    route_count: int = 20,
    seed: int = 42,
    end_date: date | None = None,
) -> pd.DataFrame:
    """Generate trip-level transportation data.

    The distribution choices mirror the original capstone project:
    Poisson for ridership counts, gamma for positive trip durations,
    exponential for delay tails, and normal noise for small timing variation.
    """
    if days <= 0:
        raise ValueError("days must be greater than zero")

    rng = np.random.default_rng(seed)
    final_day = end_date or date(2026, 5, 15)
    start_day = final_day - timedelta(days=days - 1)
    dates = pd.date_range(start=start_day, end=final_day, freq="D")
    records: list[dict[str, object]] = []

    for current_day in dates:
        current_date = current_day.date()
        for route_id in route_ids(route_count):
            trips_per_day = int(rng.poisson(12))
            route_number = int(route_id[1:])
            if route_number <= max(1, route_count // 2):
                capacity = 80
                frequency_minutes = 15
            else:
                capacity = 50
                frequency_minutes = 30

            for trip_number in range(trips_per_day):
                scheduled_time = datetime.combine(current_date, datetime.min.time()) + timedelta(
                    hours=int(rng.integers(5, 23)),
                    minutes=int(rng.integers(0, 60)),
                )
                duration = float(rng.gamma(2, 15) + 15)

                if rng.random() < 0.25:
                    delay_minutes = float(rng.exponential(8))
                else:
                    delay_minutes = float(max(0, rng.normal(0, 2)))

                ridership_multiplier = 1.3 if scheduled_time.weekday() < 5 else 0.8
                ridership = int(rng.poisson(45) * ridership_multiplier)
                weather = str(rng.choice(WEATHER_CONDITIONS, p=WEATHER_WEIGHTS))
                if weather in {"Rain", "Snow"}:
                    delay_minutes += float(rng.exponential(3))
                    ridership = int(ridership * 0.9)

                vehicle_type = str(rng.choice(VEHICLE_TYPES, p=VEHICLE_TYPE_WEIGHTS))
                ridership = min(ridership, capacity)
                actual_departure = scheduled_time + timedelta(minutes=delay_minutes)

                records.append(
                    {
                        "trip_id": f"{route_id}_{current_date.strftime('%Y%m%d')}_{trip_number:03d}",
                        "route_id": route_id,
                        "date": current_date.isoformat(),
                        "scheduled_departure": scheduled_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "actual_departure": actual_departure.strftime("%Y-%m-%d %H:%M:%S"),
                        "trip_duration_minutes": round(duration, 2),
                        "delay_minutes": round(delay_minutes, 2),
                        "ridership": ridership,
                        "capacity": capacity,
                        "vehicle_type": vehicle_type,
                        "weather_condition": weather,
                        "day_of_week": scheduled_time.strftime("%A"),
                        "hour_of_day": scheduled_time.hour,
                        "frequency_minutes": frequency_minutes,
                        "on_time": delay_minutes <= 5,
                        "occupancy_rate": round(min(ridership / capacity, 1.0), 4),
                        "revenue": round(ridership * float(rng.uniform(2.5, 4.0)), 2),
                        "fuel_cost": round(duration * float(rng.uniform(0.8, 1.2)), 2),
                        "temperature_f": round(float(rng.normal(65, 15)), 2),
                        "route_distance_km": round(float(rng.uniform(8, 45)), 2),
                    }
                )

    df = pd.DataFrame(records)
    df["efficiency_score"] = efficiency_score(df).round(4)
    df["peak_hour"] = df["hour_of_day"].isin(PEAK_HOURS)
    df["season"] = df["date"].map(lambda value: season_for_date(datetime.strptime(value, "%Y-%m-%d").date()))
    return df


def save_csv(df: pd.DataFrame, output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic transportation trip data.")
    parser.add_argument("--days", type=int, default=120, help="Number of historical days to generate.")
    parser.add_argument("--routes", type=int, default=20, help="Number of transit routes.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible data.")
    parser.add_argument("--end-date", type=parse_date, default=date(2026, 5, 15), help="Inclusive final date, YYYY-MM-DD.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/transportation/transportation_raw_data.csv"),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = generate_transportation_trips(
        days=args.days,
        route_count=args.routes,
        seed=args.seed,
        end_date=args.end_date,
    )
    output = save_csv(data, args.output)
    print(f"Transportation trip dataset created: {output}")
    print(f"rows: {len(data):,}")
    print(f"routes: {data['route_id'].nunique():,}")
    print(f"date range: {data['date'].min()} to {data['date'].max()}")


if __name__ == "__main__":
    main()
