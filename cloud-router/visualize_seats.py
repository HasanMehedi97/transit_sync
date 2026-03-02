from azure.cosmos import CosmosClient
import webbrowser
import os

# Importing the required libraries for reading database data, creating the seat map file, and opening it in the browser.

# Storing the database connection details and selecting the database and container.
COSMOS_CONN_STR = "---------------hidden due to security-------------------------------"
DATABASE_NAME = "TransitData"
CONTAINER_NAME = "Ticketing"

# Connecting to Cosmos DB for reading ticketing data.
print("Connecting to Cosmos DB...")
client = CosmosClient.from_connection_string(COSMOS_CONN_STR)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Asking the user to enter the bus ID for the live seat map.
target_bus = input("\nEnter the Bus ID to view its live seat map (e.g., Bus-001): ").strip()

# Writing the query for reading the most recent ticketing event of the selected bus.
query = """
    SELECT TOP 1 c.seatsOccupied, c.timestamp 
    FROM c 
    WHERE c.eventType = 'ticketing' AND c.vehicleID = @bus_id 
    ORDER BY c.timestamp DESC
"""

# Passing the user input safely into the query.
parameters = [{"name": "@bus_id", "value": target_bus}]

# Searching the database for the latest seat data of the selected bus.
print(f"Fetching the latest ticketing data for {target_bus}...")
items = list(container.query_items(
    query=query,
    parameters=parameters,
    enable_cross_partition_query=True
))

# Showing an error if no ticketing data is found.
if not items:
    print(f"\n[ERROR] No ticketing data found for '{target_bus}'. Has it sold any tickets yet?")
else:
    # Extracting the latest seat information from the query result.
    latest_event = items[0]
    occupied_seats = latest_event.get("seatsOccupied", [])
    last_updated = latest_event.get("timestamp")

    # Creating the HTML content for the seat map page.
    html_content = f"""
    <html>
    <head>
        <title>{target_bus} - Live Seat Map</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; text-align: center; padding: 20px; }}
            h1 {{ color: #333; }}
            .stats {{ margin-bottom: 20px; font-size: 1.2em; }}
            .bus-container {{ background-color: #ddd; padding: 30px; border-radius: 20px; display: inline-block; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }}
            .row {{ display: flex; justify-content: center; margin-bottom: 10px; }}
            .seat {{ width: 50px; height: 50px; line-height: 50px; margin: 0 5px; border-radius: 8px; font-weight: bold; color: white; }}
            .aisle {{ width: 40px; }}
            .occupied {{ background-color: #e74c3c; }}
            .available {{ background-color: #2ecc71; }}
            .legend-dot {{ display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px; }}
        </style>
    </head>
    <body>
        <h1>Live Seat Map: {target_bus}</h1>
        <div class="stats">
            <span class="legend-dot occupied"></span> <strong>Occupied:</strong> {len(occupied_seats)} / 40 &nbsp;&nbsp;&nbsp;
            <span class="legend-dot available"></span> <strong>Available:</strong> {40 - len(occupied_seats)} / 40 <br>
            <small style="color: #666; display: block; margin-top: 10px;">Last Sync: {last_updated}</small>
        </div>
        
        <div class="bus-container">
    """

    # Building the seat layout row by row.
    for row_char in range(65, 75):
        row_letter = chr(row_char)
        html_content += '<div class="row">'

        # Building the seats in each row and checking whether each seat is occupied.
        for col_num in range(1, 5):
            seat_id = f"{row_letter}{col_num}"
            status_class = "occupied" if seat_id in occupied_seats else "available"
            html_content += f'<div class="seat {status_class}">{seat_id}</div>'

            # Adding the middle aisle between the two seat groups.
            if col_num == 2:
                html_content += '<div class="aisle"></div>'

        html_content += '</div>'

    # Finishing the HTML content for the seat map page.
    html_content += """
        </div>
    </body>
    </html>
    """

    # Saving the generated seat map as an HTML file.
    html_file = f"seat_map_{target_bus}.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Opening the generated seat map file in the browser.
    print("Seat map generated successfully! Opening in browser...")
    webbrowser.open("file://" + os.path.realpath(html_file))