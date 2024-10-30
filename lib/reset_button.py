import machine
import time
import os

# set up pins
reset_button_pin = 13  # pin for button
led_pin = 12           # pin for LED

reset_button = machine.Pin(reset_button_pin, machine.Pin.IN, machine.Pin.PULL_UP)
led = machine.Pin(led_pin, machine.Pin.OUT)

# path and filename of credentials
file_path = 'reset_test.txt'

def delete_file():
    """Deletes the txt file."""
    try:
        os.remove(file_path)
        print("File deleted.")
    except OSError:
        print("File does not exist or could not be deleted.")

def blink_led(times, interval_ms):
    """Blinks the LED a given number of times with a specified interval in milliseconds."""
    for _ in range(times):
        led.on()
        time.sleep_ms(interval_ms)
        led.off()
        time.sleep_ms(interval_ms)

def monitor_button():
    """Monitors the reset button for a long press."""
    press_duration = 0
    while True:
        if reset_button.value() == 0:  # button is pressed
            led.on()  # turn on LED while button is pressed
            press_duration += 1
            time.sleep(1)  # check every second
            
            if press_duration >= 10:  # 10 seconds
                delete_file()
                press_duration = 0  # reset duration after deletion
                led.off()  # turn off LED before starting blink sequence
                blink_led(5, 500)  # blink LED 5 times with 500ms intervals
        else:
            led.off()  # LED is off when button is not pressed
            press_duration = 0  # reset if button is released

# start monitoring the reset button
monitor_button()
