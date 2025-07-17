# slave_lights.py
from machine import Pin
import network
import time
from umqtt.simple import MQTTClient

# === CONFIGURATION ===
# Network and MQTT configuration settings
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change to your WiFi network name
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <-- Change to your WiFi password
MQTT_BROKER = "192.168.1.100"       # <-- Change to your MQTT broker IP address

# Button inputs with internal pull-up resistors
# Buttons connect to ground when pressed (active-low)
BTN_LIGHT1 = Pin(14, Pin.IN, Pin.PULL_UP)  # <-- Button for light 1 (adjust pin)
BTN_LIGHT2 = Pin(27, Pin.IN, Pin.PULL_UP)  # <-- Button for light 2 (adjust pin)
BTN_LIGHT3 = Pin(26, Pin.IN, Pin.PULL_UP)  # <-- Button for light 3 (adjust pin)

# Relay outputs for controlling lights
# Relays are active-high (HIGH = ON, LOW = OFF)
RELAY_LIGHT1 = Pin(12, Pin.OUT)  # <-- Relay for light 1 (adjust pin)
RELAY_LIGHT2 = Pin(13, Pin.OUT)  # <-- Relay for light 2 (adjust pin)
RELAY_LIGHT3 = Pin(15, Pin.OUT)  # <-- Relay for light 3 (adjust pin)

# === FUNCTIONS ===
def toggle_light(light_num):
    """
    Toggle the state of the specified light (1-3)
    Args:
        light_num (int): Light number to toggle (1, 2, or 3)
    """
    # Select the appropriate relay based on light number
    relay = [RELAY_LIGHT1, RELAY_LIGHT2, RELAY_LIGHT3][light_num-1]
    
    # Invert the current relay state (toggle)
    relay.value(not relay.value())
    
    # Print status update to console
    print(f"Light {light_num} {'ON' if relay.value() else 'OFF'}")

# === MAIN ===
def main():
    """
    Main program execution loop.
    Continuously checks button states and toggles lights when pressed.
    Note: WiFi connection code is currently omitted in this version.
    """
    while True:
        # Check each button and toggle corresponding light when pressed
        # Button reads LOW when pressed (due to pull-up resistor)
        if not BTN_LIGHT1.value(): toggle_light(1)  # Light 1 button pressed
        if not BTN_LIGHT2.value(): toggle_light(2)  # Light 2 button pressed
        if not BTN_LIGHT3.value(): toggle_light(3)  # Light 3 button pressed
        
        # Small delay to debounce buttons and reduce CPU usage
        time.sleep(0.1)

if __name__ == "__main__":
    # Program entry point - calls main function
    main()
