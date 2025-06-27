# slave_climate.py
from machine import Pin, SoftI2C
import network
import time
from umqtt.simple import MQTTClient
from lib.bme680 import constants    # BME680 library

# === CONFIGURATION ===
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <--
MQTT_BROKER = "192.168.1.100"       # <--

# BME680 Sensors (I2C)
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
bme_int = BME680(i2c, address=0x76)  # Indoor
bme_ext = BME680(i2c, address=0x77)  # Outdoor

# Fan control
FAN = Pin(12, Pin.OUT)  # <-- Adjust pin

# === FUNCTIONS ===
def climate_control():
    temp_int = bme_int.temperature
    temp_ext = bme_ext.temperature
    diff = abs(temp_int - temp_ext)
    
    if diff < 6 and not FAN.value():
        FAN.on()
    elif diff >= 6 and FAN.value():
        FAN.off()
    
    print(f"Temp: indoor={temp_int:.1f}°C, outdoor={temp_ext:.1f}°C, fan={'ON' if FAN.value() else 'OFF'}")

# === MAIN ===
def main():
    # WiFi connection (omitted)
    while True:
        climate_control()
        time.sleep(5)

if __name__ == "__main__":
    main()
