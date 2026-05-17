#!/usr/bin/env python3
"""Generate synthetic tabular data from an existing dataframe.

This consolidates the duplicate `SyntheticDataGenerator` examples that used to
live in `data-wrangling`. It keeps the tutorial-friendly methods while making
randomness explicit and avoiding silent failures during distribution fitting.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


class TabularSynthesizer:
    """Generate synthetic rows using bootstrap, parametric, or copula sampling."""

    def __init__(self, real_data: pd.DataFrame, seed: int = 42):
        if real_data.empty:
            raise ValueError("real_data must contain at least one row")
        self.real_data = real_data.reset_index(drop=True)
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.numerical_columns = real_data.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_columns = real_data.select_dtypes(exclude=[np.number]).columns.tolist()
        self.distributions: dict[str, tuple[str, tuple[float, ...]] | None] = {}

    def fit_distributions(self) -> None:
        """Fit a simple best-effort distribution per numeric column."""
        for column in self.numerical_columns:
            values = self.real_data[column].dropna().to_numpy()
            if len(values) == 0:
                self.distributions[column] = None
                continue
            best = None
            best_sse = np.inf

            candidates: list[tuple[str, tuple[float, ...]]] = [
                ("normal", (float(values.mean()), float(values.std(ddof=0) or 1.0))),
            ]
            positive = values[values > 0]
            if len(positive) > 1:
                mean = float(positive.mean())
                var = float(positive.var(ddof=0) or 1.0)
                candidates.append(("gamma", (mean * mean / var, var / mean)))
                log_values = np.log(positive)
                candidates.append(("lognormal", (float(log_values.mean()), float(log_values.std(ddof=0) or 1.0))))

            for name, params in candidates:
                try:
                    # Compare sorted samples as a light heuristic. This keeps the
                    # implementation dependency-light while still choosing a
                    # plausible distribution for tutorial data.
                    sample = self._sample_distribution(name, params, len(values))
                    sse = float(np.sum(np.square(np.sort(values) - np.sort(sample))))
                except Exception:
                    continue
                if sse < best_sse:
                    best_sse = sse
                    best = (name, params)
            self.distributions[column] = best

    def generate(self, rows: int, method: str = "bootstrap") -> pd.DataFrame:
        if rows <= 0:
            raise ValueError("rows must be greater than zero")
        if method == "bootstrap":
            return self.bootstrap(rows)
        if method == "parametric":
            return self.parametric(rows)
        if method == "copula":
            return self.copula(rows)
        raise ValueError("method must be one of: bootstrap, parametric, copula")

    def bootstrap(self, rows: int) -> pd.DataFrame:
        indices = self.rng.choice(len(self.real_data), size=rows, replace=True)
        synthetic = self.real_data.iloc[indices].copy().reset_index(drop=True)
        for column in self.numerical_columns:
            std = self.real_data[column].std()
            if pd.notna(std) and std > 0:
                synthetic[column] = synthetic[column] + self.rng.normal(0, 0.1 * std, rows)
        return synthetic

    def parametric(self, rows: int) -> pd.DataFrame:
        if not self.distributions:
            self.fit_distributions()
        synthetic = pd.DataFrame(index=range(rows))
        for column in self.numerical_columns:
            fitted = self.distributions.get(column)
            if fitted is None:
                synthetic[column] = self.real_data[column].sample(rows, replace=True, random_state=self.seed).to_numpy()
                continue
            distribution, params = fitted
            synthetic[column] = self._sample_distribution(distribution, params, rows)
        self._add_categorical_columns(synthetic, rows)
        return synthetic

    def copula(self, rows: int) -> pd.DataFrame:
        if not self.numerical_columns:
            synthetic = pd.DataFrame(index=range(rows))
            self._add_categorical_columns(synthetic, rows)
            return synthetic
        numeric = self.real_data[self.numerical_columns].fillna(self.real_data[self.numerical_columns].median())
        means = numeric.mean().to_numpy()
        stds = numeric.std(ddof=0).replace(0, 1).to_numpy()
        scaled = (numeric.to_numpy() - means) / stds
        covariance = np.cov(scaled, rowvar=False)
        correlated = self.rng.multivariate_normal(mean=np.zeros(len(self.numerical_columns)), cov=covariance, size=rows)
        synthetic = pd.DataFrame((correlated * stds) + means, columns=self.numerical_columns)
        self._add_categorical_columns(synthetic, rows)
        return synthetic

    def _sample_distribution(self, name: str, params: tuple[float, ...], rows: int) -> np.ndarray:
        if name == "normal":
            mean, std = params
            return self.rng.normal(mean, std, rows)
        if name == "gamma":
            shape, scale = params
            return self.rng.gamma(shape, scale, rows)
        if name == "lognormal":
            mean, sigma = params
            return self.rng.lognormal(mean, sigma, rows)
        raise ValueError(f"Unknown distribution: {name}")

    def _add_categorical_columns(self, synthetic: pd.DataFrame, rows: int) -> None:
        for column in self.categorical_columns:
            probabilities = self.real_data[column].value_counts(normalize=True, dropna=False)
            synthetic[column] = self.rng.choice(probabilities.index.to_numpy(), size=rows, p=probabilities.to_numpy())


def demo_real_data(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "age": rng.normal(35, 10, 1_000),
            "income": rng.lognormal(10, 0.5, 1_000),
            "category": rng.choice(["A", "B", "C"], 1_000, p=[0.3, 0.5, 0.2]),
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create synthetic rows from a CSV or demo dataframe.")
    parser.add_argument("--input", type=Path, default=None, help="Optional source CSV. If omitted, demo data is used.")
    parser.add_argument("--output", type=Path, default=Path("data/tabular_synthetic.csv"), help="Output CSV path.")
    parser.add_argument("--rows", type=int, default=500, help="Number of synthetic rows to generate.")
    parser.add_argument("--method", choices=["bootstrap", "parametric", "copula"], default="bootstrap", help="Generation method.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = pd.read_csv(args.input) if args.input else demo_real_data(args.seed)
    synthesizer = TabularSynthesizer(source, seed=args.seed)
    synthetic = synthesizer.generate(args.rows, method=args.method)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    synthetic.to_csv(args.output, index=False)
    print(f"Synthetic dataset created: {args.output}")
    print(f"rows: {len(synthetic):,}")
    print(f"method: {args.method}")


if __name__ == "__main__":
    main()
