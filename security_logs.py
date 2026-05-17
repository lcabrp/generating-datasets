#!/usr/bin/env python3
"""Generate synthetic security log datasets.

This script collects the useful dataset-generation ideas from the benchmark repo:

1. A vectorized tabular log generator for dataframe benchmarks.
2. A streaming SIEM-style NDJSON generator with active hosts and attack bursts.

Examples:
    python security_logs.py benchmark --rows 100000 --output data/logs/synthetic_logs.csv
    python security_logs.py benchmark --rows 100000 --output data/logs/synthetic_logs.parquet --format parquet
    python security_logs.py siem --days 7 --events-per-day 1000 --output data/logs/siem_logs.ndjson
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


SOURCE_IPS = [
    "192.168.1.10",
    "192.168.1.15",
    "192.168.1.20",
    "192.168.1.25",
    "10.0.0.5",
    "10.0.0.8",
    "10.0.0.12",
    "172.16.0.3",
    "172.16.0.7",
]
SOURCE_IP_WEIGHTS = [0.15, 0.12, 0.10, 0.08, 0.15, 0.12, 0.08, 0.10, 0.10]

DESTINATION_IPS = [
    "203.0.113.1",
    "198.51.100.5",
    "93.184.216.34",
    "8.8.8.8",
    "1.1.1.1",
    "208.67.222.222",
    "185.199.108.153",
]

PORTS = [80, 443, 22, 21, 25, 53, 3389, 8080, 8443]
PORT_WEIGHTS = [0.35, 0.30, 0.10, 0.05, 0.05, 0.05, 0.03, 0.04, 0.03]

PROTOCOLS = ["TCP", "UDP", "ICMP"]
PROTOCOL_WEIGHTS = [0.70, 0.25, 0.05]

EVENT_TYPES = [
    "login_success",
    "login_failed",
    "file_access",
    "network_scan",
    "malware_detected",
    "suspicious_activity",
    "data_transfer",
    "system_error",
]
EVENT_TYPE_WEIGHTS = [0.25, 0.15, 0.20, 0.08, 0.05, 0.07, 0.15, 0.05]

SEVERITIES = ["low", "medium", "high", "critical"]
SEVERITY_WEIGHTS = [0.50, 0.30, 0.15, 0.05]

USERS = [
    "alice.smith",
    "bob.jones",
    "charlie.brown",
    "diana.wilson",
    "eve.davis",
    "frank.miller",
    "grace.taylor",
    "system",
    "admin",
]
USER_WEIGHTS = [0.15, 0.12, 0.10, 0.08, 0.10, 0.08, 0.07, 0.15, 0.15]

STATUS_CODES = [200, 404, 500, 403, 401, 302]
STATUS_CODE_WEIGHTS = [0.60, 0.15, 0.08, 0.07, 0.05, 0.05]

COUNTRIES = ["US", "CA", "GB", "DE", "FR", "JP", "AU", "BR", "IN", "CN"]
COUNTRY_WEIGHTS = [0.30, 0.10, 0.10, 0.08, 0.07, 0.08, 0.05, 0.05, 0.07, 0.10]

DEVICES = [
    "Windows_Desktop",
    "MacOS_Laptop",
    "Linux_Server",
    "iPhone",
    "Android",
    "iPad",
    "Router",
    "IoT_Device",
]
DEVICE_WEIGHTS = [0.25, 0.15, 0.20, 0.12, 0.10, 0.08, 0.05, 0.05]

SIEM_EVENT_TYPES = [
    "auth_success",
    "auth_fail",
    "malware_detected",
    "port_scan",
    "firewall_block",
    "file_access",
    "usb_insert",
    "policy_violation",
    "process_start",
    "config_change",
]
SIEM_EVENT_WEIGHTS = [0.35, 0.22, 0.03, 0.05, 0.06, 0.12, 0.03, 0.04, 0.08, 0.02]

RISK_BY_EVENT = {
    "auth_success": "low",
    "auth_fail": "medium",
    "malware_detected": "high",
    "port_scan": "medium",
    "firewall_block": "medium",
    "file_access": "low",
    "usb_insert": "medium",
    "policy_violation": "medium",
    "process_start": "low",
    "config_change": "medium",
}


def generate_benchmark_logs(rows: int, seed: int = 42) -> pd.DataFrame:
    """Generate a vectorized dataframe suitable for dataframe benchmark workloads."""
    rng = np.random.default_rng(seed)
    start_time = datetime.now() - timedelta(days=30)
    timestamps = pd.date_range(start=start_time, periods=rows, freq="30s")

    bytes_transferred = rng.lognormal(mean=8, sigma=2, size=rows).astype(int)
    bytes_transferred = np.clip(bytes_transferred, 100, 1_000_000)

    response_times = rng.gamma(shape=2, scale=50, size=rows).astype(int)
    response_times = np.clip(response_times, 1, 5_000)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "source_ip": rng.choice(SOURCE_IPS, size=rows, p=SOURCE_IP_WEIGHTS),
            "destination_ip": rng.choice(DESTINATION_IPS, size=rows),
            "port": rng.choice(PORTS, size=rows, p=PORT_WEIGHTS),
            "protocol": rng.choice(PROTOCOLS, size=rows, p=PROTOCOL_WEIGHTS),
            "event_type": rng.choice(EVENT_TYPES, size=rows, p=EVENT_TYPE_WEIGHTS),
            "severity": rng.choice(SEVERITIES, size=rows, p=SEVERITY_WEIGHTS),
            "user": rng.choice(USERS, size=rows, p=USER_WEIGHTS),
            "status_code": rng.choice(STATUS_CODES, size=rows, p=STATUS_CODE_WEIGHTS),
            "bytes": bytes_transferred,
            "response_time_ms": response_times,
            "country": rng.choice(COUNTRIES, size=rows, p=COUNTRY_WEIGHTS),
            "device_type": rng.choice(DEVICES, size=rows, p=DEVICE_WEIGHTS),
            "session_id": rng.integers(100_000, 999_999, size=rows),
            "risk_score": rng.uniform(0, 100, size=rows).round(2),
        }
    )


def event_details(event_type: str, rng: random.Random) -> dict:
    """Generate event-specific SIEM metadata."""
    if event_type == "auth_fail":
        return {"fail_reason": rng.choice(["bad_password", "user_locked", "expired"])}
    if event_type == "malware_detected":
        return {
            "malware_name": rng.choice(["Emotet", "TrickBot", "AgentTesla", "unknown"]),
            "severity": rng.choice(["high", "medium", "low"]),
        }
    if event_type == "port_scan":
        return {
            "proto": rng.choice(["tcp", "udp"]),
            "target_port": rng.choice([22, 80, 135, 443, 445, 3389]),
        }
    if event_type == "file_access":
        return {
            "file": rng.choice(["/etc/passwd", "C:/Windows/secret.txt", "/var/log/syslog"]),
            "access_type": rng.choice(["read", "write", "delete"]),
        }
    if event_type == "firewall_block":
        return {
            "proto": rng.choice(["tcp", "udp"]),
            "rule": rng.choice(["block-list", "IDS", "manual"]),
        }
    return {}


def generate_siem_events(
    days: int = 30,
    events_per_day: int = 1_000,
    network_prefix: str = "10.1.0.",
    hosts: int = 80,
    active_hosts: int = 15,
    campaign_count: int = 3,
    seed: int = 42,
) -> Iterable[dict]:
    """Yield SIEM-style events with active hosts, weekends, and attack campaigns."""
    rng = random.Random(seed)
    hosts = min(max(hosts, 1), 254)
    active_hosts = min(max(active_hosts, 1), hosts)
    host_ips = [f"{network_prefix}{i}" for i in range(1, hosts + 1)]
    active = set(rng.sample(host_ips, active_hosts))
    passive = list(set(host_ips) - active)
    active_list = list(active)
    first_day = datetime.now() - timedelta(days=days)
    users = [f"user{i}" for i in range(1, 41)]

    campaigns = []
    if days >= 2 and campaign_count > 0:
        for campaign_id in range(1, campaign_count + 1):
            length = rng.randint(1, min(3, days))
            start_day = rng.randint(0, max(0, days - length))
            target_count = min(max(2, hosts // 10), hosts)
            campaigns.append(
                {
                    "campaign_id": f"camp_{campaign_id}",
                    "start_day": start_day,
                    "length": length,
                    "hosts": rng.sample(host_ips, target_count),
                    "event_type": rng.choices(
                        ["malware_detected", "auth_fail", "port_scan"],
                        weights=[0.5, 0.3, 0.2],
                        k=1,
                    )[0],
                    "daily_intensity": rng.randint(50, 200),
                }
            )

    campaigns_by_day = {day: [] for day in range(days)}
    for campaign in campaigns:
        for offset in range(campaign["length"]):
            day = campaign["start_day"] + offset
            if day < days:
                campaigns_by_day[day].append(campaign)

    def choose_user(host: str) -> str:
        if host in active:
            return rng.choice(users[:10])
        return rng.choice(users)

    for day in range(days):
        day_date = first_day + timedelta(days=day)
        current_events = events_per_day
        if day_date.weekday() >= 5:
            current_events = int(current_events * rng.uniform(0.5, 0.7))

        active_count = int(current_events * rng.uniform(0.70, 0.80))
        passive_count = current_events - active_count
        daily_hosts = rng.choices(active_list, k=active_count)
        if passive:
            daily_hosts.extend(rng.choices(passive, k=passive_count))
        else:
            daily_hosts.extend(rng.choices(active_list, k=passive_count))

        for host in daily_hosts:
            event_type = rng.choices(SIEM_EVENT_TYPES, weights=SIEM_EVENT_WEIGHTS, k=1)[0]
            ts = day_date + timedelta(seconds=rng.randint(0, 86_399))
            yield {
                "ts": ts.isoformat(timespec="seconds"),
                "host": host,
                "event_type": event_type,
                "user": choose_user(host),
                "risk": RISK_BY_EVENT.get(event_type, "medium"),
                **event_details(event_type, rng),
            }

        for campaign in campaigns_by_day[day]:
            for _ in range(campaign["daily_intensity"]):
                host = rng.choice(campaign["hosts"])
                event_type = campaign["event_type"]
                ts = day_date + timedelta(seconds=rng.randint(0, 86_399))
                yield {
                    "ts": ts.isoformat(timespec="seconds"),
                    "host": host,
                    "event_type": event_type,
                    "user": choose_user(host),
                    "risk": RISK_BY_EVENT.get(event_type, "medium"),
                    "campaign_id": campaign["campaign_id"],
                    **event_details(event_type, rng),
                }


def write_benchmark_logs(rows: int, output: Path, output_format: str, seed: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    df = generate_benchmark_logs(rows=rows, seed=seed)

    if output_format == "csv":
        df.to_csv(output, index=False)
    elif output_format == "parquet":
        try:
            df.to_parquet(output, index=False)
        except ImportError as exc:
            raise SystemExit("Parquet output requires pyarrow or fastparquet. Install pyarrow.") from exc
    else:
        raise ValueError(f"Unsupported benchmark format: {output_format}")

    print(f"Generated {rows:,} benchmark log rows -> {output}")
    print(f"Dataset shape: {df.shape}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")


def write_siem_logs(args: argparse.Namespace) -> None:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.output.open("w", encoding="utf-8") as file:
        for event in generate_siem_events(
            days=args.days,
            events_per_day=args.events_per_day,
            network_prefix=args.network_prefix,
            hosts=args.hosts,
            active_hosts=args.active_hosts,
            campaign_count=args.campaigns,
            seed=args.seed,
        ):
            file.write(json.dumps(event) + "\n")
            count += 1

    print(f"Generated {count:,} SIEM events -> {args.output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic security log datasets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    benchmark = subparsers.add_parser("benchmark", help="Generate vectorized benchmark logs.")
    benchmark.add_argument("--rows", type=int, default=100_000)
    benchmark.add_argument("--output", type=Path, default=Path("data/logs/synthetic_logs.csv"))
    benchmark.add_argument("--format", choices=["csv", "parquet"], default=None)
    benchmark.add_argument("--seed", type=int, default=42)

    siem = subparsers.add_parser("siem", help="Generate streaming SIEM NDJSON logs.")
    siem.add_argument("--days", type=int, default=30)
    siem.add_argument("--events-per-day", type=int, default=1_000)
    siem.add_argument("--network-prefix", default="10.1.0.")
    siem.add_argument("--hosts", type=int, default=80)
    siem.add_argument("--active-hosts", type=int, default=15)
    siem.add_argument("--campaigns", type=int, default=3)
    siem.add_argument("--output", type=Path, default=Path("data/logs/siem_logs.ndjson"))
    siem.add_argument("--seed", type=int, default=42)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "benchmark":
        output_format = args.format or args.output.suffix.lower().lstrip(".") or "csv"
        write_benchmark_logs(args.rows, args.output, output_format, args.seed)
    elif args.command == "siem":
        write_siem_logs(args)


if __name__ == "__main__":
    main()
