# slave_shutters.py
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
BTN_UP = Pin(25, Pin.IN, Pin.PULL_UP)    # <-- Button to move shutters up (adjust pin)
BTN_DOWN = Pin(33, Pin.IN, Pin.PULL_UP)  # <-- Button to move shutters down (adjust pin)

# Motor control outputs
# These pins control the shutter motor direction
MOTOR_UP = Pin(12, Pin.OUT)    # <-- Output to move shutters up (adjust pin)
MOTOR_DOWN = Pin(13, Pin.OUT)  # <-- Output to move shutters down (adjust pin)

# State tracking variable
# Possible states: "idle", "open", "closed"
shutter_state = "idle"  # Initial state

# === FUNCTIONS ===
def move_shutter(direction):
    """
    Control the shutter movement based on requested direction
    Args:
        direction (str): Either "up" to open or "down" to close shutters
    """
    global shutter_state
    
    # Open shutter if not already open
    if direction == "up" and shutter_state != "open":
        MOTOR_UP.on()        # Activate motor in up direction
        time.sleep(2)        # Run motor for 2 seconds (adjust for your shutter)
        MOTOR_UP.off()       # Stop motor
        shutter_state = "open"  # Update state
        print("Shutters opened")
        
    # Close shutter if not already closed
    elif direction == "down" and shutter_state != "closed":
        MOTOR_DOWN.on()      # Activate motor in down direction
        time.sleep(2)        # Run motor for 2 seconds (adjust for your shutter)
        MOTOR_DOWN.off()     # Stop motor
        shutter_state = "closed"  # Update state
        print("Shutters closed")

# === MAIN ===
def main():
    """
    Main program execution loop.
    Continuously checks button states and controls shutters accordingly.
    Note: WiFi connection code is currently omitted in this version.
    """
    # Initialize motor control pins to off
    MOTOR_UP.off()
    MOTOR_DOWN.off()
    
    while True:
        # Check up button (active-low)
        if not BTN_UP.value(): 
            move_shutter("up")
            
        # Check down button (active-low)
        if not BTN_DOWN.value(): 
            move_shutter("down")
        
        # Small delay to debounce buttons and reduce CPU usage
        time.sleep(0.1)

if __name__ == "__main__":
    # Program entry point - calls main function
    main()
