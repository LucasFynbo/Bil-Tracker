import tkinter as tk
import socket
from tkintermapview import TkinterMapView

def start_socket_server():
    # Start en socket-server til at modtage koordinater
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("localhost", 65432))  # Brug en unik port
    server.listen(1)
    print("Serveren venter på forbindelse...")
    conn, addr = server.accept()
    print(f"Forbundet til: {addr}")

    # Modtag data (forvent to tal adskilt af komma, f.eks. "10,20")
    data = conn.recv(1024).decode()
    conn.close()

    # Opdel koordinaterne7
    x, y = data.split(",")
    return float(x), float(y)

def show_coordinates(x, y):
    # Opdater labels med de modtagne koordinater
    label_received.config(text="Modtaget koordinator")
    label_coordinates.config(text=f"X koordinat: {x:.6f}, Y koordinat: {y:.6f}")
    map_widget.set_position(x, y)
    map_widget.set_marker(x, y, text=f"({x:.6f}, {y:.6f})")

# Start socket-serveren og få koordinaterne
x_coord, y_coord = start_socket_server()

# Opret hovedvinduet
window = tk.Tk()
window.title("Koordinatmodtager")
window.geometry("320x480")

# Opret en ramme til at holde koordinaterne
frame_coordinates = tk.Frame(window)
frame_coordinates.pack(pady=10)

# Opret labels til at vise de modtagne koordinater
label_received = tk.Label(frame_coordinates, text="Modtaget koordinator", font=("Arial", 14), fg='darkblue')
label_received.pack()

label_coordinates = tk.Label(frame_coordinates, text="", font=("Arial", 8), fg='darkblue')
label_coordinates.pack()

# Opret kort-widget
map_widget = TkinterMapView(window, width=250, height=330)
map_widget.pack(pady=10)

# Opdater labels med modtagne værdier
show_coordinates(x_coord, y_coord)

# Start GUI-løkken
window.mainloop()




