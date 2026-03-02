import json
from pathlib import Path

# Importing the required libraries for reading JSON files and working with folder paths.

# Setting the main folder paths used for reading event files and saving the report.
BASE_DIR = Path(__file__).resolve().parent.parent
PENDING_DIR = BASE_DIR / "data" / "pending"
SYNCED_DIR = BASE_DIR / "data" / "synced"
ALERT_LOG_PATH = BASE_DIR / "src" / "alerts.log"
REPORTS_DIR = BASE_DIR / "reports"

# Creating the reports folder if it does not already exist.
REPORTS_DIR.mkdir(exist_ok=True)

# Reading all JSON files from the pending and synced folders.
pending_files = list(PENDING_DIR.glob("*.json"))
synced_files = list(SYNCED_DIR.glob("*.json"))

# Counting how many files are currently pending and how many have already been synced.
pending_count = len(pending_files)
synced_count = len(synced_files)

# Setting the starting values for alert analysis.
alert_count = 0
high_engine_temp_count = 0
low_fuel_count = 0

# Reading the alert log file and counting the different types of alerts.
if ALERT_LOG_PATH.exists():
    with open(ALERT_LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        alert_count = len(lines)
        for line in lines:
            if "HIGH_ENGINE_TEMP" in line:
                high_engine_temp_count += 1
            if "LOW_FUEL" in line:
                low_fuel_count += 1

# Setting the starting values for synced data analysis.
delayed_sync_count = 0
event_type_counts = {
    "telemetry": 0,
    "ticketing": 0,
    "trip": 0,
    "alert": 0,
    "unknown": 0
}

# Reading each synced file and analyzing its event type and sync delay.
for file_path in synced_files:
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            event_data = json.load(f)

            # Counting the files that were uploaded after being delayed offline.
            if event_data.get("syncDelaySeconds", 0) > 0:
                delayed_sync_count += 1

            # Counting how many synced files belong to each event type.
            e_type = event_data.get("eventType", "unknown")
            if e_type in event_type_counts:
                event_type_counts[e_type] += 1
            else:
                event_type_counts["unknown"] += 1

        except json.JSONDecodeError:
            # Printing a warning if a file cannot be read properly.
            print(f"Warning: Could not read {file_path.name}")

# Creating the summary report content line by line.
summary_lines = [
    "==========================================",
    "  EDGE NODE SYNC SUMMARY REPORT",
    "==========================================",
    f"Total Pending Files : {pending_count}",
    f"Total Synced Files  : {synced_count}",
    "------------------------------------------",
    "  SYNCED EVENT BREAKDOWN",
    "------------------------------------------",
    f"  - Telemetry       : {event_type_counts['telemetry']}",
    f"  - Ticketing       : {event_type_counts['ticketing']}",
    f"  - Trips           : {event_type_counts['trip']}",
    f"  - Alerts          : {event_type_counts['alert']}",
    "------------------------------------------",
    "  NETWORK RESILIENCE METRICS",
    "------------------------------------------",
    f"Files recovered from offline state (Delay > 0s): {delayed_sync_count}",
    "------------------------------------------",
    "  CRITICAL ALERT LOG SUMMARY",
    "------------------------------------------",
    f"Total Logged Alerts : {alert_count}",
    f"  - High Engine Temp: {high_engine_temp_count}",
    f"  - Low Fuel        : {low_fuel_count}",
    "=========================================="
]

# Printing the summary report to the console.
print("\n".join(summary_lines))

# Saving the summary report to a text file.
report_path = REPORTS_DIR / "summary_report.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))

# Showing the location of the saved report file.
print(f"\n[SUCCESS] Summary report saved to: {report_path}")