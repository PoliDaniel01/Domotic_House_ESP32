# smarthome/common/wifi.py

import network
import time

def connect_wifi(ssid, password):
    """
    Connects the device to a Wi-Fi network.

    :param ssid: The SSID of the Wi-Fi network.
    :type ssid: str
    :param password: The password of the Wi-Fi network.
    :type password: str
    :raises RuntimeError: If the Wi-Fi connection fails.
    """
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        print("Already connected to Wi-Fi.")
        return

    sta.active(True)
    sta.connect(ssid, password)
    
    print(f"Connecting to Wi-Fi network: {ssid}...")
    
    timeout = time.time() + 15  # 15-second timeout
    while not sta.isconnected():
        if time.time() > timeout:
            raise RuntimeError("Failed to connect to Wi-Fi.")
        time.sleep(1)
        
    print(f"Successfully connected to Wi-Fi. IP address: {sta.ifconfig()[0]}")

