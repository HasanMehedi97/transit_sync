# Importing the required libraries for receiving events, storing data, and running asynchronous tasks.
from azure.eventhub.aio import EventHubConsumerClient
from azure.eventhub import TransportType
from azure.cosmos import CosmosClient
import json
import asyncio



# Storing the connection details for Event Hub and Cosmos DB.
EVENT_HUB_CONN_STR = "---------------hidden due to security-------------------------------"".strip()
EVENT_HUB_NAME = "---------------hidden due to security-------------------------------"
COSMOS_CONN_STR = "---------------hidden due to security-------------------------------"
DATABASE_NAME = "TransitData"

# Connecting to Cosmos DB for storing incoming events.
print("Connecting to Cosmos DB...")
cosmos_client = CosmosClient.from_connection_string(COSMOS_CONN_STR)
database = cosmos_client.get_database_client(DATABASE_NAME)

# Defining which event type will be stored in which Cosmos DB container.
CONTAINER_MAPPING = {
    "telemetry": "Telemetry",
    "ticketing": "Ticketing",
    "trip": "Trips",
    "alert": "Alerts"
}

async def on_event(partition_context, event):
    # Receiving one event message from IoT Hub.
    message_body = event.body_as_str(encoding='UTF-8')
    print(f"\n[RECEIVED] Message caught from IoT Hub: {message_body[:60]}...")

    try:
        # Reading the message content and identifying the event type.
        event_data = json.loads(message_body)
        event_type = event_data.get("eventType")

        # Checking whether the event type is valid before processing it.
        if not event_type or event_type not in CONTAINER_MAPPING:
            print(f"[WARNING] Unknown or missing eventType: {event_type}. Skipping.")
            await partition_context.update_checkpoint(event)
            return

        # Selecting the correct Cosmos DB container based on the event type.
        container_name = CONTAINER_MAPPING[event_type]
        container = database.get_container_client(container_name)

        # Creating a document id if one is not already present.
        if 'id' not in event_data:
            event_data['id'] = f"{event_data.get('vehicleID')}-{event_data.get('timestamp')}"

        # Saving the event into Cosmos DB.
        container.upsert_item(body=event_data)
        print(f"[SUCCESS] Routed {event_type} event -> Cosmos DB {container_name} container!")

        # Updating the checkpoint after successful processing.
        await partition_context.update_checkpoint(event)

    except Exception as e:
        # Printing an error message if something goes wrong during processing.
        print(f"[ERROR] Failed to process message: {e}")

async def main():
    # Starting the local router and preparing it to listen for incoming events.
    print(f"Starting Local Cloud Router... Listening to {EVENT_HUB_NAME} on Port 443...")

    # Creating the Event Hub consumer client.
    client = EventHubConsumerClient.from_connection_string(
        conn_str=EVENT_HUB_CONN_STR,
        consumer_group="local-router-group",
        transport_type=TransportType.AmqpOverWebsocket
    )

    # Continuously receiving new events and passing them to the event handler.
    async with client:
        await client.receive(
            on_event=on_event,
            starting_position="@latest",
        )

if __name__ == "__main__":
    try:
        # Running the router program.
        asyncio.run(main())
    except KeyboardInterrupt:
        # Stopping the router safely when interrupted by the user.
        print("\nRouter stopped manually.")