"""
troubleshoot.py
------------------
This module takes the raw metrics from monitor.py and decides:
  1. Is anything wrong? (threshold checks)
  2. If yes, what's the likely cause and what should be checked first?

This is deliberately built to mirror how L1 support actually thinks:
not "here is the exact fix", but "here is the direction to investigate",
which is exactly what your senior described HPE asking in interviews.

Thresholds are loaded from config.json instead of being hardcoded here.
This matters in practice: different servers have different "normal"
loads (a database server naturally runs hotter than a file server), so
a real monitoring tool needs thresholds an admin can tune per-environment
without touching code. If config.json is missing or a key is absent, we
fall back to sensible defaults so the module never crashes.
"""

import json
import os

_DEFAULT_CONFIG = {
    "cpu_warning": 75, "cpu_critical": 90,
    "memory_warning": 75, "memory_critical": 90,
    "disk_warning": 80, "disk_critical": 95,
    "latency_warning_ms": 150,
}


def _load_config(path="config.json"):
    if not os.path.isfile(path):
        return _DEFAULT_CONFIG
    with open(path, "r") as f:
        user_config = json.load(f)
    # Merge: values from config.json override defaults, but any key
    # missing from the file still falls back safely.
    return {**_DEFAULT_CONFIG, **user_config}


_config = _load_config()

CPU_WARNING = _config["cpu_warning"]
CPU_CRITICAL = _config["cpu_critical"]

MEMORY_WARNING = _config["memory_warning"]
MEMORY_CRITICAL = _config["memory_critical"]

DISK_WARNING = _config["disk_warning"]
DISK_CRITICAL = _config["disk_critical"]

LATENCY_WARNING_MS = _config["latency_warning_ms"]


def check_cpu(cpu_percent):
    if cpu_percent >= CPU_CRITICAL:
        return {
            "level": "CRITICAL",
            "message": f"CPU usage is {cpu_percent}%, above critical threshold ({CPU_CRITICAL}%).",
            "next_steps": [
                "Check top processes for a runaway or stuck process",
                "Check if a scheduled job/backup is running",
                "Check for a possible malware/crypto-mining process",
                "Check if this is sustained or a short spike",
            ],
        }
    elif cpu_percent >= CPU_WARNING:
        return {
            "level": "WARNING",
            "message": f"CPU usage is {cpu_percent}%, approaching critical levels.",
            "next_steps": [
                "Monitor for a few more minutes to see if it's a spike or sustained",
                "Check top processes",
            ],
        }
    return {"level": "OK", "message": f"CPU usage is normal ({cpu_percent}%).", "next_steps": []}


def check_memory(memory_stats):
    percent = memory_stats["percent"]
    if percent >= MEMORY_CRITICAL:
        return {
            "level": "CRITICAL",
            "message": f"Memory usage is {percent}%, above critical threshold ({MEMORY_CRITICAL}%).",
            "next_steps": [
                "Check for a memory leak in a long-running process",
                "Check top processes by memory usage",
                "Consider restarting the offending service if identified",
                "Check swap usage if applicable",
            ],
        }
    elif percent >= MEMORY_WARNING:
        return {
            "level": "WARNING",
            "message": f"Memory usage is {percent}%, approaching critical levels.",
            "next_steps": ["Check top processes by memory usage"],
        }
    return {"level": "OK", "message": f"Memory usage is normal ({percent}%).", "next_steps": []}


def check_disk(disk_stats):
    percent = disk_stats["percent"]
    if percent >= DISK_CRITICAL:
        return {
            "level": "CRITICAL",
            "message": f"Disk usage is {percent}%, above critical threshold ({DISK_CRITICAL}%).",
            "next_steps": [
                "Identify large files or logs consuming space",
                "Check application/system logs for excessive growth",
                "Clear temporary files if safe to do so",
                "Check if disk failure/bad sectors could be a factor",
            ],
        }
    elif percent >= DISK_WARNING:
        return {
            "level": "WARNING",
            "message": f"Disk usage is {percent}%, approaching critical levels.",
            "next_steps": ["Review largest files/directories proactively"],
        }
    return {"level": "OK", "message": f"Disk usage is normal ({percent}%).", "next_steps": []}


def check_network(network_stats):
    if network_stats["status"] == "DOWN":
        return {
            "level": "CRITICAL",
            "message": "Network connectivity check failed - cannot reach external host.",
            "next_steps": [
                "Verify the network interface (NIC) is up and enabled",
                "Check IP configuration (is it a valid IP, correct subnet?)",
                "Check the default gateway is reachable",
                "Check physical cable / link light if on-site",
                "Check DNS resolution separately from raw connectivity",
            ],
        }
    latency = network_stats["latency_ms"]
    if latency is not None and latency >= LATENCY_WARNING_MS:
        return {
            "level": "WARNING",
            "message": f"Network is reachable but latency is high ({latency} ms).",
            "next_steps": [
                "Check for network congestion",
                "Run a traceroute to see where delay is introduced",
            ],
        }
    return {
        "level": "OK",
        "message": f"Network is reachable ({latency} ms latency).",
        "next_steps": [],
    }


def analyze(metrics):
    """
    Takes the full metrics dictionary from monitor.collect_all_metrics()
    and returns a structured health report combining all checks.
    """
    report = {
        "cpu": check_cpu(metrics["cpu"]),
        "memory": check_memory(metrics["memory"]),
        "disk": check_disk(metrics["disk"]),
        "network": check_network(metrics["network"]),
    }

    levels = [item["level"] for item in report.values()]
    if "CRITICAL" in levels:
        overall = "CRITICAL"
    elif "WARNING" in levels:
        overall = "WARNING"
    else:
        overall = "HEALTHY"

    report["overall_status"] = overall
    return report


if __name__ == "__main__":
    # Manual test using fake data, so this module can be tested
    # independently of monitor.py.
    fake_metrics = {
        "cpu": 92,
        "memory": {"percent": 60},
        "disk": {"percent": 97},
        "network": {"status": "UP", "latency_ms": 45},
    }
    import json
    print(json.dumps(analyze(fake_metrics), indent=2))
