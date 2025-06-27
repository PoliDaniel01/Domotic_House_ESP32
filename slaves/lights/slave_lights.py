# slave_lights.py
from machine import Pin
import network
import time
from lib.umqtt import simple, robust

# === CONFIGURATION ===
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <--
MQTT_BROKER = "192.168.1.100"       # <--

# Buttons (internal pull-up)
BTN_LIGHT1 = Pin(14, Pin.IN, Pin.PULL_UP)  # <-- Adjust pins
BTN_LIGHT2 = Pin(27, Pin.IN, Pin.PULL_UP)  # <--
BTN_LIGHT3 = Pin(26, Pin.IN, Pin.PULL_UP)  # <--

# Relay outputs
RELAY_LIGHT1 = Pin(12, Pin.OUT)  # <-- Adjust pins
RELAY_LIGHT2 = Pin(13, Pin.OUT)  # <--
RELAY_LIGHT3 = Pin(15, Pin.OUT)  # <--

# === FUNCTIONS ===
def toggle_light(light_num):
    relay = [RELAY_LIGHT1, RELAY_LIGHT2, RELAY_LIGHT3][light_num-1]
    relay.value(not relay.value())
    print(f"Light {light_num} {'ON' if relay.value() else 'OFF'}")

# === MAIN ===
def main():
    # WiFi connection (omitted for brevity)
    while True:
        if not BTN_LIGHT1.value(): toggle_light(1)
        if not BTN_LIGHT2.value(): toggle_light(2)
        if not BTN_LIGHT3.value(): toggle_light(3)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
