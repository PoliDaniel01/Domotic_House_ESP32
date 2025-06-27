# domotic_esp32

This project runs on an **ESP32 using MicroPython**, with a clean folder structure to manage custom and external libraries easily.

## Project Tree

```
domotica_esp32/
│
├── README.md                      # Main guide
│
├── docs/                          # Documentation
│   ├── manuals/                   # Manuals
│   │   └── temp/
│   ├── project_docs/
│   │   └── temp/
│   └── wiring_diagrams/           # Fritzing diagrams
│       ├── master_v1.0.fzz
│       ├── lights_v1.0.png
│       └── climate_v1.0.pdf
│
├── master/                        # Master device
│   ├── master.py                  # Main code
│   ├── config.py                  # WiFi/MQTT configuration
│   └── lib/
│       ├── st7789/                # Display driver
│       │   ├── __init__.py
│       │   └── st7789.py
│       └── umqtt/                 # MQTT clients
│           ├── simple.py
│           └── robust.py
│
├── slaves/                        # Slaves
│   ├── lights/
│   │   ├── slave_lights.py        # Lights slave code
│   │   └── lib/
│   │       └── umqtt/
│   │           ├── simple.py
│   │           └── robust.py
│   │
│   ├── shutters/
│   │   ├── slave_shutters.py      # Shutters slave code
│   │   └── lib/
│   │       └── umqtt/
│   │           ├── simple.py
│   │           └── robust.py
│   │
│   └── climate/
│       ├── slave_climate.py       # Climate slave code
│       └── lib/
│           ├── bme680/            # Sensor library
│           │   ├── __init__.py
│           │   ├── constants.py
│           │   └── bme680.py
│           └── umqtt/
│               ├── simple.py
│               └── robust.py
│
└── utils/                         # Tools
    ├── mqtt_test.py               # MQTT testing script
    └── wifi_config_tool.py        # WiFi configuration tool
```




- `main.py`: the main script executed at boot.
- `lib/`: folder for custom or third-party libraries.
- `umqtt/`: folder containing the MQTT client module.
- `simple.py`: contains functions to handle MQTT operations.
- `__init__.py`: allows MicroPython to treat the folder as a package (can be empty).

## ⚙️ Imports

In MicroPython:

- You can use dot notation for imports:
  ```python
  from umqtt.simple import MQTTClient

If needed, manually add the lib folder to sys.path:

  ```python

import sys
sys.path.append('/lib')
from umqtt import simple

You can also import specific functions directly:

  ```python
from umqtt.simple import connect_mqtt

##🚀 ## 🗂️ Project Structure

Upload all files to the ESP32 using tools like ampy, mpremote, PyMakr, or Thonny.
Make sure the folder structure is correctly replicated on the device.
Edit master.py to include your application logic.
Reset the ESP32 to auto-run your main script.

##✅ **Best Practices**

Keep all libraries inside the /lib/ directory.
Include an __init__.py file (even if empty) in library folders to ensure compatibility.
Test imports on your ESP32 to confirm your MicroPython firmware supports nested packages.

##🛠️ **Requirements**

ESP32 board flashed with MicroPython.
Recommended IDE: VSCode with PyMakr extension, or Thonny.
USB drivers for your ESP32 board installed on your computer.
