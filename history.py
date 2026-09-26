"""
history.py
------------------
Adds persistence: every time the dashboard collects a metrics snapshot,
we append a row to a local CSV file. This is what turns ServerPulse from
"a single live reading" into something that can show trends over time -
e.g. "CPU has been climbing steadily for the last 10 minutes" instead of
just "CPU is 92% right now".

Kept deliberately simple: a flat CSV file, no database. In a real
enterprise tool this would go to a time-series database (e.g. Prometheus),
but for this project a CSV is easy to inspect, explain, and reason about
line by line - which matters more than using a "fancier" tool I can't
fully explain in an interview.
"""

import csv
import os
from datetime import datetime

HISTORY_FILE = "history.csv"
FIELDNAMES = ["timestamp", "cpu", "memory_percent", "disk_percent", "network_latency_ms", "overall_status"]


def log_snapshot(metrics, overall_status, path=HISTORY_FILE):
    """
    Appends one row of metrics to the history CSV.
    Creates the file with a header row the first time it's called.
    """
    file_exists = os.path.isfile(path)

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cpu": metrics["cpu"],
            "memory_percent": metrics["memory"]["percent"],
            "disk_percent": metrics["disk"]["percent"],
            "network_latency_ms": metrics["network"]["latency_ms"] or 0,
            "overall_status": overall_status,
        })


def load_history(path=HISTORY_FILE, max_points=50):
    """
    Reads the history CSV and returns the last `max_points` rows.
    Returns an empty list if the file doesn't exist yet (e.g. on first run).
    We only keep the most recent points so the chart stays readable and
    the file doesn't need to be fully re-read into memory as it grows.
    """
    if not os.path.isfile(path):
        return []

    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return rows[-max_points:]


if __name__ == "__main__":
    # Quick manual test
    fake_metrics = {
        "cpu": 45,
        "memory": {"percent": 60},
        "disk": {"percent": 70},
        "network": {"latency_ms": 20},
    }
    log_snapshot(fake_metrics, "HEALTHY", path="test_history.csv")
    print(load_history(path="test_history.csv"))
    os.remove("test_history.csv")
