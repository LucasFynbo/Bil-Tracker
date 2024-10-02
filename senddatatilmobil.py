import socket

def send_coordinates(x, y):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("localhost", 65432))  # Forbind til serveren
    coordinates = f"{x},{y}"  # Formatér data som "x,y"
    client.sendall(coordinates.encode())  # Send data
    client.close()  # Luk forbindelsen

# Eksempel på at sende koordinater
send_coordinates(55.7123, 12.0564)  # Eksempelkoordinater for København

