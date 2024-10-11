from machine import I2C, Pin, UART
import time
import MPU6050
import ConnectHandler
import urequests
import ujson as json

class SendData:
    def __init__(self, server_url, tracker_id=None):

        self.server_url = server_url
        self.tracker_id = tracker_id

    def send_data(self, type=None, gps=None):

        if 'tracker id request' == type:
            try:
                data_packet = {
                    'data': 'tracker id request',					
                }

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(self.server_url, json=data_packet)

                response_data = response.json()

                if response_data[0]['status'] == 'success':
                    print(f"Server response: {response.text}")

                    # Måske skal det være [0] eller [2] idk...
                    self.tracker_id = response_data[2]['tracker_id']

                    with open('tracker_id.txt', 'w') as file:
                        file.write(f"TrackerID:{self.tracker_id}")

                    print("[+] Tracker id request successfully handled")

                else:
                    print("[!] Error handeling tracker id request response.")	

            except Exception as e:
                print(f"Unhandled exception: {e}")


        elif 'send gps coordinates' == type:
            try:                
                data_packet = {
                    'data': 'received coords',	
                    'coords': gps,
                    'tracker_id': self.tracker_id				
                }

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(self.server_url, json=data_packet)

            except Exception as e:
                print(f"Unhandled exception: {e}")


def tracker_id_control():
    # Kontroller om der allerede er genereret et Tracker ID for enheden
    try:
        with open('tracker_id.txt', 'r') as file:
            credentials_file = file.read()
        
        # Hvis filen indeholdende tracker ID'et står tomt
        if '' == credentials_file:
            print("[!] Tracker ID file empty, requesting...")
            SendData.send_data(type='tracker id request')
        # Hvis Tracker ID'et allerede er skabt for enheden
        else:
            for line in credentials_file.split('\n'):
                if "TrackerID:" in line:
                    tracker_id = line.split(':')[1].strip()
            print(f"[+] Tracker ID: {tracker_id}")
            return tracker_id
            
    except OSError as e:
        # Hvis filen ikke eksisterer
        if errno.ENOENT == e.errno:
            print("[!] Tracker ID does not exist, requesting...")
            SendData.send_data(type='tracker id request')
        # Andre errors
        else:
            print("[!] Error: '%s' occured." % e)

class GPS:
    def __init__(self):
        # Initialize UART for the GPS
        self.uart = UART(2, baudrate=9600, bits=8, parity=None, stop=1, tx=43, rx=44, timeout=300)

    def convert_to_decimal(self, degrees, minutes, direction):
        # Convert degrees and minutes to decimal
        decimal = float(degrees) + (float(minutes) / 60.0)
        if direction in ['S', 'W']:
            decimal *= -1  # Convert to negative for South and West
        return decimal

    def read_gps(self):
        while True:
            new_msg = self.uart.readline()

            if new_msg:
                try:
                    # Attempt to decode as UTF-8
                    nmea_sentence = new_msg.decode('utf-8').strip()

                    # Filter out GPTXT messages
                    if nmea_sentence.startswith('$GPTXT'):
                        print("[!] Debug message, skipping...")
                        continue

                    # Print NMEA sentence for debugging
                    print(nmea_sentence)

                    # Split the sentence into parts
                    fields = nmea_sentence.split(',')

                    # Handle GPRMC, GPGGA, and GPGLL within the same function
                    if nmea_sentence.startswith('$GPRMC') and len(fields) >= 12 and fields[2] == 'A':
                        latitude = self.convert_to_decimal(fields[3][:2], fields[3][2:], fields[4])
                        longitude = self.convert_to_decimal(fields[5][:3], fields[5][3:], fields[6])
                        return latitude, longitude

                    elif nmea_sentence.startswith('$GPGGA') and len(fields) >= 9 and fields[6] == '1':
                        latitude = self.convert_to_decimal(fields[2][:2], fields[2][2:], fields[3])
                        longitude = self.convert_to_decimal(fields[4][:3], fields[4][3:], fields[5])
                        return latitude, longitude

                    elif nmea_sentence.startswith('$GPGLL') and len(fields) >= 7 and fields[6] == 'A':
                        latitude = self.convert_to_decimal(fields[1][:2], fields[1][2:], fields[2])
                        longitude = self.convert_to_decimal(fields[3][:3], fields[3][3:], fields[4])
                        return latitude, longitude

                    else:
                        print("[!] No valid GPS fix yet, retrying...")

                except Exception as e:
                    # Handle decoding errors or unexpected sentence format
                    print("[!] Error while processing message: ", new_msg, "\nError: ", str(e))

            else:
                print("[!] No message received.")

            # Sleep briefly to avoid spamming the GPS module
            time.sleep(1)

class Accelerometer:
    def __init__(self):
        # Set up the I2C interface
        i2c = I2C(1, sda=Pin(8), scl=Pin(9))

        # Set up the MPU6050 class 
        self.mpu = MPU6050.MPU6050(i2c)

        # Wake up the MPU6050 from sleep
        self.mpu.wake()

        self.gps = GPS()
        self.send = SendData()

        # Flag to track if GPS data has been sent
        self.gps_data_sent = False

    def read(self):
        while True:  # Loop continuously
            current_accel = abs(self.mpu.read_accel_data())

            print("Accel: %.2f" % current_accel)

            # Check if the current acceleration exceeds the threshold
            if current_accel > 0.24:  # Acceleration exceeds threshold
                print("[+] Acceleration threshold exceeded, acquiring GPS data...")

                if not self.gps_data_sent:
                    # Get GPS data
                    gps_data = self.gps.read_gps()

                    if gps_data:
                        # Send GPS data
                        self.send.send_data("send gps coordinates", gps_data)
                        self.gps_data_sent = True  # Mark that data has been sent

                    # Start a grace period after sending GPS data
                    start_time = time.time()

                    # 5-second grace period
                    while time.time() - start_time < 5:
                        # Continuously check accelerometer data
                        current_accel = abs(self.mpu.read_accel_data())
                        print("Accel during grace period: %.2f" % current_accel)

                        # If acceleration exceeds 0.0 during grace period, break out
                        if current_accel > 0.0:
                            print("[+] Acceleration is above 0.0 during grace period, allowing further GPS requests...")
                            break
                        
                        time.sleep(0.5)

                print("[+] Grace period ended, checking for acceleration drop...")

                # After grace period, check if acceleration is still above threshold
                if current_accel <= 0.0:
                    print("[!] Acceleration dropped to 0.0, resetting GPS state.")
                    self.gps_data_sent = False  # Reset for next GPS send

            elif current_accel > 0.10 and self.gps_data_sent:
                print("[+] Current acceleration is above 0.0, checking for new GPS data...")
                # Keep requesting new GPS data
                gps_data = self.gps.read_gps()

                if gps_data:
                    self.send.send_data("send gps coordinates", gps_data)  # Send GPS data while acceleration > 0.0

            else:
                print("[!] Current acceleration not above threshold, waiting for next movement...")
            
            time.sleep(0.5)  # Optional delay to avoid excessive processing

if __name__ == "__main__":
    connect = ConnectHandler.getip("BibNet", "")
    print(f"Received IP: {connect}")
    
    time.sleep(2)
    
    MPU = Accelerometer()
    
    MPU.read()  # Start reading accelerometer data

