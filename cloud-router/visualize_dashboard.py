# Importing the required libraries for reading database data, creating the dashboard file, and opening it in the browser.
from azure.cosmos import CosmosClient
import webbrowser
import os
import json



# Storing the database connection details and selecting the database.
COSMOS_CONN_STR = "---------------hidden due to security-------------------------------"
DATABASE_NAME = "TransitData"

# Connecting to Cosmos DB for reading telemetry and trip data.
print("Connecting to Cosmos DB...")
client = CosmosClient.from_connection_string(COSMOS_CONN_STR)
database = client.get_database_client(DATABASE_NAME)

# Asking the user to enter the bus ID for the dashboard.
target_bus = input("\nEnter the Bus ID for the telemetry dashboard (e.g., Bus-001): ").strip()
parameters = [{"name": "@bus_id", "value": target_bus}]

# Reading telemetry data such as fuel level and engine temperature.
print(f"Fetching Telemetry data for {target_bus}...")
container_tel = database.get_container_client("Telemetry")
query_tel = """
    SELECT c.timestamp, c.fuelLevel, c.engineTemp 
    FROM c 
    WHERE (c.vehicleID = @bus_id OR c.vehicleId = @bus_id) AND c.eventType = 'telemetry'
"""
items_tel = list(container_tel.query_items(query=query_tel, parameters=parameters, enable_cross_partition_query=True))

# Reading trip data such as vehicle speed.
print(f"Fetching Trip data for {target_bus}...")
container_trips = database.get_container_client("Trips")
query_trips = """
    SELECT c.timestamp, c.gps 
    FROM c 
    WHERE (c.vehicleID = @bus_id OR c.vehicleId = @bus_id) AND c.eventType = 'trip' AND IS_DEFINED(c.gps)
"""
items_trips = list(container_trips.query_items(query=query_trips, parameters=parameters, enable_cross_partition_query=True))

# Checking whether any data was found for the selected bus.
if not items_tel and not items_trips:
    print(f"\n[ERROR] No data found for '{target_bus}'.")
    exit()

# Sorting the data by time for showing the charts in the correct order.
items_tel.sort(key=lambda x: x.get("timestamp", ""))
items_trips.sort(key=lambda x: x.get("timestamp", ""))

# Extracting the chart data from the query results.
tel_times = [i.get("timestamp")[11:19] for i in items_tel]
fuel_data = [i.get("fuelLevel") for i in items_tel]
temp_data = [i.get("engineTemp") for i in items_tel]

trip_times = [i.get("timestamp")[11:19] for i in items_trips]
speed_data = [i.get("gps", {}).get("speed") for i in items_trips]

# Extracting the latest values for the dashboard summary cards.
latest_speed = f"{speed_data[-1]}" if speed_data and speed_data[-1] is not None else "--"
latest_temp = f"{temp_data[-1]}" if temp_data and temp_data[-1] is not None else "--"
latest_fuel = f"{fuel_data[-1]}" if fuel_data and fuel_data[-1] is not None else "--"

# Creating the full HTML content for the telemetry dashboard.
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{target_bus} - Live Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #161623; color: #fff; padding: 20px; margin: 0; }}
        h1 {{ text-align: center; color: #fff; margin-bottom: 10px; font-weight: 300; letter-spacing: 2px; }}
        .header-subtitle {{ text-align: center; color: #888; margin-bottom: 40px; font-size: 0.9em; }}
        .kpi-container {{ display: flex; justify-content: center; gap: 30px; margin-bottom: 40px; flex-wrap: wrap; }}
        .kpi-card {{ background: linear-gradient(145deg, #1f1f30, #2a2a40); padding: 30px; border-radius: 20px; text-align: center; width: 250px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); border: 1px solid #333; }}
        .kpi-icon {{ font-size: 3em; margin-bottom: 15px; }}
        .kpi-value {{ font-size: 3.5em; font-weight: bold; margin: 10px 0; text-shadow: 0 0 15px rgba(255,255,255,0.1); }}
        .kpi-unit {{ font-size: 0.3em; color: #aaa; font-weight: normal; vertical-align: middle; }}
        .kpi-label {{ color: #aaa; font-size: 1.1em; text-transform: uppercase; letter-spacing: 1px; }}
        .grid-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; max-width: 1400px; margin: 0 auto; }}
        .chart-card {{ background-color: #1f1f30; padding: 25px; border-radius: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); border: 1px solid #333; }}
        .full-width {{ grid-column: 1 / -1; }}
    </style>
</head>
<body>
    <h1>FLEET TELEMETRY DASHBOARD</h1>
    <div class="header-subtitle">LIVE TRACKING ACTIVE FOR: <strong>{target_bus.upper()}</strong></div>

    <div class="kpi-container">
        <div class="kpi-card">
            <i class="fa-solid fa-gauge-high kpi-icon" style="color: #00f2fe;"></i>
            <div class="kpi-value">{latest_speed} <span class="kpi-unit">km/h</span></div>
            <div class="kpi-label">Current Speed</div>
        </div>

        <div class="kpi-card">
            <i class="fa-solid fa-temperature-half kpi-icon" style="color: #ff0844;"></i>
            <div class="kpi-value">{latest_temp} <span class="kpi-unit">°C</span></div>
            <div class="kpi-label">Engine Temp</div>
        </div>

        <div class="kpi-card">
            <i class="fa-solid fa-gas-pump kpi-icon" style="color: #4facfe;"></i>
            <div class="kpi-value">{latest_fuel} <span class="kpi-unit">%</span></div>
            <div class="kpi-label">Fuel Level</div>
        </div>
    </div>

    <div class="grid-container">
        <div class="chart-card">
            <canvas id="speedChart"></canvas>
        </div>
        <div class="chart-card">
            <canvas id="tempChart"></canvas>
        </div>
        <div class="chart-card full-width">
            <canvas id="fuelChart"></canvas>
        </div>
    </div>

    <script>
        const createChart = (ctxId, label, labels, data, borderColor, bgColor) => {{
            new Chart(document.getElementById(ctxId), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: label + ' History',
                        data: data,
                        borderColor: borderColor,
                        backgroundColor: bgColor,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 2,
                        pointHoverRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }},
                    scales: {{
                        x: {{ grid: {{ color: '#333' }}, ticks: {{ color: '#aaa' }} }},
                        y: {{ grid: {{ color: '#333' }}, ticks: {{ color: '#aaa' }} }}
                    }}
                }}
            }});
        }};

        const tripTimes = {json.dumps(trip_times)};
        const speedData = {json.dumps(speed_data)};

        const telTimes = {json.dumps(tel_times)};
        const tempData = {json.dumps(temp_data)};
        const fuelData = {json.dumps(fuel_data)};

        createChart('speedChart', 'Speed (km/h)', tripTimes, speedData, '#00f2fe', 'rgba(0, 242, 254, 0.1)');
        createChart('tempChart', 'Engine Temp (°C)', telTimes, tempData, '#ff0844', 'rgba(255, 8, 68, 0.1)');
        createChart('fuelChart', 'Fuel Level (%)', telTimes, fuelData, '#4facfe', 'rgba(79, 172, 254, 0.1)');
    </script>
</body>
</html>
"""

# Saving the dashboard as an HTML file.
html_file = f"dashboard_{target_bus}.html"
with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

# Opening the generated dashboard file in the browser.
print("\nDashboard generated successfully! Opening in browser...")
webbrowser.open("file://" + os.path.realpath(html_file))