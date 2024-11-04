from machine import I2C, Pin, UART
import time
import captive_portal
import urequests
import ujson as json
import os

SERVER_URL = "http://79.171.148.143/api"
TRACKER_ID = None


class HTTPServer:
    def send_data(type=None, gps=None):
        global TRACKER_ID

        if 'tracker id request' == type:
            try:
                data_packet = {
                    'data': 'tracker id request'				
                }

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(SERVER_URL, json=data_packet)

                print(f"Server response: {response.text}")

                response_data = response.json()

                if response_data['status'] == 'success':
                    TRACKER_ID = response_data['tracker_id']

                    with open('tracker_id.txt', 'w') as file:
                        file.write(f"TrackerID:{TRACKER_ID}")

                    print("[+] Tracker id request successfully handled")

                else:
                    print("[!] Error handeling tracker id request response.")	

            except Exception as e:
                print(f"Unhandled exception: {e}")


        elif 'send gps coordinates' == type:

            try:                
                data_packet = {
                    'data': 'received coords',	
                    'coords_lat': f"{gps[0]}",
                    'coords_long': f"{gps[1]}",
                    'tracker_id': TRACKER_ID				
                }

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(SERVER_URL, json=data_packet)

            except Exception as e:
                print(f"Unhandled exception: {e}")


        elif 'password reset procedure' == type:
            
            try:
                data_packet = {
                            'data': 'wipe password request',    
                            'tracker_id': TRACKER_ID                
                        }
                        
                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(SERVER_URL, json=data_packet)
                        
            except Exception as e:
                print(f"Unhandled exception: {e}")

def tracker_id_control():
    global TRACKER_ID
    
    # Kontroller om der allerede er genereret et Tracker ID for enheden
    try:
        with open('tracker_id.txt', 'r') as file:
            credentials_file = file.read()
        
        # Hvis filen indeholdende tracker ID'et står tomt
        if '' == credentials_file:
            print("[!] Tracker ID file empty, requesting...")
            HTTPServer.send_data(type='tracker id request')
        # Hvis Tracker ID'et allerede er skabt for enheden
        else:
            for line in credentials_file.split('\n'):
                if "TrackerID:" in line:
                    TRACKER_ID = line.split(':')[1].strip()
            print(f"[+] Tracker ID: {TRACKER_ID}")
            
    except OSError as e:
        # Hvis filen ikke eksisterer
        if errno.ENOENT == e.errno:
            print("[!] Tracker ID does not exist, requesting...")
            HTTPServer.send_data(type='tracker id request')
        # Andre errors
        else:
            print("[!] Error: '%s' occured." % e)


class ResetButton:
    def __init__(self):
        self.reset_button_pin = 13  # Pin for reset button
        self.led_pin = 12           # Pin for LED
        self.reset_button = Pin(self.reset_button_pin, Pin.IN, Pin.PULL_UP)
        self.led = Pin(self.led_pin, Pin.OUT)
        self.file_path = 'network_credentials.txt'
        
        self.press_start = None  # To track button press start time
        self.reset_button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.handle_button_press)
        
    def handle_button_press(self, pin):
        """Interrupt handler to monitor the button press asynchronously."""
        if pin.value() == 0:  # Button is pressed
            self.press_start = time.time()
            self.led.on()  # Turn LED on
            self.monitor_button()  # Start monitoring button duration
        else:  # Button released
            press_duration = time.time() - self.press_start if self.press_start else 0
            self.led.off()
            
            if 10 <= press_duration < 30:
                self.perform_reset(level=1)
            elif press_duration >= 30:
                self.perform_reset(level=2)
                
            self.press_start = None  # Reset the press start time

    def blink_led(self, times, interval_ms):
        for _ in range(times):
            self.led.on()
            time.sleep_ms(interval_ms)
            self.led.off()
            time.sleep_ms(interval_ms)

    def delete_file(self):
        try:
            os.remove(self.file_path)
            print("File deleted.")
        except OSError:
            print("File does not exist or could not be deleted.")
            
    def perform_reset(self, level):
        if level == 1:
            self.delete_file()
            self.blink_led(5, 250)
        elif level == 2:
            print("running password reset procedure")
            HTTPServer.send_data(type="password reset procedure")
            self.blink_led(5, 250)

    def monitor_button(self):
        press_duration = 0  # Duration counter
        blinked_10s = False  # Flag for 10s blink
        blinked_30s = False  # Flag for 30s blink

        while self.reset_button.value() == 0:  # While button is pressed
            press_duration = time.time() - self.press_start  # Update duration
            
            if press_duration >= 30 and not blinked_30s:  # If pressed for 30 seconds
                self.led.off()
                self.blink_led(5, 250)  # Blink for 30 seconds
                self.perform_reset(level=2)  # Perform level 2 reset
                blinked_30s = True  # Set flag to indicate the 30s blink has occurred
                return  # Exit after handling the 30s reset

            elif press_duration >= 10 and not blinked_10s:  # If pressed for 10 seconds
                self.led.off()
                self.blink_led(5, 250)  # Blink for 10 seconds
                self.perform_reset(level=1)
                blinked_10s = True  # Set flag to indicate the 10s blink has occurred

            self.led.on()
            time.sleep(1)  # Wait for a second before the next check

        # Reset flags when the button is released
        blinked_10s = False
        blinked_30s = False
        self.led.off()



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

    def check_speed(self):
        """Check the speed from the GPRMC sentence and return True if moving."""
        new_msg = self.uart.readline()
        if new_msg:
            try:
                nmea_sentence = new_msg.decode('utf-8').strip()
                
                print(nmea_sentence)
                
                fields = nmea_sentence.split(',')
                # Check speed in GPRMC sentence (speed is in knots)
                if nmea_sentence.startswith('$GPRMC') and len(fields) >= 8:
                    speed_knots = float(fields[7]) if fields[7] else 0.0
                    speed_kmh = speed_knots * 1.852
                    print(speed_kmh)
                    return speed_kmh > 0  # Moving if speed > 0
            except Exception as e:
                print("[!] Error while processing speed: ", str(e))
        return False

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


if __name__ == "__main__":
    try:
        with open('network_credentials.txt', 'r') as file:
            credentials_file = file.read()
            
        # Hvis filen indeholdende network credentials står tomt
        if '' == credentials_file:
            print("[!] Network credentials file empty, please generate...")
            ip_value = captive_portal.trackerConnection()
        else:
            for line in credentials_file.split('\n'):
                if "SSID:" in line:
                    ssid = line.split(':')[1].strip()
                elif "PASS:" in line:
                    password = line.split(':')[1].strip()

            print(f"SSID: {ssid}, PASS: {password}")
            ip_value = captive_portal.ConnectHandler.activate(ssid, password)
            
    except OSError as e:
        # Hvis filen ikke eksisterer
        if errno.ENOENT == e.errno:
            print("[!] Network credentials doesn't exist, please generate...")
            ip_value = captive_portal.trackerConnection()
            
        # Andre errors
        else:
            print("[!] Error: '%s' occured." % e)
            ip_value = captive_portal.trackerConnection()
    
    print(f"Received IP: {ip_value}")
    
    reset_button = ResetButton()
    
    tracker_id_control()
    
    gps_device = GPS()

    while True:

        if gps_device.check_speed():
            gps_data = gps_device.read_gps()

            if gps_data:
                HTTPServer.send_data(type="send gps coordinates", gps=gps_data)
            time.sleep(15)
        else:
            print("Car is stationary, not reading GPS.")
            time.sleep(1)
