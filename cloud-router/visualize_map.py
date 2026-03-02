# Importing the required libraries for reading trip data, creating the map, and opening it in the browser.
from azure.cosmos import CosmosClient
import folium
import webbrowser
import os



# Storing the database connection details and selecting the database and container.
COSMOS_CONN_STR = "---------------hidden due to security-------------------------------"
DATABASE_NAME = "TransitData"
CONTAINER_NAME = "Trips"

# Connecting to Cosmos DB for reading trip location data.
print("Connecting to Cosmos DB...")
client = CosmosClient.from_connection_string(COSMOS_CONN_STR)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Asking the user to enter the bus ID to visualize.
target_bus = input("\nEnter the Bus ID you want to visualize (e.g., Bus-001 or Bus-002): ").strip()

# Writing the query for reading GPS records for the selected bus.
query = """
    SELECT c.vehicleId, c.vehicleID, c.gps.lat, c.gps.lon, c.networkStatusAtCreation, c.timestamp 
    FROM c 
    WHERE IS_DEFINED(c.gps) AND (c.vehicleID = @bus_id OR c.vehicleId = @bus_id)
"""

# Passing the user input safely into the query.
parameters = [
    {"name": "@bus_id", "value": target_bus}
]

# Searching the database for GPS data of the selected bus.
print(f"Searching database for {target_bus}...")
items = list(container.query_items(
    query=query,
    parameters=parameters,
    enable_cross_partition_query=True
))

# Showing an error if no GPS records are found.
if not items:
    print(f"\n[ERROR] No GPS data found for '{target_bus}'! Check the exact spelling and try again.")
else:
    # Sorting the GPS records by time for placing the route points in the correct order.
    items.sort(key=lambda x: x.get('timestamp', ''))

    # Printing the number of points found and preparing the map.
    print(f"\nFound {len(items)} location points for {target_bus}. Generating map...")

    # Centering the map on the first available GPS point.
    start_lat = items[0]['lat']
    start_lon = items[0]['lon']
    transit_map = folium.Map(location=[start_lat, start_lon], zoom_start=14)

    last_index = len(items) - 1

    # Going through each GPS point and preparing the marker details.
    for index, item in enumerate(items):
        lat = item.get('lat')
        lon = item.get('lon')
        status = item.get('networkStatusAtCreation')
        bus_name = item.get('vehicleID') or item.get('vehicleId')

        # Using a different marker style for the current location and historical locations.
        if index == last_index:
            dot_color = 'blue'
            dot_radius = 9
            popup_text = f"CURRENT LOCATION - Bus: {bus_name} | Status: {status}"
        else:
            dot_color = 'green' if status == 'ONLINE' else 'red'
            dot_radius = 6
            popup_text = f"Bus: {bus_name} | Status: {status}"

        # Adding each GPS point to the map.
        folium.CircleMarker(
            location=[lat, lon],
            radius=dot_radius,
            popup=popup_text,
            color=dot_color,
            fill=True,
            fill_color=dot_color,
            fill_opacity=0.8 if index == last_index else 0.6
        ).add_to(transit_map)

    # Saving the generated map as an HTML file.
    html_file = f"dhaka_transit_map_{target_bus}.html"
    transit_map.save(html_file)

    # Opening the saved map file in the browser.
    print("Map generated successfully! Opening in browser...")
    webbrowser.open("file://" + os.path.realpath(html_file))