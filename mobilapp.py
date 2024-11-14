import tkinter as tk
from tkinter import messagebox
import requests
from tkintermapview import TkinterMapView

import asyncio
import threading
from bleak import BleakScanner, BleakClient
import queue
import time

URL = 'http://79.171.148.143/api'  # Adjust the URL if the Flask server is running on a different address or port

# Create the main window
window = tk.Tk()
window.title("Coordinate Receiver")
window.geometry("320x480")

CHARACTERISTIC_UUID_WIFI_SSID = "841677b2-99fe-4175-9fc9-033ac6c85a54"
CHARACTERISTIC_UUID_WIFI_PASSWORD = "dfc2c17e-9f7f-480e-82e4-b540a21ebf0b"
CHARACTERISTIC_UUID_TRACKER_PASSWORD = "1370af71-05bd-42cd-9604-72667f439c42"

TARGET_DEVICE_NAME = "car_tracker"

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
    def __init__(self, master):
        self.main_menu_frame = tk.Frame(master)

        # Initialize handler instances without immediately creating frames
        self.coords_handler = CoordinatesHandling()
        self.locate_tracker = LocateTracker(master, self)
        self.setup_tracker = SetupTracker(master, self)

        # Main Menu Buttons
        btn_track_location = tk.Button(self.main_menu_frame, text="Track Location", command=self.locate_tracker.show_locate_tracker_view, width=20, height=2)
        btn_set_up_tracker = tk.Button(self.main_menu_frame, text="Set up Tracker", command=self.setup_tracker.queue_ble_scan, width=20, height=2)
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
        self.device_list = []
        
        self.ble_to_main_queue = queue.Queue()
        self.client = None

        self.setup_tracker_widgets()  # Initialize widgets on this frame

        self.ble_thread = threading.Thread(target=self.ble_thread_loop)
        self.ble_thread.start()

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

    def ble_thread_loop(self):
        """Runs in a separate thread, manages the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_forever()
        except Exception as e:
            print("Error in BLE thread loop:", e)
        finally:
            self.loop.close()

    def queue_ble_scan(self):
        """Queue a BLE scan task from the main Tkinter thread."""
        asyncio.run_coroutine_threadsafe(self.bluetooth_scan(), self.loop)

    async def bluetooth_scan(self):
        """Async Bluetooth scanning function."""
        self.device_list = await BleakScanner.discover()
        target_device = None

        for device in self.device_list:
            print(f"Found device: {device.name} ({device.address})")
            if device.name == TARGET_DEVICE_NAME:
                target_device = device
                break

        if target_device is None:
            print(f"Device {TARGET_DEVICE_NAME} not found.")
            messagebox.showerror("Connection Error", f"Device {TARGET_DEVICE_NAME} not found.")
            return
        
        print(f"Connecting to device {TARGET_DEVICE_NAME} ({target_device.address})...")
        self.client = BleakClient(target_device.address)

        # Try connecting and then display the setup screen if successful
        try:
            await self.client.connect()
            if self.client.is_connected:
                print(f"Successfully connected to {TARGET_DEVICE_NAME}!")
                await self.show_setup_screen()  # Move to setup screen upon successful connection
            else:
                messagebox.showerror("Connection Error", f"Failed to connect to {TARGET_DEVICE_NAME}.")
        except Exception as e:
            print(f"Failed to connect to {TARGET_DEVICE_NAME}: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect to {TARGET_DEVICE_NAME}: {str(e)}")

    async def show_setup_screen(self):
        # Hide the main menu and tracker frames, and show the setup frame
        self.main_menu.main_menu_frame.pack_forget()
        self.setup_frame.pack(fill='both', expand=True)

    def submit_setup(self):
        asyncio.run_coroutine_threadsafe(self.write_to_gatt_services(), self.loop)

    async def write_to_gatt_services(self):
        """Writes Wi-Fi and tracker credentials to the device's GATT services."""
        ssid = self.entry_wifi_ssid.get()
        password = self.entry_wifi_password.get()
        tracker_password = self.entry_tracker_password.get()

        # Debug: Log the values being written
        print(f"SSID: {ssid}, Password: {password}, Tracker Password: {tracker_password}")

        try:
            # Ensure the client is connected before writing
            if self.client.is_connected:
                print("Client is connected, writing to GATT services...")

                # Write each characteristic
                await self.client.write_gatt_char(CHARACTERISTIC_UUID_WIFI_SSID, ssid.encode())
                await self.client.write_gatt_char(CHARACTERISTIC_UUID_WIFI_PASSWORD, password.encode())
                await self.client.write_gatt_char(CHARACTERISTIC_UUID_TRACKER_PASSWORD, tracker_password.encode())

                print("GATT services written successfully.")

                # Show success message and return to the main menu
                messagebox.showinfo("Setup Successful", "Configuration completed successfully.")
                self.close_setup_screen()
            else:
                print("Client is not connected.")
                messagebox.showerror("Setup Error", "Device is not connected.")
        except Exception as e:
            print(f"Write error: {str(e)}")
            messagebox.showerror("Setup Error", f"Failed to write to GATT services: {str(e)}")

    def close_setup_screen(self):
        """Close setup frame and return to main menu."""
        self.setup_frame.pack_forget()
        self.main_menu.show_main_menu()
        if self.client and self.client.is_connected:
            asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)

if __name__ == "__main__":
    main_menu = MainMenu(window)
    # Show the main menu at startup
    main_menu.show_main_menu()

    # Start the GUI loop
    window.mainloop()
