<details>
<summary>📚 <b>Table of Contents</b></summary>

 1. [Requirements](#Requirements)  
  
 2. [Project Structure](#project-structure)
  
 3.  [Instructions](#Instructions)
  
 4. [Imports](#Imports)
  
 5.  [How to Use](#how-to-use)
  
</details>


## Domotic House with ESP32 master-slave

This

This project implements a **smart home automation system** using a network of ESP32 microcontrollers.
The system follows a **master-slave architecture**:
- **Master ESP32:** Central hub coordinating communication and control logic (e.g., sensors, user inputs).
- **Slave ESP32s:** Nodes handling localized tasks (e.g., room-specific lighting, temperature monitoring).
- **Stack:** Firmware is written in **MicroPython** for rapid development and IoT-focused functionality.

# 🛠️ **Requirements**
## 🐍**Software Requirements**


## 🖥️ **Hardware Requirements**

4 ESP32 board flashed with MicroPython.
Python 3.10+ to interact with your boards using esptool
Recommended IDE: VSCode with PyMakr extension, or Thonny.
USB drivers for your ESP32 board installed on your computer.


## 🗂️ Project-Structure

```
domotica_esp32/
│
├──Domotic_House_project/
│   ├──connections/    
│   │   ├── client.py
│   │   ├── hub.py
│   │   ├── index.html
│   │   └── states.json  
│   │
│   ├──master/
│   │   ├── lib/ 
│   │   │   ├── screen file/
│   │   │   │    └── xpt2046.py
│   │   │   ├── st7789/
│   │   │   │    └── st7789py.py
│   │   │   ├── umqtt/
│   │   │   │    ├── robust.py                    # Use that for long-lasting connections on unreliable networks
│   │   │   │    └── simple.py                    # Usually always use that
│   │   │   └── bitmap 
│   │   └── master.py 
│   │
│   ├──micropython_utils/
│   │   ├── ESP32_GENERIC-20250415-v1.25.0.bin
│   │   └── ESP32_GENERIC_S3-20250415-v1.25.0.bin
│   │
│   ├──slaves/
│   │   ├── climate/
│   │   │   ├── lib/
│   │   │   │    ├── bme680/
│   │   │   │    │    ├── __init__.py
│   │   │   │    │    ├── bme680.py
│   │   │   │    │    └── constants.py
│   │   │   │    └──umqtt/
│   │   │   │         ├── robust.py
│   │   │   │         └── simple.py
│   │   │   └── climate.py
│   │   ├── lights/
│   │   │   ├── lib/
│   │   │   │    └──umqtt/
│   │   │   │         ├── robust.py
│   │   │   │         └── simple.py
│   │   │   └── lights.py
│   │   └──shutters/
│   │       ├── lib/
│   │       │    └──umqtt/
│   │       │         ├── robust.py
│   │       │         └── simple.py
│   │       └── slave_shutters.py
│   │
│   └──utils/
│       ├── mqtt_retry.py                        # MQTT testing script
│       └── wifi_config_tool.py                  # WiFi configuration tool
│   
└── README.md                                    # Main guide

```
- `master.py`: the main script executed at boot.
- `lib/`: folder for custom or third-party libraries.
- `umqtt/`: folder containing the MQTT client module.
- `simple.py`: contains functions to handle MQTT operations.
- `__init__.py`: allows MicroPython to treat the folder as a package (can be empty).

## Instructions
Before uploading files to the esp32 boards, ensure the rigth version of micropython is flashed on them. To do so you can wire them to your computer and, using command prompt or bash:
1. Create a python environment:
```
python -m venv esp32_smart_home
esp32_smart_home\Scripts\activate
```
2. Download esptool, which is usefull to interact with micropython for both flashing firmware and testing tasks:
```
pip install esptool
```
3. Erasing and flashing firmware
```
esptool erase_flash
esptool --baud 460800 write_flash 0x1000 micropython_utils/NAME_OF_MICROPYTHON_BINARY
```
where NAME_OF_MICROPYTHON_BINARY depends on your particoular device model

## ⚙️ Imports

In MicroPython:

You can use dot notation for imports:
  ```python
  from umqtt.simple import MQTTClient
  ```
If needed, manually add the lib folder to sys.path:

  ```python

import sys
sys.path.append('/lib')
from umqtt import simple
```
You can also import specific functions directly:

  ```python
from umqtt.simple import connect_mqtt
```
## 🚀 How to Use
  ```python
Upload all files to the ESP32 using tools like ampy, mpremote, PyMakr, or Thonny.
Make sure the folder structure is correctly replicated on the device.
Edit master.py to include your application logic.
Reset the ESP32 to auto-run your main script.
```
## ✅ **Best Practices**
 ```python
Keep all libraries inside the /lib/ directory.
Include an __init__.py file (even if empty) in library folders to ensure compatibility.
Test imports on your ESP32 to confirm your MicroPython firmware supports nested packages.
```
