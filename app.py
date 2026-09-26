"""
app.py
------------------
Streamlit dashboard for ServerPulse.

This file is intentionally "thin" - it doesn't contain monitoring or
troubleshooting logic itself. It just calls monitor.collect_all_metrics(),
passes the result to troubleshoot.analyze(), and displays everything.

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import time

from monitor import collect_all_metrics
from troubleshoot import analyze
from history import log_snapshot, load_history

st.set_page_config(page_title="ServerPulse", page_icon="📡", layout="wide")

STATUS_COLORS = {
    "OK": "🟢",
    "HEALTHY": "🟢",
    "WARNING": "🟡",
    "CRITICAL": "🔴",
}

STATUS_BG = {
    "HEALTHY": "#e6f4ea",
    "WARNING": "#fff4e5",
    "CRITICAL": "#fdecea",
}
STATUS_TEXT = {
    "HEALTHY": "#1e7e34",
    "WARNING": "#a06400",
    "CRITICAL": "#a61b1b",
}

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 12px 16px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    "<h1 style='margin-bottom:0;'>📡 ServerPulse</h1>"
    "<p style='color:#6c757d; margin-top:4px;'>Real-Time Server Health &amp; Network Monitoring System</p>",
    unsafe_allow_html=True,
)

placeholder = st.empty()

refresh = st.sidebar.checkbox("Auto-refresh every 5 seconds", value=False)
run_once = st.sidebar.button("Refresh now")


def render(metrics, report):
    with placeholder.container():
        overall = report["overall_status"]
        st.markdown(
            f"""
            <div style="background-color:{STATUS_BG[overall]}; color:{STATUS_TEXT[overall]};
                        padding:14px 20px; border-radius:10px; font-size:18px; font-weight:600;
                        margin-bottom:6px;">
                {STATUS_COLORS[overall]} Server Status: {overall}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Last updated: {metrics['timestamp']}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CPU", f"{metrics['cpu']}%")
        col2.metric("Memory", f"{metrics['memory']['percent']}%")
        col3.metric("Disk", f"{metrics['disk']['percent']}%")
        col4.metric(
            "Network",
            metrics["network"]["status"],
            f"{metrics['network']['latency_ms']} ms" if metrics["network"]["latency_ms"] else "",
        )

        st.divider()

        info_col, proc_col = st.columns([1, 2])

        with info_col:
            st.markdown("**System Information**")
            sysinfo = metrics["system"]
            st.write(f"Hostname: `{sysinfo['hostname']}`")
            st.write(f"OS: `{sysinfo['os']}`")
            st.write(f"Uptime: `{sysinfo['uptime']}`")

        with proc_col:
            st.markdown("**Top Processes**")
            df = pd.DataFrame(metrics["processes"])
            if not df.empty:
                df = df.rename(columns={
                    "pid": "PID", "name": "Process",
                    "cpu_percent": "CPU %", "memory_percent": "Memory %"
                })
                df["Memory %"] = df["Memory %"].round(2)
                st.dataframe(df, hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("**Alerts & Troubleshooting Guidance**")

        any_alert = False
        for component in ["cpu", "memory", "disk", "network"]:
            check = report[component]
            if check["level"] != "OK":
                any_alert = True
                icon = STATUS_COLORS[check["level"]]
                with st.expander(f"{icon} {component.upper()} — {check['level']}: {check['message']}"):
                    st.write("Suggested first steps to investigate:")
                    for step in check["next_steps"]:
                        st.write(f"- {step}")

        if not any_alert:
            st.success("No issues detected. All systems within normal range.")

        st.divider()
        st.markdown("**Trend — CPU & Memory over recent readings**")
        history_rows = load_history(max_points=50)
        if len(history_rows) >= 2:
            hist_df = pd.DataFrame(history_rows)
            hist_df["cpu"] = hist_df["cpu"].astype(float)
            hist_df["memory_percent"] = hist_df["memory_percent"].astype(float)
            hist_df = hist_df.set_index("timestamp")[["cpu", "memory_percent"]]
            hist_df.columns = ["CPU %", "Memory %"]
            st.line_chart(hist_df)
        else:
            st.caption("Not enough history yet — refresh a few more times to see a trend.")


metrics = collect_all_metrics()
report = analyze(metrics)
log_snapshot(metrics, report["overall_status"])
render(metrics, report)

if refresh:
    time.sleep(5)
    st.rerun()
