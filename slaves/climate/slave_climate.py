# slave_climate.py
from machine import Pin, SoftI2C
import network
import time
from umqtt.simple import MQTTClient
from bme680 import constants    # BME680 library for environmental sensing

# === CONFIGURATION ===
# Network and MQTT configuration settings
WIFI_SSID = "YOUR_WIFI_SSID"        # <-- Change to your WiFi network name
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # <-- Change to your WiFi password
MQTT_BROKER = "192.168.1.100"       # <-- Change to your MQTT broker IP address

# Initialize I2C communication for BME680 sensors
# Using GPIO pins 22 (SCL) and 21 (SDA) for I2C
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

# Initialize two BME680 environmental sensors:
# - Indoor sensor at I2C address 0x76
# - Outdoor sensor at I2C address 0x77
bme_int = BME680(i2c, address=0x76)  # Indoor sensor
bme_ext = BME680(i2c, address=0x77)  # Outdoor sensor

# Fan control pin configuration
# GPIO 12 as output to control a fan (adjust pin as needed)
FAN = Pin(12, Pin.OUT)  # <-- Adjust pin according to your hardware setup

# === FUNCTIONS ===
def climate_control():
    """
    Monitor temperature difference and control fan accordingly.
    Turns fan on when temperature difference is less than 6°C
    and turns it off when difference is 6°C or more.
    """
    # Read temperatures from both sensors
    temp_int = bme_int.temperature  # Indoor temperature
    temp_ext = bme_ext.temperature  # Outdoor temperature
    
    # Calculate absolute temperature difference
    diff = abs(temp_int - temp_ext)
    
    # Fan control logic:
    # Turn fan ON if difference is small (<6°C) and fan is currently OFF
    if diff < 6 and not FAN.value():
        FAN.on()
    # Turn fan OFF if difference is large (≥6°C) and fan is currently ON
    elif diff >= 6 and FAN.value():
        FAN.off()
    
    # Print status to console for debugging
    print(f"Temp: indoor={temp_int:.1f}°C, outdoor={temp_ext:.1f}°C, fan={'ON' if FAN.value() else 'OFF'}")

# === MAIN ===
def main():
    """
    Main program execution loop.
    Note: WiFi connection code is currently omitted in this version.
    """
    while True:
        climate_control()  # Run climate control logic
        time.sleep(5)      # Wait 5 seconds between measurements

if __name__ == "__main__":
    # Program entry point - calls main function
    main()
