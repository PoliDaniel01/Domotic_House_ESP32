# domotic_esp32

This project runs on an **ESP32 using MicroPython**, with a clean folder structure to manage custom and external libraries easily.

## 🗂️ Project Structure

domotica_esp32/
│
├── master/                          # Cartella principale del master
│   ├── master.py                    # Main Code
│   ├── config.py                    # WiFi/MQTT Configuration (missing)
│   └── lib/
│       ├── st7789/                  # display library
│       │   ├── __init__.py          # init (missing)
│       │   ├── st7789.py            # Main Driver (missing)
│       │   └── fonts/               # Fonts (missing)
│       └── umqtt/
│           ├── simple.py            # Client MQTT base
│           └── robust.py            # Client MQTT advanced
├── slaves/
│   ├── lights/
│   │   ├── slave_light.py           # Light Code
│   │   └── lib/
│   │       └── umqtt/
│   │           ├── simple.py        # Client MQTT base
│   │           └── robust.py        # Client MQTT advanced
│   ├── shutters/
│   │   ├── main.py                  # Codice tapparelle
│   │   └── lib/
│   │       └── umqtt/
│   │
│   └── climate/
│       ├── main.py                  # Codice clima
│       └── lib/
│           ├── bme680/              # Libreria sensore
│           │   ├── __init__.py
│           │   └── bme680.py
│           └── umqtt/
│
├── docs/
│   ├── wiring_diagrams/             # Schemi Fritzing
│   │   ├── master_v1.0.fzz
│   │   ├── lights_v1.0.png
│   │   └── climate_v1.0.pdf
│   │
│   └── manuals/                     # Manuali
│       ├── MQTT_setup.md
│       └── ESP32_flashing_guide.pdf
│
├── utils/
│   ├── mqtt_test.py                 # Script di test
│   └── wifi_config_tool.py          # Configurazione WiFi
│
└── README.md                        # Guida principale
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
