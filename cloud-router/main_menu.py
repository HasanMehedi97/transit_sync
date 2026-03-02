# Importing the required libraries for running other Python scripts from the main menu.
import sys
import subprocess



def print_menu():
    # Displaying the control center menu options to the user.
    print("\n" + "=" * 55)
    print(" TRANSIT SYNC: EDGE-TO-CLOUD CONTROL CENTER ")
    print("=" * 55)
    print(" 1. Launch Interactive GPS Map ")
    print(" 2. Launch Live Seat Viewer")
    print(" 3. Launch Fleet Telemetry Dashboard")
    print(" 4. Exit System")
    print("=" * 55)

def run_script(script_name):
    # Running another Python script using the same Python environment.
    try:
        subprocess.run([sys.executable, script_name])
    except KeyboardInterrupt:
        # Handling manual interruption while running a script.
        print(f"\n[INFO] Closed {script_name}.")
    except Exception as e:
        # Printing an error message if the script cannot be started.
        print(f"\n[ERROR] Failed to run {script_name}. Error: {e}")

def main():
    # Repeating the menu until the user chooses to exit.
    while True:
        print_menu()
        choice = input("Select a dashboard to launch (1-4): ").strip()

        # Launching the GPS map if option 1 is selected.
        if choice == '1':
            print("\n>>> Launching GPS Map...")
            run_script("visualize_map.py")

        # Launching the seat viewer if option 2 is selected.
        elif choice == '2':
            print("\n>>> Launching Seat Viewer...")
            run_script("visualize_seats.py")

        # Launching the telemetry dashboard if option 3 is selected.
        elif choice == '3':
            print("\n>>> Launching Telemetry Dashboard...")
            run_script("visualize_dashboard.py")

        # Closing the program if option 4 is selected.
        elif choice == '4':
            print("\nClosing Control Center. Goodbye!")
            break

        # Showing an error message if the input is invalid.
        else:
            print("\n[ERROR] Invalid selection. Please type 1, 2, 3, or 4.")

if __name__ == "__main__":
    # Starting the control center program.
    main()