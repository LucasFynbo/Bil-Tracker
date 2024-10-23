import tkinter as tk
import requests
from tkintermapview import TkinterMapView

def get_coordinates(tracker_id):
    try:
        # Send HTTP POST request to the Flask backend to get the most recent coordinates
        url = 'http://localhost:13371/coords'  # Adjust the URL if the Flask server is running on a different address or port
        response = requests.post(url, json={'tracker_id': tracker_id})

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()

            # Extract coordinates from the response
            if data['status'] == 'success' and 'coords' in data:
                # Expecting coords in "x_value,y_value" format
                coords = data['coords']
                x, y = map(float, coords.split(','))
                show_coordinates(x, y)
            else:
                print(f"Error: {data.get('message')}")
        else:
            print(f"Failed to get coordinates: {response.status_code}")

    except Exception as e:
        print(f"Exception occurred while retrieving coordinates: {e}")

def show_coordinates(x, y):
    # Update labels with the received coordinates
    label_received.config(text="Received coordinates")
    label_coordinates.config(text=f"X: {x:.6f}, Y: {y:.6f}")
    
    # Set the map position and marker based on the coordinates
    map_widget.set_position(x, y)
    map_widget.set_marker(x, y, text=f"({x:.6f}, {y:.6f})")

# Create the main window
window = tk.Tk()
window.title("Coordinate Receiver")
window.geometry("320x480")

# Create a frame to hold the coordinate labels
frame_coordinates = tk.Frame(window)
frame_coordinates.pack(pady=10)

# Label for received coordinates message
label_received = tk.Label(frame_coordinates, text="Received coordinates", font=("Arial", 14), fg='darkblue')
label_received.pack()

# Label to display X and Y coordinates
label_coordinates = tk.Label(frame_coordinates, text="", font=("Arial", 8), fg='darkblue')
label_coordinates.pack()

# Create the map widget
map_widget = TkinterMapView(window, width=250, height=330)
map_widget.pack(pady=10)

# Replace 'Tracker#12345' with the actual tracker ID you're testing with
tracker_id = 'Tracker#12345'  # Example tracker ID
get_coordinates(tracker_id)  # Fetch the latest coordinates for this tracker ID

# Start the GUI loop
window.mainloop()
