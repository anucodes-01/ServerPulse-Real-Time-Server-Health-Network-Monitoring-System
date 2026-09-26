# ServerPulse — Real-Time Server Health & Network Monitoring System

A lightweight Python tool that monitors a server's CPU, memory, disk and
network health, detects abnormal conditions using threshold-based checks,
and surfaces first-step troubleshooting guidance for each alert — rather
than just showing raw numbers.

## Why I built this

I wanted to understand, hands-on, how system health monitoring and basic
infrastructure troubleshooting actually work under the hood — not just
watch a dashboard, but build the logic that decides *what counts as a
problem* and *what to check first*.

## How it works

The project is split into files on purpose, so each piece has a single
responsibility:

- **`monitor.py`** — collects raw data only. Uses `psutil` for CPU,
  memory, disk and process stats. Checks network reachability with a raw
  TCP socket connection to `8.8.8.8:53` (Google DNS) instead of shelling
  out to `ping`, so it behaves the same on Windows, Linux and Mac.
- **`config.json`** — all warning/critical thresholds live here instead
  of being hardcoded, since different servers have different "normal"
  load (a database server runs hotter than a file server by default).
- **`troubleshoot.py`** — loads `config.json`, then applies threshold
  checks (warning/critical) for CPU, memory, disk and network. For every
  alert it returns not just a message but a short list of **first
  troubleshooting steps** — the same "what's your first step" style of
  answer used in L1 support.
- **`history.py`** — appends every metrics snapshot to a local CSV file
  and loads the last N readings back. This is what turns the project
  from "a single live reading" into something that can show a trend.
- **`app.py`** — a Streamlit dashboard that calls the modules above and
  displays: live metrics, a CPU/memory trend chart, top processes, and
  expandable alert cards with suggested next steps.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Or test the logic directly from the terminal without the UI:

```bash
python monitor.py       # prints a raw metrics snapshot
python troubleshoot.py  # prints a sample analysis using fake data
```

## Design decisions worth knowing (likely interview questions)

- **Why psutil?** It's cross-platform and reads directly from the OS
  (`/proc` on Linux, WMI on Windows) rather than parsing shell command
  output, which is more reliable.
- **Why a TCP socket instead of `ping`?** `ping` uses ICMP, which some
  networks/firewalls block even when the host is reachable over TCP, and
  `ping`'s command-line output format differs across operating systems.
  A socket connection to a known-open port (DNS, port 53) is a cleaner,
  cross-platform reachability check.
- **Why separate monitor.py and troubleshoot.py?** So data collection
  and decision-making are independent — you could swap in a different
  data source (e.g. real server SNMP data) without touching the
  threshold/alerting logic at all.
- **Why thresholds as constants?** Real monitoring tools (e.g. HPE
  OneView, Nagios) make thresholds configurable per environment; hardcoding
  them here keeps the project simple while showing I understand that
  thresholds shouldn't be arbitrary.

## Possible extensions (if asked "what would you add next")

- Move history from CSV to a proper time-series database for longer retention
- Email/Slack alerting when status becomes CRITICAL
- Remote monitoring of multiple servers instead of just localhost
- RAID/disk health via SMART data
- Configurable thresholds per server profile, not just one global config.json
