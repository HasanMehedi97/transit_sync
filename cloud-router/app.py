# Importing the required libraries for the web app, database connection, and map display.
from flask import Flask, request, redirect, url_for, render_template_string
from azure.cosmos import CosmosClient
import folium



# Creating the Flask application.
app = Flask(__name__)

# Storing the database connection details and selecting the database and container.
COSMOS_CONN_STR = "---------------hidden due to security-------------------------------"
DATABASE_NAME = "TransitData"
CONTAINER_NAME = "Trips"

# Connecting to Azure Cosmos DB for reading trip data.
print("Connecting to Cosmos DB...")
client = CosmosClient.from_connection_string(COSMOS_CONN_STR)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Creating the main search page for entering a bus number.
SEARCH_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TransitSync Live Tracker</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; text-align: center; padding-top: 100px; }
        .container { background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; }
        h1 { color: #333; margin-bottom: 5px; }
        p { color: #666; margin-bottom: 25px; }
        input[type="text"] { padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; width: 250px; }
        button { padding: 12px 20px; font-size: 16px; background-color: #0078D4; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background-color: #005a9e; }
        .error { color: #d93025; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>TransitSync Passenger Portal</h1>
        <p>Enter your bus number to track its live location.</p>
        <form method="POST" action="/">
            <input type="text" name="bus_id" placeholder="e.g., Bus-001" required>
            <button type="submit">Track Bus</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None

    # Handling the search request and reading the bus number entered by the user.
    if request.method == 'POST':
        bus_id = request.form.get('bus_id').strip()

        # Searching the database to check whether the entered bus exists.
        query = "SELECT TOP 1 c.id FROM c WHERE (c.vehicleID = @bus_id OR c.vehicleId = @bus_id)"
        parameters = [{"name": "@bus_id", "value": bus_id}]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        # Showing an error if the bus is not found, or opening the map page if it exists.
        if not items:
            error = f"Bus '{bus_id}' not found. Please check the spelling."
        else:
            return redirect(url_for('show_map', bus_id=bus_id))

    # Rendering the main search page.
    return render_template_string(SEARCH_PAGE_HTML, error=error)


@app.route('/map/<bus_id>')
def show_map(bus_id):

    # Loading all saved GPS records for the selected bus.
    query = """
        SELECT c.vehicleId, c.vehicleID, c.gps.lat, c.gps.lon, c.networkStatusAtCreation, c.timestamp 
        FROM c 
        WHERE IS_DEFINED(c.gps) AND (c.vehicleID = @bus_id OR c.vehicleId = @bus_id)
    """
    parameters = [{"name": "@bus_id", "value": bus_id}]
    items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    # Returning an error message if no trip data is found.
    if not items:
        return "No data found for this bus.", 404

    # Sorting the trip records by time for showing the route in the correct order.
    items.sort(key=lambda x: x.get('timestamp', ''))

    # Centering the map on the latest known location of the bus.
    start_lat = items[-1]['lat']
    start_lon = items[-1]['lon']
    transit_map = folium.Map(location=[start_lat, start_lon], zoom_start=15)

    last_index = len(items) - 1
    for index, item in enumerate(items):
        lat = item.get('lat')
        lon = item.get('lon')
        status = item.get('networkStatusAtCreation')
        bus_name = item.get('vehicleID') or item.get('vehicleId')

        # Using a different marker style for the current location and past locations.
        if index == last_index:
            dot_color = 'blue'
            dot_radius = 9
            popup_text = f"CURRENT LOCATION: {bus_name} | Status: {status}"
        else:
            dot_color = 'green' if status == 'ONLINE' else 'red'
            dot_radius = 6
            popup_text = f"History: {bus_name} | Status: {status}"

        # Adding each bus location as a marker on the map.
        folium.CircleMarker(
            location=[lat, lon],
            radius=dot_radius,
            popup=popup_text,
            color=dot_color,
            fill=True,
            fill_color=dot_color,
            fill_opacity=0.8 if index == last_index else 0.6
        ).add_to(transit_map)

    # Rendering the map directly in the browser.
    return transit_map.get_root().render()


if __name__ == '__main__':

    # Starting the Flask web server on port 5000.
    print("\n" + "=" * 50)
    print("Passenger Portal is LIVE at: http://127.0.0.1:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)