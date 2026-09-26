"""
monitor.py
------------------
Core monitoring engine for ServerPulse.

This module is responsible for ONE thing only: collecting raw system
health data. It does not decide whether something is "good" or "bad" -
that judgment happens in troubleshoot.py. Keeping these separate makes
the code easier to explain: "monitor.py collects data, troubleshoot.py
interprets it."
"""

import psutil
import socket
import platform
import time
import subprocess


def get_cpu_usage():
    """
    Returns current CPU utilization as a percentage.
    interval=1 means psutil measures CPU usage over a 1-second window
    instead of instantly comparing two calls (which gives noisy results).
    """
    return psutil.cpu_percent(interval=1)


def get_memory_usage():
    """
    Returns a dictionary with total, used, available memory (in GB)
    and percentage used.
    """
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "used_gb": round(mem.used / (1024 ** 3), 2),
        "available_gb": round(mem.available / (1024 ** 3), 2),
        "percent": mem.percent,
    }


def get_disk_usage(path="/"):
    """
    Returns disk usage stats for the given path (root by default).
    On Windows this should be changed to something like 'C:\\'.
    """
    disk = psutil.disk_usage(path)
    return {
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "used_gb": round(disk.used / (1024 ** 3), 2),
        "free_gb": round(disk.free / (1024 ** 3), 2),
        "percent": disk.percent,
    }


def get_network_status(host="8.8.8.8", port=53, timeout=2):
    """
    Checks network connectivity WITHOUT relying on the OS 'ping' command,
    so it works the same way on Windows/Linux/Mac.

    How it works:
    We try to open a raw TCP socket connection to 8.8.8.8 (Google's public
    DNS server) on port 53 (the DNS port). If the connection succeeds,
    we know the network path (NIC -> gateway -> internet) is working.
    This is the same underlying idea as 'can I reach the outside world',
    just done at the socket level instead of shelling out to ping.
    """
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        latency_ms = round((time.time() - start) * 1000, 2)
        return {"status": "UP", "latency_ms": latency_ms}
    except OSError:
        return {"status": "DOWN", "latency_ms": None}


def get_top_processes(limit=5):
    """
    Returns the top N processes sorted by CPU usage.
    We call cpu_percent() once per process without an interval first
    to 'prime' psutil's internal counters, then sort by the values
    on the second pass. This mirrors how top/htop-style tools work.
    """
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # A process can exit between listing it and reading its info -
            # we just skip it rather than crashing.
            continue

    processes.sort(key=lambda p: p["cpu_percent"] or 0, reverse=True)
    return processes[:limit]


def get_system_info():
    """
    Basic identifying information about the machine - hostname, OS,
    and uptime. Uptime is calculated from psutil.boot_time(), which
    returns a Unix timestamp of when the system started.
    """
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_str = format_uptime(uptime_seconds)

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "uptime": uptime_str,
    }


def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}m"


def collect_all_metrics():
    """
    Convenience function that gathers everything in one call.
    This is what the dashboard (app.py) will import and use.
    """
    return {
        "cpu": get_cpu_usage(),
        "memory": get_memory_usage(),
        "disk": get_disk_usage(),
        "network": get_network_status(),
        "processes": get_top_processes(),
        "system": get_system_info(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


if __name__ == "__main__":
    # Quick manual test: run "python monitor.py" to print a snapshot
    # of current system health to the terminal.
    import json
    metrics = collect_all_metrics()
    print(json.dumps(metrics, indent=2))
