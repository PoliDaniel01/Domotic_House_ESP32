## Table of Contents
- [Requirements](#Requirements)
- [Project Structure](#Project-Structure)
- [Instructions](#Instructions)
- [Imports](#Imports)
- [How to Use](#How-to-Use)

# domotic_esp32

This project runs on an **ESP32 using MicroPython**, with a clean folder structure to manage custom and external libraries easily.

## 🛠️ **Requirements**
```
4 ESP32 board flashed with MicroPython.
Python 3.10+ to interact with your boards using esptool
Recommended IDE: VSCode with PyMakr extension, or Thonny.
USB drivers for your ESP32 board installed on your computer.
```

## 🗂️ Project Structure

```
domotica_esp32/
│
├── docs/                              # Documentation
│   ├── manuals/                       # Manuals
│   │   ├── temp                       # Delete that when other files are added
│   │   ├── MQTT_setup.md              # Missing file
│   │   └── ESP32_flashing_guide.pdf   # Missing file
│   │
│   ├── project_docs/
│   │    ├── temp                       # Delete that when other files are added
│   │    ├── api_reference.md           # MQTT API Documentation
│   │    ├── pinout_cheatsheet.png      # ESP32 Pinout Infographic
│   │    ├── protocol_guide.md          # Communication Specifications
│   │    └── troubleshooting.md         # Common Issues & Solutions
│   │
│   └── wiring_diagrams/               # Fritzing diagrams
│       ├── design_files/              # Editable source files
│       │   ├── temp                   # Delete that when other files are added
│       │   ├── master_esp32.fzz       # Fritzing master diagram
│       │   ├── full_system.drawio     # Complete system architecture
│       │   └── power_supply.kicad     # PCB power design (KiCAD)
│       │
│       ├── exports/                   # Ready-to-use references
│       │   ├── temp                   # Delete that when other files are added
│       │   ├── master_esp32.png
│       │   ├── esp32_pinout.pdf       # GPIO cheat sheet
│       │   └── power_supply.pdf       # Power circuit diagram
│       │
│       ├── photos/                    # Real-world references
│       │   ├── temp                   # Delete that when other files are added
│       │   ├── master_front.jpg
│       │   └── relay_wiring.jpg       # Close-up of critical connections
│       │
│       └── checklists/                # Validation tools
│           ├── temp                   # Delete that when other files are added
│           ├── wiring_checklist.md
│           └── safety_checks.md
│ 
├── master/                            # Master device
│   ├── master.py                      # Main code
│   ├── config.py                      # WiFi/MQTT configuration (MISSING!)
│   └── lib/    
│       ├── st7789/                    # Display driver
│       │   ├── temp                   # Delete that when other files are added
│       │   ├── __init__.py            # MISSING!
│       │   └── st7789.py              # MISSING!
│       │
│       └── umqtt/                     # MQTT clients
│           ├── simple.py              # Usually always use that
│           └── robust.py              # Use that for long-lasting connections on unreliable networks, with automatic reconnection and minimal extra coding.
│
├── slaves/                            # Slaves
│   ├── climate/
│   │   ├── slave_climate.py           # Climate slave code
│   │   └── lib/
│   │       ├── bme680/                # Sensor library
│   │       │   ├── __init__.py
│   │       │   └── constants.py
│   │       │   
│   │       └── umqtt/                 # MQTT clients
│   │           ├── simple.py          # Usually always use that
│   │           └── robust.py          # Use that for long-lasting connections on unreliable networks, with automatic reconnection and minimal extra coding.
│   │
│   ├── lights/
│   │   ├── slave_lights.py            # Lights slave code
│   │   └── lib/
│   │       └── umqtt/                 # MQTT clients
│   │           ├── simple.py          # Usually always use that
│   │           └── robust.py          # Use that for long-lasting connections on unreliable networks, with automatic reconnection and minimal extra coding.
│   │
│   └── shutters/
│       ├── slave_shutters.py          # Shutters slave code
│       └── lib/
│           └── umqtt/                 # MQTT clients
│               ├── simple.py          # Usually always use that
│               └── robust.py          # Use that for long-lasting connections on unreliable networks, with automatic reconnection and minimal extra coding.
│
├── utils/                             # Tools
│   ├── mqtt_test.py                   # MQTT testing script
│   └── wifi_config_tool.py            # WiFi configuration tool
│
└── README.md                          # Main guide
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
