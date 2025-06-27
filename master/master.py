# master_esp32_2432s028.py
from machine import Pin, SoftI2C
import network
import time
import json
from umqtt.simple import MQTTClient
from lib.st7789 import    #put there the missing library

# === CONFIGURATION ===
# Network and MQTT configuration settings
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change to your WiFi network name
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <-- Change to your WiFi password
MQTT_BROKER = "192.168.1.100"       # <-- Change to your MQTT broker IP address

# Initialize I2C communication for display
# Using GPIO pins 18 (SCL) and 23 (SDA) for I2C
i2c = SoftI2C(scl=Pin(18), sda=Pin(23))

# Initialize ST7789 display (240x320 resolution)
# Reset pin is connected to GPIO 33
display = ST7789(i2c, 240, 320, reset=Pin(33))

# === FUNCTIONS ===
def connect_wifi():
    """Connect to WiFi network using the configured credentials"""
    sta_if = network.WLAN(network.STA_IF)  # Create station interface
    sta_if.active(True)                    # Activate the interface
    sta_if.connect(WIFI_SSID, WIFI_PASS)   # Connect to WiFi
    while not sta_if.isconnected():        # Wait until connected
        time.sleep(0.5)
    print("WiFi connected")

def show_status(message):
    """Display status message on the screen"""
    display.fill(0)  # Clear screen (fill with black)
    display.text("HOME AUTOMATION", 10, 10)  # Display title at (10,10)
    display.text(message, 10, 50)           # Display status message at (10,50)
    display.show()                          # Update the display

# === MAIN ===
def main():
    """Main program execution"""
    # Connect to WiFi network
    connect_wifi()
    
    # Initialize MQTT client and connect to broker
    client = MQTTClient("master", MQTT_BROKER)
    client.connect()
    
    # Main program loop
    while True:
        show_status("Status: ONLINE")  # Update display status
        time.sleep(5)                 # Wait 5 seconds before next update

if __name__ == "__main__":
    # Program entry point - calls main function
    main()
