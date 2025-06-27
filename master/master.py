# master_esp32_2432s028.py
from machine import Pin, SoftI2C
import network
import time
import json
from lib.umqtt import simple.py
from lib.st7789 import    #put there the missing library

# === CONFIGURATION ===
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <--
MQTT_BROKER = "192.168.1.100"       # <-- Broker IP

# ST7789 Display (240x320)
i2c = SoftI2C(scl=Pin(18), sda=Pin(23))
display = ST7789(i2c, 240, 320, reset=Pin(33))

# === FUNCTIONS ===
def connect_wifi():
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(WIFI_SSID, WIFI_PASS)
    while not sta_if.isconnected():
        time.sleep(0.5)
    print("WiFi connected")

def show_status(message):
    display.fill(0)  # Clear screen
    display.text("HOME AUTOMATION", 10, 10)
    display.text(message, 10, 50)
    display.show()

# === MAIN ===
def main():
    connect_wifi()
    client = MQTTClient("master", MQTT_BROKER)
    client.connect()
    
    while True:
        show_status("Status: ONLINE")
        time.sleep(5)

if __name__ == "__main__":
    main()
