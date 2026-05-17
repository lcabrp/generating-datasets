#!/usr/bin/env python3
"""Generate synthetic patient readmission and hospital datasets.

This is the reusable source-of-truth version of the generator from the
`patient-analysis` course project. It keeps that project's useful clinical
patterns, fixes the hospital-ID coupling bug, and can optionally persist the
feature-engineered columns that the notebook originally created later.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_PATIENTS = 3_500
DEFAULT_HOSPITALS = 20
MAX_HOSPITALS = 50
DEFAULT_SEED = 42

DIAGNOSIS_TREATMENTS = {
    "Diabetes": ["Insulin", "Metformin", "Lifestyle Changes"],
    "Heart Failure": ["ACE Inhibitors", "Beta Blockers", "Diuretics"],
    "Pneumonia": ["Antibiotics", "Respiratory Therapy", "Oxygen"],
    "COPD": ["Bronchodilators", "Steroids", "Oxygen Therapy"],
    "Stroke": ["Thrombolytics", "Anticoagulants", "Rehabilitation"],
    "Kidney Disease": ["Dialysis", "Medication", "Dietary Changes"],
    "Cancer": ["Chemotherapy", "Radiation", "Surgery"],
    "Hypertension": ["ACE Inhibitors", "Diuretics", "Beta Blockers"],
    "Mental Health": ["Psychotherapy", "Antidepressants", "Mood Stabilizers"],
    "Surgery": ["Laparoscopic", "Open Surgery", "Minimally Invasive"],
    "Infection": ["Antibiotics", "Antiviral", "Supportive Care"],
    "Fracture": ["Cast", "Surgery", "Physical Therapy"],
    "Burn": ["Wound Care", "Skin Grafts", "Pain Management"],
    "Obesity": ["Diet Counseling", "Bariatric Surgery", "Exercise Program"],
    "Injury": ["Emergency Care", "Surgery", "Rehabilitation"],
    "Rehabilitation": ["Physical Therapy", "Occupational Therapy", "Speech Therapy"],
}

HOSPITAL_NAMES = [
    "Memorial Hospital",
    "University Medical Center",
    "Community Hospital",
    "Regional Medical Center",
    "General Hospital",
    "St. Mary's Hospital",
    "Mercy Medical Center",
    "County Hospital",
    "Metropolitan Hospital",
    "Sacred Heart Hospital",
    "Providence Hospital",
    "Hope Medical Center",
    "Valley Hospital",
    "Riverside Medical Center",
    "Central Hospital",
    "Highland Hospital",
    "Lakeside Medical Center",
    "Summit Hospital",
    "Oakwood Hospital",
    "Pinecrest Medical Center",
    "Northside Hospital",
    "Southside Medical Center",
    "Eastside Hospital",
    "Westside Medical Center",
    "City General Hospital",
    "Suburban Medical Center",
    "Downtown Hospital",
    "Uptown Medical Center",
    "Midtown Hospital",
    "Crossroads Medical Center",
    "Parkview Hospital",
    "Hillcrest Medical Center",
    "Greenwood Hospital",
    "Fairview Medical Center",
    "Sunset Hospital",
    "Sunrise Medical Center",
    "Mountain View Hospital",
    "Ocean View Medical Center",
    "Forest Hills Hospital",
    "Garden City Medical Center",
    "Spring Valley Hospital",
    "Winter Park Medical Center",
    "Autumn Ridge Hospital",
    "Summer Heights Medical Center",
    "Crystal Lake Hospital",
    "Golden Gate Medical Center",
    "Silver Creek Hospital",
    "Diamond Valley Medical Center",
    "Emerald City Hospital",
    "Ruby Ridge Medical Center",
]

SPECIALTIES = [
    "Cardiology",
    "Oncology",
    "Neurology",
    "Orthopedics",
    "Pediatrics",
    "Geriatrics",
    "Pulmonology",
    "Gastroenterology",
    "Endocrinology",
    "Psychiatry",
    "Emergency Medicine",
    "Surgery",
    "Infectious Disease",
    "Trauma Care",
    "Burn Unit",
    "Bariatric Surgery",
    "Rehabilitation",
    "Physical Therapy",
    "Mental Health",
    "Pain Management",
]


def age_group(age: int) -> str:
    if age < 30:
        return "Young Adult (18-29)"
    if age < 50:
        return "Middle Age (30-49)"
    if age < 65:
        return "Older Adult (50-64)"
    return "Senior (65+)"


def los_category(length_of_stay: int) -> str:
    if length_of_stay <= 2:
        return "Short (1-2 days)"
    if length_of_stay <= 5:
        return "Medium (3-5 days)"
    if length_of_stay <= 10:
        return "Long (6-10 days)"
    return "Extended (11+ days)"


def readmission_risk_score(row: pd.Series) -> int:
    score = 0
    if row["age"] > 70:
        score += 2
    elif row["age"] > 60:
        score += 1

    if row["length_of_stay"] > 10:
        score += 3
    elif row["length_of_stay"] > 5:
        score += 2
    elif row["length_of_stay"] > 2:
        score += 1

    high_risk = {"Heart Failure", "COPD", "Kidney Disease", "Cancer", "Stroke", "Burn", "Surgery"}
    if row["diagnosis"] in high_risk:
        score += 2
    if row["insurance_type"] in {"Medicaid", "Uninsured"}:
        score += 1
    return min(score, 10)


def generate_hospitals(hospital_count: int = DEFAULT_HOSPITALS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    if hospital_count <= 0:
        raise ValueError("hospital_count must be greater than zero")
    if hospital_count > MAX_HOSPITALS:
        raise ValueError(f"hospital_count must be {MAX_HOSPITALS} or fewer")

    rng = np.random.default_rng(seed)
    hospital_ids = [f"H{i:03d}" for i in range(1, hospital_count + 1)]
    hospital_types = rng.choice(["Urban", "Suburban", "Rural"], size=hospital_count, p=[0.5, 0.3, 0.2])
    bed_counts = []
    for hospital_type in hospital_types:
        if hospital_type == "Urban":
            bed_counts.append(int(rng.integers(300, 800)))
        elif hospital_type == "Suburban":
            bed_counts.append(int(rng.integers(150, 400)))
        else:
            bed_counts.append(int(rng.integers(50, 200)))

    specialties = []
    for _ in range(hospital_count):
        count = int(rng.integers(3, 8))
        specialties.append(", ".join(rng.choice(SPECIALTIES, size=count, replace=False)))

    return pd.DataFrame(
        {
            "hospital_id": hospital_ids,
            "hospital_name": rng.choice(HOSPITAL_NAMES, size=hospital_count, replace=False),
            "region": rng.choice(["Northeast", "Southeast", "Midwest", "Southwest", "West"], size=hospital_count),
            "hospital_type": hospital_types,
            "bed_count": bed_counts,
            "staff_count": [int(beds * rng.uniform(3.5, 5.5)) for beds in bed_counts],
            "is_teaching_hospital": rng.choice([1, 0], size=hospital_count, p=[0.3, 0.7]),
            "quality_score": np.clip(rng.normal(3.5, 0.8, hospital_count), 1, 5).round(1),
            "specialties": specialties,
        }
    )


def generate_patients(
    patient_count: int = DEFAULT_PATIENTS,
    hospital_ids: list[str] | None = None,
    seed: int = DEFAULT_SEED,
    as_of_date: date = date(2026, 5, 15),
    readmission_rate: float = 0.08,
) -> pd.DataFrame:
    if patient_count <= 0:
        raise ValueError("patient_count must be greater than zero")
    if not 0 <= readmission_rate <= 1:
        raise ValueError("readmission_rate must be between 0 and 1")

    rng = np.random.default_rng(seed + 1)
    if hospital_ids is None:
        hospital_ids = [f"H{i:03d}" for i in range(1, DEFAULT_HOSPITALS + 1)]
    if not hospital_ids:
        raise ValueError("hospital_ids must contain at least one hospital")

    diagnoses = rng.choice(list(DIAGNOSIS_TREATMENTS), size=patient_count)
    treatments = [rng.choice(DIAGNOSIS_TREATMENTS[diagnosis]) for diagnosis in diagnoses]
    length_of_stay = np.clip(rng.lognormal(1.5, 0.5, patient_count).astype(int), 1, 30)

    discharge_dates = []
    admission_dates = []
    base_datetime = datetime.combine(as_of_date, datetime.min.time()).replace(hour=12)
    for stay in length_of_stay:
        discharge = base_datetime - timedelta(days=int(rng.integers(1, 365)))
        admission = discharge - timedelta(days=int(stay))
        discharge_dates.append(discharge.date().isoformat())
        admission_dates.append(admission.date().isoformat())

    readmitted = rng.choice([1, 0], size=patient_count, p=[readmission_rate, 1 - readmission_rate])
    days_to_readmission = [
        int(rng.integers(1, 31)) if flag == 1 else None
        for flag in readmitted
    ]

    return pd.DataFrame(
        {
            "patient_id": [f"P{i:06d}" for i in range(1, patient_count + 1)],
            "hospital_id": rng.choice(hospital_ids, size=patient_count),
            "age": np.clip(rng.normal(65, 15, patient_count).astype(int), 18, 95),
            "gender": rng.choice(["M", "F"], size=patient_count),
            "diagnosis": diagnoses,
            "treatment": treatments,
            "admission_date": admission_dates,
            "discharge_date": discharge_dates,
            "length_of_stay": length_of_stay,
            "readmitted": readmitted,
            "days_to_readmission": days_to_readmission,
            "insurance_type": rng.choice(
                ["Medicare", "Medicaid", "Private", "Uninsured"],
                size=patient_count,
                p=[0.45, 0.25, 0.25, 0.05],
            ),
        }
    )


def add_readmission_features(patients: pd.DataFrame) -> pd.DataFrame:
    """Add the derived columns used by the original analysis notebook."""
    out = patients.copy()
    out["age_group"] = out["age"].map(age_group)
    out["los_category"] = out["length_of_stay"].map(los_category)
    # Keep this row-wise calculation explicit; the scoring rules are business
    # logic that future reviewers should be able to read without indirection.
    out["risk_score"] = out.apply(readmission_risk_score, axis=1)
    return out


def create_schema(conn: sqlite3.Connection, include_features: bool = True) -> None:
    feature_columns = ""
    if include_features:
        feature_columns = """
            age_group TEXT,
            los_category TEXT,
            risk_score INTEGER,
        """

    conn.executescript(
        f"""
        PRAGMA foreign_keys = ON;
        DROP TABLE IF EXISTS patients;
        DROP TABLE IF EXISTS hospitals;

        CREATE TABLE hospitals (
            hospital_id TEXT PRIMARY KEY,
            hospital_name TEXT,
            region TEXT,
            hospital_type TEXT,
            bed_count INTEGER,
            staff_count INTEGER,
            is_teaching_hospital INTEGER,
            quality_score REAL,
            specialties TEXT
        );

        CREATE TABLE patients (
            patient_id TEXT PRIMARY KEY,
            hospital_id TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            diagnosis TEXT,
            treatment TEXT,
            admission_date TEXT,
            discharge_date TEXT,
            length_of_stay INTEGER,
            readmitted INTEGER,
            days_to_readmission INTEGER,
            insurance_type TEXT,
            {feature_columns}
            FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
        );

        CREATE INDEX idx_patients_hospital_id ON patients(hospital_id);
        CREATE INDEX idx_patients_readmitted ON patients(readmitted);
        CREATE INDEX idx_patients_diagnosis ON patients(diagnosis);
        """
    )


def write_sqlite(db_path: Path, patients: pd.DataFrame, hospitals: pd.DataFrame, include_features: bool) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        create_schema(conn, include_features=include_features)
        # Use append after explicit schema creation. `replace` would discard
        # primary keys, foreign keys, and indexes, which was the main bug in the
        # project-local helper.
        hospitals.to_sql("hospitals", conn, if_exists="append", index=False)
        patients.to_sql("patients", conn, if_exists="append", index=False)
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"SQLite foreign key violations: {violations}")


def generate_dataset(
    output_dir: str | Path = "data/healthcare_readmissions",
    patients: int = DEFAULT_PATIENTS,
    hospitals: int = DEFAULT_HOSPITALS,
    seed: int = DEFAULT_SEED,
    sqlite_name: str = "healthcare_readmissions.db",
    include_features: bool = True,
    readmission_rate: float = 0.08,
) -> dict[str, int | Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    hospital_df = generate_hospitals(hospitals, seed=seed)
    patient_df = generate_patients(
        patients,
        hospital_ids=hospital_df["hospital_id"].tolist(),
        seed=seed,
        readmission_rate=readmission_rate,
    )
    if include_features:
        patient_df = add_readmission_features(patient_df)

    patient_csv = output_path / "patient_data.csv"
    hospital_csv = output_path / "hospital_data.csv"
    db_path = output_path / sqlite_name
    patient_df.to_csv(patient_csv, index=False)
    hospital_df.to_csv(hospital_csv, index=False)
    write_sqlite(db_path, patient_df, hospital_df, include_features=include_features)

    return {
        "patient_data_csv": patient_csv,
        "hospital_data_csv": hospital_csv,
        "database": db_path,
        "patients": len(patient_df),
        "hospitals": len(hospital_df),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic healthcare readmission datasets.")
    parser.add_argument("--patients", type=int, default=DEFAULT_PATIENTS, help="Number of patient records.")
    parser.add_argument("--hospitals", type=int, default=DEFAULT_HOSPITALS, help="Number of hospital records.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/healthcare_readmissions"), help="Output directory.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for reproducible datasets.")
    parser.add_argument("--sqlite-name", default="healthcare_readmissions.db", help="SQLite database filename.")
    parser.add_argument("--readmission-rate", type=float, default=0.08, help="Approximate readmission probability.")
    parser.add_argument("--no-features", action="store_true", help="Skip age_group, los_category, and risk_score columns.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_dataset(
        output_dir=args.output_dir,
        patients=args.patients,
        hospitals=args.hospitals,
        seed=args.seed,
        sqlite_name=args.sqlite_name,
        include_features=not args.no_features,
        readmission_rate=args.readmission_rate,
    )
    print(f"Healthcare readmissions dataset created in {args.output_dir}")
    print(f"patients: {result['patients']:,} -> {result['patient_data_csv']}")
    print(f"hospitals: {result['hospitals']:,} -> {result['hospital_data_csv']}")
    print(f"database: {result['database']}")


if __name__ == "__main__":
    main()
