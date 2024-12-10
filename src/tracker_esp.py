from machine import I2C, Pin, UART, reset
import time
import captive_portal
import urequests

import aioble
import bluetooth
import struct
import uasyncio as asyncio

import ujson as json
import os
from micropython import const
import gc

SERVER_URL = "https://79.171.148.143/api"
TRACKER_ID = None

_TRACKER_SERVICE_UUID = bluetooth.UUID("4f450d8c-b4fa-4ee6-b131-3161f2e82aac")
_CHARACTERISTIC_UUID_WIFI_SSID = bluetooth.UUID("841677b2-99fe-4175-9fc9-033ac6c85a54")
_CHARACTERISTIC_UUID_WIFI_PASSWORD = bluetooth.UUID("dfc2c17e-9f7f-480e-82e4-b540a21ebf0b")
_CHARACTERISTIC_UUID_TRACKER_PASSWORD = bluetooth.UUID("1370af71-05bd-42cd-9604-72667f439c42")
_ADV_INTERVAL_US = const(100000)


class BLEPeripheral:
    def __init__(self):
        
        # Define BLE service and characteristics with explicit permissions
        self.device_service = aioble.Service(_TRACKER_SERVICE_UUID)

        # Define characteristics with write permissions
        self.ssid_characteristic = aioble.Characteristic(self.device_service,
                                                         _CHARACTERISTIC_UUID_WIFI_SSID,
                                                         write=True, read=True, notify=True, capture=True)
        
        self.ssid_password_characteristic = aioble.Characteristic(self.device_service,
                                                                  _CHARACTERISTIC_UUID_WIFI_PASSWORD,
                                                                  write=True, read=True, notify=True, capture=True)
        
        self.user_password_characteristic = aioble.Characteristic(self.device_service,
                                                                  _CHARACTERISTIC_UUID_TRACKER_PASSWORD,
                                                                  write=True, read=True, notify=True, capture=True)

        # Register the service
        aioble.register_services(self.device_service)

    async def start_advertising(self):
        await asyncio.sleep(1)  # Add a delay to ensure the BLE stack is initialized

        while True:
            try:
                print("Starting advertisement...")
                async with await aioble.advertise(
                        _ADV_INTERVAL_US,
                        name='car_tracker',
                        services=[_TRACKER_SERVICE_UUID]
                ) as connection:

                    # Log the connection
                    client_mac = connection.device.addr
                    print(f"Connected to MAC: {client_mac}")

                    while connection.is_connected():
                        await asyncio.sleep_ms(1000)

                    print("Client disconnected")

            except Exception as e:
                print(f"Connection error: {e}")
                await asyncio.sleep(2)
    
    async def monitor_char_value(self):
        while True:
            _, SSID_VALUE_BYTE = await self.ssid_characteristic.written(timeout_ms=0)
            print(SSID_VALUE_BYTE)
            
            _, SSID_PASS_VALUE_BYTE = await self.ssid_password_characteristic.written(timeout_ms=0)
            print(SSID_PASS_VALUE_BYTE)
            
            _, TRACKER_PASS_VALUE_BYTE = await self.user_password_characteristic.written(timeout_ms=0)
            print(TRACKER_PASS_VALUE_BYTE)
            
            
            
            if SSID_VALUE_BYTE and SSID_PASS_VALUE_BYTE and TRACKER_PASS_VALUE_BYTE:
                print("Recieved characteristic values, processing...")
                
                credentials = {
                    "SSID": SSID_VALUE_BYTE.decode('utf-8'),
                    "PASS": SSID_PASS_VALUE_BYTE.decode('utf-8')
                }
                
                tracker_password = {
                    "Tracker_pass": TRACKER_PASS_VALUE_BYTE.decode('utf-8'),
                }
                
                with open('network_credentials.txt', 'w') as file:
                    json.dump(credentials, file)
                    
                with open('temp_tracker_password.txt', 'w') as file:
                    json.dump(tracker_password, file)
                    
                   
                asyncio.sleep(5)
                   
                reset()
                 
                # Uncomment below statement when vsphere up and running
                # HTTPServer.send_data(type="tracker password update", tracker_password=TRACKER_PASS_VALUE_BYTE.decode('utf-8'))
            
            await asyncio.sleep(1)
            
        
class HTTPServer:
    def send_data(type=None, data=None):
        global TRACKER_ID

        gc.collect()

        if 'tracker id request' == type:
            try:
                
                data_packet = {'data': 'tracker id request'}

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                
                response = urequests.post(SERVER_URL, json=data_packet)

                print(f"Server response: {response.text}")

                response_data = response.json()

                if response_data['status'] == 'success':
                    TRACKER_ID = response_data['tracker_id']

                    tracker_id = {
                        'Tracker_id': TRACKER_ID
                        }		

                    with open('tracker_id.txt', 'w') as file:
                        json.dump(tracker_id, file)

                    print("[+] Tracker id request successfully handled")
                    

                else:
                    print("[!] Error handeling tracker id request response.")

            except Exception as e:
                print(f"Unhandled exception: {e}")


        elif 'send gps coordinates' == type:

            try:                
                data_packet = {
                    'data': 'received coords',	
                    'coords_lat': f"{data[0]}",
                    'coords_long': f"{data[1]}",
                    'tracker_id': TRACKER_ID
                    }

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(SERVER_URL, json=data_packet)

            except Exception as e:
                print(f"Unhandled exception: {e}")


        elif 'tracker password update' == type:
            
            try:                
                data_packet = {
                    'data': 'update password request',	
                    'tracker_id': TRACKER_ID,
                    'tracker_password': data
                    }

                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(SERVER_URL, json=data_packet)

                print(f"Server response: {response.text}")

                response_data = response.json()
                
                if response_data['status'] == 'success':
                    os.remove('temp_tracker_password.txt')
                

            except Exception as e:
                print(f"Unhandled exception: {e}")

        elif 'password reset procedure' == type:
            
            try:
                data_packet = {
                    'data': 'reset password request',
                    'tracker_id': TRACKER_ID
                    }
                        
                print(f"[+] Sending data: {json.dumps(data_packet)}")
                response = urequests.post(SERVER_URL, json=data_packet)
                        
                print(f"Server response: {response.text}")    
                    
            except Exception as e:
                print(f"Unhandled exception: {e}")
        
        gc.collect()


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
            print("[!] Performing level 1 reset")
            
            self.delete_file()
            self.blink_led(5, 250)
        elif level == 2:
            print("[!] Performing level 2 reset")
            
            print("Deleting wifi credentials")
            self.delete_file()
            
            print("Running password reset procedure")
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
                    print("Current speed [KM/H]:", speed_kmh)
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
            tracker_id = json.loads(credentials_file)
            TRACKER_ID = tracker_id.get("Tracker_id")

            print(f"[+] Tracker ID: {TRACKER_ID}")
            
    except OSError as e:
        # Hvis filen ikke eksisterer
        if errno.ENOENT == e.errno:
            print("[!] Tracker ID does not exist, requesting...")
            HTTPServer.send_data(type='tracker id request')
        # Andre errors
        else:
            print("[!] Error: '%s' occured." % e)

def send_password():
    try:
        with open('temp_tracker_password.txt', 'r') as file:
            temp_tracker_password = file.read()

            tracker_password_file = json.loads(temp_tracker_password)
            tracker_password = tracker_password_file.get("Tracker_pass")
            HTTPServer.send_data(type='tracker password update', data=tracker_password)
        
    except OSError:
        print("[!] Password Temp file doesn't exist. Skipping update procedure")


async def main():
    try:
        with open('network_credentials.txt', 'r') as file:
            credentials_file = file.read()
            
        # Hvis filen indeholdende network credentials står tomt
        if '' == credentials_file:
            print("[!] Network credentials file empty, please generate...")
            ble = BLEPeripheral()
            await asyncio.gather(
                asyncio.create_task(ble.start_advertising()),
                asyncio.create_task(ble.monitor_char_value()),
            )
            
        else:
            credentials = json.loads(credentials_file)
            ssid_value = credentials.get("SSID")
            password_value = credentials.get("PASS")

            if ssid_value and password_value:
                print(f"SSID: {ssid_value}, PASS: {password_value}")
                ip_value = captive_portal.ConnectHandler.activate(ssid_value, password_value)
            else:
                print("[!] Network credentials are invalid or incomplete.")
            
    except OSError as e:
        # Hvis filen ikke eksisterer
        if errno.ENOENT == e.errno:
            print("[!] Network credentials doesn't exist, please generate...")
            ble = BLEPeripheral()
            await asyncio.gather(
                asyncio.create_task(ble.start_advertising()),
                asyncio.create_task(ble.monitor_char_value()),
            )
            
            
        # Andre errors
        else:
            print("[!] Error: '%s' occured." % e)
            ble = BLEPeripheral()
            await asyncio.gather(
                asyncio.create_task(ble.start_advertising()),
                asyncio.create_task(ble.monitor_char_value()),
            )
            
    
    print(f"Received IP: {ip_value}")
    
    reset_button = ResetButton()
    
    tracker_id_control()
    
    send_password()
    
    gps_device = GPS()

    while True:
        if gps_device.check_speed():
            gps_data = gps_device.read_gps()

            if gps_data:
                HTTPServer.send_data(type="send gps coordinates", data=gps_data)
            time.sleep(15)
        else:
            print("Car is stationary, not reading GPS.")
            time.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
