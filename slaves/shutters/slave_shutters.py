# slave_shutters.py
from machine import Pin
import network
import time
from lib.umqtt import simple

# === CONFIGURATION ===
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <--
MQTT_BROKER = "192.168.1.100"       # <--

# Buttons
BTN_UP = Pin(25, Pin.IN, Pin.PULL_UP)    # <-- Adjust pins
BTN_DOWN = Pin(33, Pin.IN, Pin.PULL_UP)  # <--

# Motor outputs
MOTOR_UP = Pin(12, Pin.OUT)    # <--
MOTOR_DOWN = Pin(13, Pin.OUT)  # <--

# State tracking
shutter_state = "idle"  # "open", "closed", "idle"

# === FUNCTIONS ===
def move_shutter(direction):
    global shutter_state
    if direction == "up" and shutter_state != "open":
        MOTOR_UP.on()
        time.sleep(2)  # Movement duration
        MOTOR_UP.off()
        shutter_state = "open"
    elif direction == "down" and shutter_state != "closed":
        MOTOR_DOWN.on()
        time.sleep(2)
        MOTOR_DOWN.off()
        shutter_state = "closed"

# === MAIN ===
def main():
    # WiFi connection (omitted)
    while True:
        if not BTN_UP.value(): move_shutter("up")
        if not BTN_DOWN.value(): move_shutter("down")
        time.sleep(0.1)

if __name__ == "__main__":
    main()
