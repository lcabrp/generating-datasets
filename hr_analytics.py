#!/usr/bin/env python3
"""Generate a relational HR analytics dataset.

This is the canonical generator for HR/employee analytics examples. It folds in
the richer workforce model from the sibling `employee-analysis` project while
preserving the project and sales tutorial tables from the older data-wrangling
script. Keeping the generator here gives downstream repos one source of truth.
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from faker import Faker


DEFAULT_AS_OF_DATE = date(2026, 5, 15)

DEPARTMENTS = (
    "IT",
    "HR",
    "Marketing",
    "Finance",
    "Sales",
    "Operations",
    "Research",
    "Development",
    "Customer Service",
    "Legal",
    "Administration",
    "Product Management",
    "Quality Assurance",
)

LOCATIONS = {
    "Headquarters": {
        "city": "Chicago",
        "state": "IL",
        "facility_type": "Corporate Office",
        "departments": ("IT", "HR", "Marketing", "Finance", "Legal", "Administration", "Product Management"),
    },
    "West Coast Office": {
        "city": "San Francisco",
        "state": "CA",
        "facility_type": "Regional Office",
        "departments": ("Sales", "Marketing", "IT", "Customer Service"),
    },
    "East Coast Office": {
        "city": "Boston",
        "state": "MA",
        "facility_type": "Regional Office",
        "departments": ("Sales", "Finance", "Customer Service"),
    },
    "Southern Distribution Center": {
        "city": "Atlanta",
        "state": "GA",
        "facility_type": "Distribution Center",
        "departments": ("Operations", "Quality Assurance", "Administration"),
    },
    "Midwest Distribution Center": {
        "city": "Columbus",
        "state": "OH",
        "facility_type": "Distribution Center",
        "departments": ("Operations", "Quality Assurance", "Administration"),
    },
    "Research Facility": {
        "city": "Austin",
        "state": "TX",
        "facility_type": "R&D Center",
        "departments": ("Research", "Development", "Quality Assurance"),
    },
    "Remote": {
        "city": "Various",
        "state": "Various",
        "facility_type": "Remote",
        "departments": ("IT", "Development", "Sales", "Customer Service"),
    },
}

EMPLOYMENT_TYPE_WEIGHTS = {
    "Full-time": 0.65,
    "Part-time": 0.15,
    "Contract": 0.10,
    "Seasonal": 0.05,
    "Temporary": 0.03,
    "Intern": 0.02,
}

ROLES = {
    "IT": ("Software Engineer", "System Administrator", "Data Scientist", "IT Support", "Network Engineer", "DevOps Engineer", "Security Analyst"),
    "HR": ("HR Manager", "Recruiter", "Benefits Specialist", "HR Coordinator", "Talent Development Specialist", "Employee Relations Manager"),
    "Marketing": ("Marketing Manager", "Digital Marketing Specialist", "Content Creator", "Brand Manager", "SEO Specialist", "Social Media Manager"),
    "Finance": ("Financial Analyst", "Accountant", "Controller", "Payroll Specialist", "Tax Specialist", "Auditor"),
    "Sales": ("Sales Representative", "Account Manager", "Sales Manager", "Business Development", "Sales Analyst"),
    "Operations": ("Operations Manager", "Supply Chain Analyst", "Logistics Coordinator", "Process Improvement Specialist"),
    "Research": ("Research Scientist", "Research Analyst", "Lab Technician", "Research Director"),
    "Development": ("Product Developer", "R&D Engineer", "Development Manager"),
    "Customer Service": ("Customer Service Representative", "Customer Success Manager", "Support Specialist"),
    "Legal": ("Legal Counsel", "Compliance Officer", "Contract Specialist", "Paralegal"),
    "Administration": ("Administrative Assistant", "Office Manager", "Executive Assistant", "Receptionist"),
    "Product Management": ("Product Manager", "Product Owner", "Product Analyst", "UX Researcher"),
    "Quality Assurance": ("QA Engineer", "QA Analyst", "Test Engineer", "Quality Manager"),
}

EDUCATION_LEVELS = ("High School", "Associate's", "Bachelor's", "Master's", "PhD", "Professional Certification")
TRAINING_NAMES = (
    "Leadership Development",
    "Project Management",
    "Communication Skills",
    "Technical Skills",
    "Software Training",
    "Compliance Training",
    "Safety Training",
    "Customer Service",
    "Sales Training",
    "Diversity and Inclusion",
    "Data Analysis",
    "Business Ethics",
    "Process Improvement",
    "Risk Management",
)
TRAINING_TYPES = (
    "Online Course",
    "Workshop",
    "Seminar",
    "Conference",
    "Certification Program",
    "Webinar",
    "Instructor-Led Training",
)
TRAINING_STATUSES = ("Completed", "In Progress", "Not Started", "Cancelled")
TRAINING_PROVIDERS = (
    "Internal HR Department",
    "External Consultant",
    "Online Platform",
    "Professional Association",
    "University",
    "Training Company",
)
PRODUCTS = ("Product A", "Product B", "Product C", "Service X")


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def split_employee_counts(employee_count: int, include_past: bool, past_ratio: float) -> tuple[int, int]:
    if not include_past:
        return employee_count, 0
    current_count = int(employee_count * (1 - past_ratio))
    if employee_count > 1 and current_count == 0:
        current_count = 1
    return current_count, employee_count - current_count


def compatible_location(rng: random.Random, department: str) -> tuple[str, dict[str, Any]]:
    names = [name for name, data in LOCATIONS.items() if department in data["departments"]]
    location_name = rng.choice(names)
    return location_name, LOCATIONS[location_name]


def calculate_salary(rng: random.Random, role: str, department: str, location_data: dict[str, Any], years_experience: int) -> int:
    base_salary = {
        "Manager": 80_000,
        "Director": 120_000,
        "Specialist": 65_000,
        "Analyst": 60_000,
        "Engineer": 75_000,
        "Assistant": 45_000,
        "Coordinator": 50_000,
        "Representative": 45_000,
    }
    if location_data["facility_type"] == "Distribution Center":
        # Distribution center roles intentionally use lower local baselines so
        # location analyses do not compare warehouse and corporate jobs as if
        # they shared the same labor market.
        base_salary = {
            "Manager": 65_000,
            "Supervisor": 45_000,
            "Specialist": 30_000,
            "Analyst": 28_000,
            "Engineer": 32_000,
            "Assistant": 25_000,
            "Coordinator": 27_000,
            "Representative": 25_000,
            "Receptionist": 22_000,
            "Quality": 50_000,
        }

    salary_base = 25_000 if location_data["facility_type"] == "Distribution Center" else 50_000
    for keyword, value in base_salary.items():
        if keyword in role:
            salary_base = value
            break

    department_multiplier = {
        "IT": 1.2,
        "Finance": 1.15,
        "Legal": 1.25,
        "Sales": 1.1,
        "HR": 0.95,
        "Administration": 0.9,
        "Operations": 0.85 if location_data["facility_type"] == "Distribution Center" else 1.0,
        "Quality Assurance": 0.9 if location_data["facility_type"] == "Distribution Center" else 1.0,
    }.get(department, 1.0)
    experience_factor = 1.0 + (min(years_experience, 20) / 20)
    random_factor = rng.uniform(0.85, 1.15)
    salary = int(salary_base * department_multiplier * experience_factor * random_factor / 1000) * 1000

    cost_of_living = {
        "San Francisco": 1.3,
        "Boston": 1.2,
        "Chicago": 1.1,
        "Austin": 1.05,
        "Atlanta": 0.95,
        "Columbus": 0.9,
        "Various": 1.0,
    }.get(location_data["city"], 1.0)
    salary = int(max(30_000, min(salary, 250_000)) * cost_of_living)
    return salary


def adjust_salary_for_type(salary: int, employment_type: str) -> int:
    type_factor = {
        "Full-time": 1.0,
        "Part-time": 0.6,
        "Contract": 1.2,
        "Seasonal": 0.9,
        "Temporary": 0.9,
        "Intern": 0.4,
    }.get(employment_type, 1.0)
    return int(salary * type_factor)


def create_employee_record(
    fake: Faker,
    rng: random.Random,
    employee_id: int,
    as_of_date: date,
    employment_status: str,
) -> dict[str, Any]:
    department = rng.choice(DEPARTMENTS)
    location_name, location_data = compatible_location(rng, department)
    city = fake.city() if location_name == "Remote" else location_data["city"]
    state = fake.state() if location_name == "Remote" else location_data["state"]
    employment_type = weighted_choice(rng, EMPLOYMENT_TYPE_WEIGHTS)

    if location_data["facility_type"] == "Distribution Center" and rng.random() < 0.2:
        employment_type = "Seasonal"
    if location_name == "Remote" and employment_type in {"Seasonal", "Temporary"}:
        employment_type = rng.choice(("Full-time", "Part-time", "Contract"))

    role = rng.choice(ROLES[department])
    hire_end = as_of_date if employment_status == "Active" else as_of_date - timedelta(days=365)
    hire_date = fake.date_between(start_date="-20y", end_date=hire_end)
    birth_date = fake.date_of_birth(minimum_age=22, maximum_age=65)

    age = as_of_date.year - birth_date.year
    min_experience = max(0, as_of_date.year - hire_date.year)
    max_experience = max(min_experience, min(40, age - 18))
    years_experience = rng.randint(min_experience, max_experience)
    salary = adjust_salary_for_type(calculate_salary(rng, role, department, location_data, years_experience), employment_type)

    record = {
        "id": employee_id,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "birth_date": birth_date,
        "gender": rng.choice(("Male", "Female", "Non-binary")),
        "email": fake.unique.email(),
        "phone": fake.phone_number(),
        "address": fake.street_address().replace("\n", " "),
        "city": city,
        "state": state,
        "zipcode": fake.zipcode(),
        "department": department,
        "role": role,
        "location_name": location_name,
        "facility_type": location_data["facility_type"],
        "employment_type": employment_type,
        "employment_status": employment_status,
        "hire_date": hire_date,
        "years_experience": years_experience,
        "education": rng.choice(EDUCATION_LEVELS),
        "salary": salary,
        "manager_id": None,
        "performance_score": rng.choices((1, 2, 3, 4, 5), weights=(0.05, 0.1, 0.5, 0.25, 0.1), k=1)[0],
        "termination_date": None,
        "termination_reason": None,
        "tenure_years": round((as_of_date - hire_date).days / 365.25, 2),
        "exit_interview_score": None,
        "exit_interview_feedback": None,
    }

    if employment_status == "Terminated":
        min_tenure_days = 90
        max_tenure_days = max(min_tenure_days, (as_of_date - hire_date).days)
        tenure_days = rng.randint(min_tenure_days, max_tenure_days)
        termination_reasons = (
            "Resignation - Better Opportunity",
            "Resignation - Work-Life Balance",
            "Resignation - Relocation",
            "Resignation - Career Change",
            "Resignation - Compensation",
            "Resignation - Management Issues",
            "Layoff - Restructuring",
            "Layoff - Performance",
            "Retirement",
            "Contract End",
            "Mutual Agreement",
        )
        reason_weights = (0.25, 0.15, 0.1, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05)
        reason = rng.choices(termination_reasons, weights=reason_weights, k=1)[0]
        if employment_type in {"Seasonal", "Temporary", "Contract", "Intern"} and rng.random() < 0.7:
            reason = "Contract End"
        record["termination_date"] = hire_date + timedelta(days=tenure_days)
        record["termination_reason"] = reason
        record["tenure_years"] = round(tenure_days / 365.25, 2)
        if rng.random() < 0.7:
            record["exit_interview_score"] = rng.randint(1, 5)
            record["exit_interview_feedback"] = fake.paragraph(nb_sentences=2)

    return record


def create_employees(
    fake: Faker,
    rng: random.Random,
    employee_count: int,
    as_of_date: date,
    include_past: bool,
    past_ratio: float,
) -> pd.DataFrame:
    current_count, past_count = split_employee_counts(employee_count, include_past, past_ratio)
    rows = [
        create_employee_record(fake, rng, employee_id, as_of_date, "Active")
        for employee_id in range(1, current_count + 1)
    ]
    rows.extend(
        create_employee_record(fake, rng, employee_id, as_of_date, "Terminated")
        for employee_id in range(current_count + 1, current_count + past_count + 1)
    )
    employees = pd.DataFrame(rows)
    employee_ids = employees["id"].tolist()
    manager_pool = employees.loc[employees["employment_status"] == "Active", "id"].tolist() or employee_ids
    for index, row in employees.iterrows():
        possible_managers = [manager_id for manager_id in manager_pool if manager_id != row["id"]]
        if possible_managers and row["id"] > min(10, employee_count):
            employees.at[index, "manager_id"] = rng.choice(possible_managers)
    return employees


def create_performance_reviews(employees: pd.DataFrame, rng: random.Random, as_of_date: date) -> pd.DataFrame:
    rows = []
    employee_ids = employees["id"].tolist()
    for _, employee in employees.iterrows():
        hire_date = pd.Timestamp(employee["hire_date"]).date()
        end_date = pd.Timestamp(employee["termination_date"]).date() if pd.notna(employee["termination_date"]) else as_of_date
        years_employed = max(0, int((end_date - hire_date).days / 365.25))
        for year in range(min(years_employed + 1, 5)):
            base_performance = employee["performance_score"]
            technical_score = round(max(1, min(5, base_performance + rng.uniform(-0.8, 0.8))))
            communication_base = base_performance + rng.uniform(-0.6, 0.6)
            if employee.get("department") in {"IT", "Development", "Research"}:
                communication_base -= rng.uniform(0, 0.3)
            communication_score = round(max(1, min(5, communication_base)))
            teamwork_score = round(max(1, min(5, ((communication_score + base_performance) / 2) + rng.uniform(-0.7, 0.7))))
            initiative_base = base_performance + rng.uniform(-1.0, 1.0)
            if "Manager" in employee.get("role", "") or "Director" in employee.get("role", ""):
                initiative_base += rng.uniform(0, 0.5)
            initiative_score = round(max(1, min(5, initiative_base)))
            overall_score = round((technical_score + communication_score + teamwork_score + initiative_score) / 4)
            overall_score = max(1, min(5, overall_score))
            bonus_pct = {5: (0.10, 0.20), 4: (0.05, 0.15), 3: (0.02, 0.08), 2: (0.01, 0.03), 1: (0.0, 0.0)}[overall_score]
            reviewer_candidates = [employee_id for employee_id in employee_ids if employee_id != employee["id"]]
            reviewer_id = employee["manager_id"] if pd.notna(employee["manager_id"]) else rng.choice(reviewer_candidates)
            rows.append(
                {
                    "employee_id": employee["id"],
                    "review_date": hire_date + pd.DateOffset(years=year + 1),
                    "reviewer_id": reviewer_id,
                    "technical_score": technical_score,
                    "communication_score": communication_score,
                    "teamwork_score": teamwork_score,
                    "initiative_score": initiative_score,
                    "overall_score": overall_score,
                    "bonus_amount": int(employee["salary"] * rng.uniform(*bonus_pct)),
                    "promotion_recommended": rng.random() < {5: 0.7, 4: 0.3, 3: 0.1, 2: 0.02, 1: 0.0}[overall_score],
                }
            )
    return pd.DataFrame(rows)


def create_training(fake: Faker, rng: random.Random, employees: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, employee in employees.iterrows():
        for _ in range(rng.randint(1, 8)):
            start_date = fake.date_between(start_date="-3y", end_date="today")
            status = rng.choice(TRAINING_STATUSES)
            completion_date = None
            score = None
            if status == "Completed":
                completion_date = start_date + timedelta(days=rng.randint(1, 90))
                score = round(rng.uniform(60, 100), 1)
            rows.append(
                {
                    "employee_id": employee["id"],
                    "training_name": rng.choice(TRAINING_NAMES),
                    "training_type": rng.choice(TRAINING_TYPES),
                    "start_date": start_date,
                    "completion_date": completion_date,
                    "status": status,
                    "score": score,
                    "certification": rng.random() < 0.3,
                    "provider": rng.choice(TRAINING_PROVIDERS),
                    "cost": round(rng.uniform(0, 2_000), 2),
                    "training_cost": None,
                    "department_specific": rng.random() < 0.7,
                }
            )
            rows[-1]["training_cost"] = rows[-1]["cost"]
    return pd.DataFrame(rows)


def create_benefits(rng: random.Random, employees: pd.DataFrame) -> pd.DataFrame:
    rows = []
    health_cost = {
        "Basic Health": 5_000,
        "Premium Health": 8_000,
        "Family Health": 12_000,
        "High Deductible Health Plan": 3_000,
        "Health Savings Account": 4_000,
        "No Coverage": 0,
    }
    dental_cost = {"Basic Dental": 500, "Premium Dental": 1_000, "Family Dental": 1_500, "No Coverage": 0}
    vision_cost = {"Basic Vision": 300, "Premium Vision": 600, "Family Vision": 900, "No Coverage": 0}
    for _, employee in employees.iterrows():
        if employee["employment_status"] == "Terminated" or employee["employment_type"] in {"Intern", "Temporary"}:
            continue
        is_full_time = employee["employment_type"] == "Full-time"
        is_part_time = employee["employment_type"] == "Part-time"
        health_weights = (0.2, 0.3, 0.3, 0.1, 0.05, 0.05) if is_full_time else (0.3, 0.1, 0.05, 0.2, 0.05, 0.3)
        if not is_full_time and not is_part_time:
            health_weights = (0.2, 0.1, 0.05, 0.15, 0.0, 0.5)
        health_plan = rng.choices(tuple(health_cost), weights=health_weights, k=1)[0]
        has_premium = "Premium" in health_plan
        has_health = health_plan != "No Coverage"
        dental_weights = (0.1, 0.6, 0.2, 0.1) if has_premium else (0.4, 0.2, 0.1, 0.3) if has_health else (0.2, 0.1, 0.0, 0.7)
        vision_weights = dental_weights
        dental_plan = rng.choices(tuple(dental_cost), weights=dental_weights, k=1)[0]
        vision_plan = rng.choices(tuple(vision_cost), weights=vision_weights, k=1)[0]
        retirement_plan = rng.choices(
            ("401(k)", "Roth 401(k)", "Pension", "No Plan"),
            weights=(0.5, 0.3, 0.1, 0.1) if is_full_time else (0.3, 0.2, 0.0, 0.5) if is_part_time else (0.1, 0.1, 0.0, 0.8),
            k=1,
        )[0]
        contribution_pct = 0.0
        company_match = 0.0
        if retirement_plan != "No Plan":
            salary_factor = min(1.0, employee["salary"] / 100_000)
            contribution_pct = round(rng.uniform(1, 10) * (0.5 + 0.5 * salary_factor), 1)
            company_match = rng.choice((3.0, 4.0, 5.0, 6.0))
        years_of_service = datetime.now().year - pd.to_datetime(employee["hire_date"]).year
        pto_days = 0
        if is_full_time:
            pto_days = 20 if "Manager" in employee["role"] or "Director" in employee["role"] else 15
            pto_days += 10 if years_of_service >= 10 else 5 if years_of_service >= 5 else 2 if years_of_service >= 2 else 0
        elif is_part_time:
            pto_days = int(10 + (years_of_service // 2))
        has_fsa = is_full_time and rng.random() < 0.4
        fsa_contribution = round(rng.uniform(500, 2_750)) if has_fsa else 0
        benefits_cost = round(
            health_cost[health_plan]
            + dental_cost[dental_plan]
            + vision_cost[vision_plan]
            + (min(company_match, contribution_pct) * employee["salary"] / 100)
            + (fsa_contribution * 0.3 if has_fsa else 0)
        )
        rows.append(
            {
                "employee_id": employee["id"],
                "health_plan": health_plan,
                "dental_plan": dental_plan,
                "vision_plan": vision_plan,
                "retirement_plan": retirement_plan,
                "retirement_contribution_pct": contribution_pct,
                "company_match_pct": company_match,
                "pto_days": pto_days,
                "sick_leave_days": 10 if is_full_time else 5 if is_part_time else 0,
                "life_insurance_coverage": int(employee["salary"] * rng.choice((1.0, 1.5, 2.0))) if is_full_time else 0,
                "has_fsa": has_fsa,
                "fsa_contribution": fsa_contribution,
                "benefits_cost_annual": benefits_cost,
                "benefits_cost": benefits_cost,
            }
        )
    return pd.DataFrame(rows)


def create_attendance(rng: random.Random, employees: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    rows = []
    start = as_of_date - timedelta(days=365)
    for _, employee in employees.iterrows():
        if employee["employment_status"] == "Terminated":
            continue
        hire_date = pd.Timestamp(employee["hire_date"]).date()
        employee_start = max(start, hire_date)
        if employee_start > as_of_date:
            continue
        events = rng.randint(3, 10) if employee["employment_type"] == "Full-time" else rng.randint(2, 6) if employee["employment_type"] == "Part-time" else rng.randint(0, 3)
        days_available = max(1, (as_of_date - employee_start).days)
        for _ in range(events):
            event_date = employee_start + timedelta(days=rng.randint(0, days_available))
            rows.append(
                {
                    "employee_id": employee["id"],
                    "date": event_date,
                    "type": rng.choices(("Vacation", "Sick Leave", "Personal Day", "Family Leave", "Bereavement"), weights=(0.6, 0.25, 0.1, 0.03, 0.02), k=1)[0],
                    "hours": rng.choice((4, 8)),
                    "approved": rng.random() < 0.95,
                }
            )
    return pd.DataFrame(rows)


def create_sales(fake: Faker, rng: random.Random, employees: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sales_employees = employees[(employees["department"].isin(("Sales", "Marketing"))) & (employees["employment_status"] == "Active")]
    for _, employee in sales_employees.iterrows():
        for _ in range(rng.randint(1, 20)):
            rows.append(
                {
                    "employee_id": employee["id"],
                    "sale_date": fake.date_between(start_date="-1y", end_date="today"),
                    "sale_amount": rng.randint(1_000, 50_000),
                    "customer": fake.company(),
                    "product": rng.choice(PRODUCTS),
                }
            )
    return pd.DataFrame(rows)


def create_projects(fake: Faker, rng: random.Random, employees: pd.DataFrame, project_count: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    projects = [
        {
            "project_id": project_id,
            "project_name": f"Project {fake.word().capitalize()}",
            "start_date": fake.date_between(start_date="-2y", end_date="-6m"),
            "end_date": fake.date_between(start_date="-6m", end_date="+6m"),
            "budget": rng.randint(10_000, 1_000_000),
        }
        for project_id in range(1, project_count + 1)
    ]
    project_ids = [project["project_id"] for project in projects]
    assignments = []
    for _, employee in employees[employees["employment_status"] == "Active"].iterrows():
        for _ in range(rng.randint(1, 3)):
            assignments.append(
                {
                    "employee_id": employee["id"],
                    "project_id": rng.choice(project_ids),
                    "assignment_role": rng.choice(("Lead", "Member", "Consultant")),
                    "hours_allocated": rng.randint(5, 40),
                }
            )
    return pd.DataFrame(projects), pd.DataFrame(assignments)


def add_review_summary(employees: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    if reviews.empty:
        return employees
    summary = (
        reviews.groupby("employee_id")
        .agg(
            avg_technical_score=("technical_score", "mean"),
            avg_communication_score=("communication_score", "mean"),
            avg_teamwork_score=("teamwork_score", "mean"),
            avg_initiative_score=("initiative_score", "mean"),
            avg_overall_score=("overall_score", "mean"),
            total_bonus_amount=("bonus_amount", "sum"),
        )
        .reset_index()
    )
    # Denormalized review metrics help beginner notebooks while the detailed
    # review table remains available for relational joins.
    return employees.merge(summary, how="left", left_on="id", right_on="employee_id").drop(columns=["employee_id"])


def normalize_for_storage(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[column]):
            out[column] = out[column].dt.strftime("%Y-%m-%d")
        elif out[column].dtype == "object":
            out[column] = out[column].map(
                lambda value: value.strftime("%Y-%m-%d")
                if isinstance(value, (date, datetime, pd.Timestamp))
                else value
            )
    return out


def write_outputs(output_dir: Path, tables: dict[str, pd.DataFrame], sqlite_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_tables = {name: normalize_for_storage(df) for name, df in tables.items()}
    for table_name, df in normalized_tables.items():
        df.to_csv(output_dir / f"{table_name}.csv", index=False)
    db_path = output_dir / sqlite_name
    with sqlite3.connect(db_path) as conn:
        for table_name, df in normalized_tables.items():
            df.to_sql(table_name, conn, if_exists="replace", index=False)
    return db_path


def generate_dataset(
    output_dir: str | Path = "data/hr_analytics",
    employees: int = 1_000,
    projects: int = 50,
    seed: int = 42,
    sqlite_name: str = "hr_analytics.db",
    include_past_employees: bool = True,
    past_employee_ratio: float = 0.3,
    as_of_date: date = DEFAULT_AS_OF_DATE,
) -> dict[str, int | Path]:
    if employees <= 1:
        raise ValueError("employees must be greater than 1 so reviewer relationships can be generated")
    if projects <= 0:
        raise ValueError("projects must be greater than zero")
    if not 0 <= past_employee_ratio <= 1:
        raise ValueError("past_employee_ratio must be between 0 and 1")

    fake = Faker("en_US")
    Faker.seed(seed)
    fake.seed_instance(seed)
    fake.unique.clear()
    rng = random.Random(seed)

    employees_df = create_employees(fake, rng, employees, as_of_date, include_past_employees, past_employee_ratio)
    performance_df = create_performance_reviews(employees_df, rng, as_of_date)
    benefits_df = create_benefits(rng, employees_df)
    training_df = create_training(fake, rng, employees_df)
    attendance_df = create_attendance(rng, employees_df, as_of_date)
    sales_df = create_sales(fake, rng, employees_df)
    projects_df, assignments_df = create_projects(fake, rng, employees_df, projects)
    employees_df = add_review_summary(employees_df, performance_df)

    tables = {
        "employees": employees_df,
        "performance_reviews": performance_df,
        "benefits": benefits_df,
        "training": training_df,
        "attendance": attendance_df,
        "sales": sales_df,
        "projects": projects_df,
        "project_assignments": assignments_df,
    }
    db_path = write_outputs(Path(output_dir), tables, sqlite_name)
    result = {table_name: len(df) for table_name, df in tables.items()}
    result["database"] = db_path
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate HR analytics CSV files and SQLite database.")
    parser.add_argument("--employees", type=int, default=1_000, help="Total number of employees to generate.")
    parser.add_argument("--projects", type=int, default=50, help="Number of project records to generate.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/hr_analytics"), help="Output directory.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    parser.add_argument("--sqlite-name", default="hr_analytics.db", help="SQLite database filename.")
    parser.add_argument("--past-ratio", type=float, default=0.3, help="Share of employees marked as terminated.")
    parser.add_argument("--no-past-employees", action="store_true", help="Generate only active employees.")
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=DEFAULT_AS_OF_DATE, help="Anchor date in YYYY-MM-DD format.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_dataset(
        output_dir=args.output_dir,
        employees=args.employees,
        projects=args.projects,
        seed=args.seed,
        sqlite_name=args.sqlite_name,
        include_past_employees=not args.no_past_employees,
        past_employee_ratio=args.past_ratio,
        as_of_date=args.as_of_date,
    )
    print(f"HR analytics dataset created in {args.output_dir}")
    for table_name, count in result.items():
        if table_name == "database":
            print(f"database: {count}")
        else:
            print(f"{table_name}: {count:,}")


if __name__ == "__main__":
    main()
