# generating-datasets

Reusable scripts for generating synthetic datasets used in demos, tutorials, and sibling projects.

## Retail Dataset Generator

The current generator creates three related retail datasets and can load them into SQLite:

- `customers.csv`
- `inventory.csv`
- `transactions.csv`
- `retail.db`

Transactions reference generated customers, and each transaction stores a JSON array of purchased items from the generated inventory.

## Install

```bash
pip install -r requirements.txt
```

## Generate Data

Use the defaults:

```bash
python main.py
```

Generate a smaller demo dataset:

```bash
python main.py --customers 100 --inventory 50 --transactions 1000 --output-dir data/demo
```

Generate only CSV files:

```bash
python main.py --skip-db
```

Use a custom seed for reproducible variants:

```bash
python main.py --seed 123
```

The old positional customer-count style still works:

```bash
python main.py 5000
```

## Files

- `config.py`: defaults, file names, column lists, and retail categories.
- `customers.py`: customer row generation.
- `inventory.py`: product and stock row generation.
- `transactions.py`: transaction/order generation using customers and inventory.
- `db.py`: SQLite schema and CSV import helpers.
- `load_db.py`: load existing CSV files into SQLite.
- `UsingSpark/`: large-scale synthetic data notebook experiments.

## Notes

The checked-in `data/retail.zip` contains a prebuilt SQLite database from an earlier run. The scripts can regenerate fresh CSV and SQLite outputs at any time.


## Security Log Dataset Generator

`security_logs.py` creates synthetic security logs inspired by the benchmarking datasets used in sibling projects.

Generate a dataframe-friendly CSV for Pandas/Polars/DuckDB benchmarks:

```bash
python security_logs.py benchmark --rows 100000 --output data/logs/synthetic_logs.csv
```

Generate Parquet output:

```bash
python security_logs.py benchmark --rows 100000 --output data/logs/synthetic_logs.parquet --format parquet
```

Generate SIEM-style NDJSON with active hosts and attack campaign bursts:

```bash
python security_logs.py siem --days 7 --events-per-day 1000 --output data/logs/siem_logs.ndjson
```

The benchmark dataset includes fields commonly used in performance tests: timestamps, source/destination IPs, ports, protocols, event types, status codes, bytes, response times, countries, device types, session IDs, and risk scores.

## Credit Card Transaction Dataset Generator

`credit_card_transactions` is a cleaned-up, normalized generator based on the Sparkov-style data used by the `card-transactions-analysis` capstone project.

Run a small reusable dataset:

```bash
python -m credit_card_transactions --customers 100 --start-date 2020-01-01 --end-date 2020-01-31 --output-dir data/credit_card_transactions_demo
```

Run a capstone-sized date range with a realistic low fraud rate:

```bash
python -m credit_card_transactions --customers 1010 --start-date 2020-01-01 --end-date 2025-06-25 --fraud-rate 0.002 --output-dir data/credit_card_transactions
```

The generator writes two pipe-delimited files:

- `customers.csv`: customer demographics, location, account fields, and assigned profile.
- `transactions.csv`: transaction facts with `ssn` as the customer join key.

The package directory uses underscores (`credit_card_transactions`) so it can be imported and run with Python tooling. Use hyphens for repository names or external command aliases, not importable module paths.

## Warehouse Operations Dataset Generator

`warehouse_operations.py` creates the warehouse SQLite database used by warehouse assistant demos. It supersedes the older WMS script that lived in `data-wrangling` by keeping the same operational flow while adding normalized warehouse, location, item, inventory, order, shipment, labor, and exception tables.

Generate a small smoke-test database:

```bash
python warehouse_operations.py --items 20 --locations-per-warehouse 10 --orders 50 --exceptions 5 --output data/warehouse_demo.db
```

Generate the larger assistant-style database:

```bash
python warehouse_operations.py --items 2000 --locations-per-warehouse 2000 --orders 10000 --exceptions 500 --output data/warehouse.db
```

## HR Analytics Dataset Generator

`hr_analytics.py` is the canonical reusable generator for HR and employee analytics projects. It folds in the richer workforce model from `employee-analysis` and keeps the older project/sales tutorial tables so downstream repos can share one source of truth.

```bash
python hr_analytics.py --employees 1000 --projects 50 --output-dir data/hr_analytics
```

The generator writes both CSV files and a SQLite database with these related tables:

- `employees`
- `performance_reviews`
- `benefits`
- `training`
- `attendance`
- `sales`
- `projects`
- `project_assignments`

Use `--past-ratio` to control the terminated employee share, `--no-past-employees` for an active-only dataset, and `--as-of-date` to make tenure and termination calculations reproducible.

## Healthcare Readmissions Dataset Generator

`healthcare_readmissions.py` creates the synthetic patient and hospital datasets used by patient readmission analysis projects. It writes `patient_data.csv`, `hospital_data.csv`, and a SQLite database with primary/foreign keys preserved.

Generate a course-project-sized dataset:

```bash
python healthcare_readmissions.py --patients 3500 --hospitals 20 --output-dir data/healthcare_readmissions
```

Generate raw columns only, without notebook-style derived features:

```bash
python healthcare_readmissions.py --patients 3500 --hospitals 20 --no-features --output-dir data/healthcare_readmissions_raw
```

## Transportation Trips Dataset Generator

`transportation_trips.py` creates trip-level transit data for transportation analysis and forecasting demos. It preserves the statistical choices from the transportation dashboard project while making the output path, route count, date range, and seed explicit.

```bash
python transportation_trips.py --days 120 --routes 20 --seed 42 --output data/transportation/transportation_raw_data.csv
```

## People Profiles Dataset Generator

`people_profiles.py` replaces the useful `my-db-gen/generate_people_data.py` idea without depending on the old `pydbgen` fork. It uses Faker directly and writes one reusable person/profile table to CSV and SQLite.

```bash
python people_profiles.py --rows 1000 --output-dir data/people_profiles
```

Generate CSV only:

```bash
python people_profiles.py --rows 1000 --skip-sqlite --output-dir data/people_profiles_csv
```

The output includes fake names, birthdates, ages, SSNs, phone numbers, email addresses, addresses, location fields, job/company fields, employment status, income, education, and marital status. All personally identifying values are synthetic.

## Tabular Synthesizer

`tabular_synthesizer.py` creates synthetic rows from an existing CSV using bootstrap, parametric, or Gaussian-copula sampling. If no input CSV is provided, it uses a small demo dataframe.

```bash
python tabular_synthesizer.py --method bootstrap --rows 500 --output data/tabular_synthetic.csv
```

```bash
python tabular_synthesizer.py --input data/source.csv --method copula --rows 1000 --output data/source_synthetic.csv
```

## Tutorial Datasets

`tutorial_datasets.py` keeps intentionally small teaching examples: a subscription customer dataset with conditional spend logic, and a tiny warehouse event log with stock-before/stock-after relationships.

```bash
python tutorial_datasets.py --customers 1000 --warehouse-days 30 --output-dir data/tutorial
```
