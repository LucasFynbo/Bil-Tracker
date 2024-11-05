import tkinter as tk
from tkinter import messagebox
import requests
from tkintermapview import TkinterMapView
from bleak import BleakClient, BleakError

URL = 'http://localhost:13371/coords'  # Adjust the URL if the Flask server is running on a different address or port

# Create the main window
window = tk.Tk()
window.title("Coordinate Receiver")
window.geometry("320x480")

class CoordinatesHandling:
    def get_coordinates(self, tracker_id, password):
        try:
            # Send HTTP POST request to the Flask backend with tracker ID and password for validation
            response = requests.post(URL, json={'tracker_id': tracker_id, 'password': password})

            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()

                # Extract coordinates from the response if validation succeeds
                if data['status'] == 'success' and 'coords' in data:
                    coords = data['coords']
                    x, y = map(float, coords.split(','))
                    return x, y
                else:
                    messagebox.showerror("Error", f"Error: {data.get('message')}")
            else:
                messagebox.showerror("Error", f"Failed to get coordinates: {response.status_code}")

        except Exception as e:
            messagebox.showerror("Exception", f"Exception occurred while retrieving coordinates: {e}")
        return None, None

    def show_coordinates(self, x, y):
        # Update labels with the received coordinates
        label_received.config(text="Received coordinates")
        label_coordinates.config(text=f"X: {x:.6f}, Y: {y:.6f}")
        
        # Set the map position and marker based on the coordinates
        map_widget.set_position(x, y)
        map_widget.set_marker(x, y, text=f"({x:.6f}, {y:.6f})")

class MainMenu:
    def __init__(self):
        self.master = window
        self.main_menu_frame = tk.Frame(self.master)

        # Initialize handler instances without immediately creating frames
        self.coords_handler = CoordinatesHandling()
        self.locate_tracker = LocateTracker(self.master, self)
        self.setup_tracker = SetupTracker(self.master, self)

        # Main Menu Buttons
        btn_track_location = tk.Button(self.main_menu_frame, text="Track Location", command=self.locate_tracker.show_locate_tracker_view, width=20, height=2)
        # Use lambda to delay calling check_bluetooth_connection until button is clicked
        btn_set_up_tracker = tk.Button(self.main_menu_frame, text="Set up Tracker", command=lambda: self.setup_tracker.check_bluetooth_connection(), width=20, height=2)
        btn_track_location.pack(pady=20)
        btn_set_up_tracker.pack(pady=20)

    def show_main_menu(self):
        # Show the main menu and hide the other frames directly via locate_tracker and setup_tracker attributes
        self.main_menu_frame.pack(fill='both', expand=True)
        self.locate_tracker.tracker_view_frame.pack_forget()
        self.setup_tracker.setup_frame.pack_forget()

class LocateTracker:
    def __init__(self, master, main_menu):
        # Create a dedicated frame for the tracker view
        self.tracker_view_frame = tk.Frame(master)
        self.main_menu = main_menu

        self.locate_tracker_widgets()  # Initialize widgets on this frame

    def show_locate_tracker_view(self):
        # Hide the main menu and setup frames, and show the tracker view frame
        self.main_menu.main_menu_frame.pack_forget()
        self.tracker_view_frame.pack(fill='both', expand=True)
        self.main_menu.setup_tracker.setup_frame.pack_forget()  # Access setup_frame through setup_tracker

    def locate_tracker_widgets(self):
        # Create widgets on the tracker view frame
        label_tracker_id = tk.Label(self.tracker_view_frame, text="Enter Tracker ID:")
        label_tracker_id.pack(pady=5)
        self.entry_tracker_id = tk.Entry(self.tracker_view_frame)
        self.entry_tracker_id.pack(pady=5)

        label_password = tk.Label(self.tracker_view_frame, text="Enter Password:")
        label_password.pack(pady=5)
        self.entry_password = tk.Entry(self.tracker_view_frame, show="*")
        self.entry_password.pack(pady=5)

        btn_get_coordinates = tk.Button(self.tracker_view_frame, text="Get Coordinates", command=self.fetch_and_show_coordinates)
        btn_get_coordinates.pack(pady=10)
        btn_back_to_menu = tk.Button(self.tracker_view_frame, text="Go Back", command=self.main_menu.show_main_menu)
        btn_back_to_menu.pack(pady=5)


        # Create a frame to hold the coordinate labels
        frame_coordinates = tk.Frame(self.tracker_view_frame)
        frame_coordinates.pack(pady=10)

        # Label for received coordinates message
        global label_received
        label_received = tk.Label(frame_coordinates, text="", font=("Arial", 14), fg='darkblue')
        label_received.pack()

        # Label to display X and Y coordinates
        global label_coordinates
        label_coordinates = tk.Label(frame_coordinates, text="", font=("Arial", 8), fg='darkblue')
        label_coordinates.pack()

        # Create the map widget
        global map_widget
        map_widget = TkinterMapView(self.tracker_view_frame, width=250, height=330)
        map_widget.pack(pady=10)

    def fetch_and_show_coordinates(self):
        tracker_id = self.entry_tracker_id.get()
        password = self.entry_password.get()
        if tracker_id and password:
            x, y = self.coords_handler.get_coordinates(tracker_id, password)
            if x is not None and y is not None:
                self.coords_handler.show_coordinates(x, y)
        else:
            messagebox.showwarning("Input Error", "Please enter both Tracker ID and Password.")

class SetupTracker:
    def __init__(self, master, main_menu):
        # Create a dedicated frame for the setup view
        self.setup_frame = tk.Frame(master)
        self.main_menu = main_menu
        self.client = None  # Bluetooth client

        self.setup_tracker_widgets()  # Initialize widgets on this frame

    def setup_tracker_widgets(self):
        # Create widgets on the setup frame
        label_wifi_ssid = tk.Label(self.setup_frame, text="WiFi SSID:")
        label_wifi_ssid.pack(pady=5)
        self.entry_wifi_ssid = tk.Entry(self.setup_frame)
        self.entry_wifi_ssid.pack(pady=5)

        label_wifi_password = tk.Label(self.setup_frame, text="WiFi Password:")
        label_wifi_password.pack(pady=5)
        self.entry_wifi_password = tk.Entry(self.setup_frame, show="*")
        self.entry_wifi_password.pack(pady=5)

        label_tracker_password = tk.Label(self.setup_frame, text="Tracker Password:")
        label_tracker_password.pack(pady=5)
        self.entry_tracker_password = tk.Entry(self.setup_frame, show="*")
        self.entry_tracker_password.pack(pady=5)

        btn_submit_setup = tk.Button(self.setup_frame, text="Submit Setup", command=self.submit_setup)
        btn_submit_setup.pack(pady=10)

        btn_back_from_setup = tk.Button(self.setup_frame, text="Go Back", command=self.main_menu.show_main_menu)
        btn_back_from_setup.pack(pady=5)

    def check_bluetooth_connection(self):
        if self.client and self.client.is_connected:
            self.show_setup_screen()
        else:
            messagebox.showwarning("No Connection", "No active Bluetooth connection to a device, please connect.")

    def show_setup_screen(self):
        # Hide the main menu and tracker frames, and show the setup frame
        self.main_menu.main_menu_frame.pack_forget()
        self.setup_frame.pack(fill='both', expand=True)
        self.main_menu.tracker_view_frame.pack_forget()

    async def connect_to_tracker(self, device_address):
        try:
            self.client = BleakClient(device_address)
            await self.client.connect()
            return True
        except BleakError as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
            return False

    async def submit_setup(self):
        if self.client and self.client.is_connected:
            wifi_ssid = self.entry_wifi_ssid.get()
            wifi_password = self.entry_wifi_password.get()
            tracker_password = self.entry_tracker_password.get()

            # Send these values back to the connected tracker via Bluetooth
            try:
                await self.client.write_gatt_char("characteristic_uuid_for_ssid", wifi_ssid.encode())
                await self.client.write_gatt_char("characteristic_uuid_for_password", wifi_password.encode())
                await self.client.write_gatt_char("characteristic_uuid_for_tracker_password", tracker_password.encode())

                messagebox.showinfo("Setup Complete", "Tracker has been successfully set up.")
            except BleakError as e:
                messagebox.showerror("Error", f"Failed to send data to tracker: {e}")
        else:
            messagebox.showwarning("No Connection", "No active Bluetooth connection to a device, please connect.")


if __name__ == "__main__":
    main_menu = MainMenu()
    # Show the main menu at startup
    main_menu.show_main_menu()

    # Start the GUI loop
    window.mainloop()
