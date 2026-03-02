# Importing the required libraries for file handling, random event generation, time tracking, and IoT Hub communication.
import json
import random
import shutil
import time
import os
from pathlib import Path
from datetime import datetime, UTC
from azure.iot.device import IoTHubDeviceClient, Message



# Setting the main file paths and folder locations used by the simulator.
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"
PENDING_DIR = BASE_DIR / "data" / "pending"
SYNCED_DIR = BASE_DIR / "data" / "synced"
ALERT_LOG_PATH = BASE_DIR / "src" / "alerts.log"
STATE_FILE = BASE_DIR / "data" / "local_seat_state.json"

# Creating the pending and synced folders if they do not already exist.
PENDING_DIR.mkdir(parents=True, exist_ok=True)
SYNCED_DIR.mkdir(parents=True, exist_ok=True)

# Reading the system settings from the configuration file.
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    settings = json.load(f)

# Storing the main configuration values for the simulator and sync process.
CONNECTION_STRING = settings["iot_hub_connection_string"]
VEHICLE_ID = settings["vehicle_id"]
IS_ONLINE = settings["is_online"]
MAX_RETRIES = 3
BASE_BACKOFF_DELAY = 2

# Creating the full list of bus seats from A1 to J4.
ALL_SEATS = [f"{chr(row)}{col}" for row in range(65, 75) for col in range(1, 5)]

def load_seat_state():
    # Reading the saved seat state from the local storage file.
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_seat_state(state):
    # Saving the current seat state to the local storage file.
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

def generate_base_event(event_type):
    # Creating the common event structure used by all event types.
    return {
        "vehicleID": VEHICLE_ID,
        "eventType": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "networkStatusAtCreation": "ONLINE" if IS_ONLINE else "OFFLINE"
    }

def generate_trip():
    # Creating a trip event with route, GPS location, and speed data.
    event = generate_base_event("trip")
    event.update({
        "routeId": "DHAKA-R1",
        "gps": {
            "lat": round(23.8103 + random.uniform(-0.01, 0.01), 6),
            "lon": round(90.4125 + random.uniform(-0.01, 0.01), 6),
            "speed": random.randint(20, 65)
        }
    })
    return event

def generate_telemetry():
    # Creating a telemetry event with fuel and engine temperature values.
    event = generate_base_event("telemetry")
    event.update({
        "fuelLevel": random.randint(30, 100),
        "engineTemp": random.randint(75, 105)
    })
    return event

def generate_ticketing():
    # Creating a ticketing event and updating the saved seat state.
    event = generate_base_event("ticketing")
    vehicle_id = event["vehicleID"]

    # Reading the saved seat state for the current vehicle.
    bus_seat_state = load_seat_state()
    currently_occupied = bus_seat_state.get(vehicle_id, [])

    # Finding the seats that are still available.
    available_seats = [seat for seat in ALL_SEATS if seat not in currently_occupied]

    seat_sold_now = None

    # Selling a seat randomly if empty seats are available.
    if available_seats and random.choice([True, False]):
        seat_sold_now = random.choice(available_seats)
        currently_occupied.append(seat_sold_now)

        # Updating and saving the new seat state immediately.
        bus_seat_state[vehicle_id] = currently_occupied
        save_seat_state(bus_seat_state)

    # Adding the latest seat information into the event data.
    event.update({
        "seatsOccupied": currently_occupied.copy(),
        "seatSoldNow": seat_sold_now
    })
    return event

def save_event_to_pending(event_data):
    # Saving each generated event as a JSON file in the pending folder.
    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    event_type = event_data["eventType"]
    file_path = PENDING_DIR / f"{event_type}_{timestamp_str}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(event_data, f, indent=2)
    print(f"Created pending file: {file_path.name}")
    return event_data

if __name__ == "__main__":
    # Starting the edge simulator.
    print("--- Edge Simulator Started ---")

    # Generating and saving trip, telemetry, and ticketing events.
    trip_data = save_event_to_pending(generate_trip())
    telemetry_data = save_event_to_pending(generate_telemetry())
    ticketing_data = save_event_to_pending(generate_ticketing())

    # Checking whether alert conditions are triggered.
    engine_temp = telemetry_data["engineTemp"]
    fuel_level = telemetry_data["fuelLevel"]

    # Creating and saving an alert event if engine temperature is too high or fuel is too low.
    if engine_temp > 95 or fuel_level < 40:
        alert_event = generate_base_event("alert")
        alert_event["alerts"] = []
        if engine_temp > 95:
            alert_event["alerts"].append("HIGH_ENGINE_TEMP")
        if fuel_level < 40:
            alert_event["alerts"].append("LOW_FUEL")

        save_event_to_pending(alert_event)

        # Writing the alert details into the local alert log file.
        with open(ALERT_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(f"{datetime.now(UTC).isoformat()} | {alert_event['alerts']}\n")

    # Reading all pending files that are waiting to be synchronized.
    pending_files = list(PENDING_DIR.glob("*.json"))
    print(f"\nPending files waiting for sync: {len(pending_files)}")

    # Stopping the sync process if the system is offline.
    if not IS_ONLINE:
        print("System is offline. Files will stay in pending folder.")
        raise SystemExit()

    # Stopping the program if there are no files to upload.
    if not pending_files:
        print("No pending JSON files found.")
        raise SystemExit()

    # Connecting to Azure IoT Hub for uploading the pending files.
    print("\n--- Network Online: Initiating Cloud Sync ---")
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    client.connect()
    uploaded_count = 0

    try:
        # Reading each pending file one by one for cloud synchronization.
        for file_path in pending_files:
            with open(file_path, "r", encoding="utf-8") as f:
                event_data = json.load(f)

            # Adding synchronization time and delay information into the event data.
            created_time = datetime.fromisoformat(event_data["timestamp"])
            synced_time = datetime.now(UTC)
            event_data["syncedAt"] = synced_time.isoformat()
            event_data["syncDelaySeconds"] = int((synced_time - created_time).total_seconds())

            # Trying to send the event with retry and exponential backoff.
            sync_success = False
            for attempt in range(MAX_RETRIES):
                try:
                    msg = Message(json.dumps(event_data))
                    msg.content_encoding = "utf-8"
                    msg.content_type = "application/json"
                    client.send_message(msg)
                    sync_success = True
                    break
                except Exception as e:
                    wait_time = BASE_BACKOFF_DELAY ** attempt
                    print(f"Sync failed for {file_path.name}. Retrying in {wait_time}s... (Error: {e})")
                    time.sleep(wait_time)

            # Updating the file and moving it to the synced folder after a successful upload.
            if sync_success:
                updated_json = json.dumps(event_data, indent=2)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_json)

                destination_path = SYNCED_DIR / file_path.name
                shutil.move(str(file_path), str(destination_path))
                uploaded_count += 1
                print(f"Uploaded & Moved to synced: {destination_path.name}")
            else:
                # Keeping the file in the pending folder if all retries fail.
                print(f"ERROR: Max retries reached for {file_path.name}. Retained in pending.")

    finally:
        # Disconnecting from IoT Hub after finishing the sync process.
        client.disconnect()

    # Printing the total number of files uploaded in this run.
    print(f"\nFiles synchronized in this run: {uploaded_count}")