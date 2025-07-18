<a id="top"></a>
# README

<details>
<summary>📚 <b>Table of Contents</b></summary>

 1. [About the project](#-domotic-house-with-esp32-master---slave)  

 2. [Requirements](#️-requirements)
  
 3. [Project Structure](#️-project-structure)
  
 4. [Project Explanation](#-project-explanation)
  
 5. [How to Start](#-how-to-start)
  
 6.  [ Video and Presentation](#-video-and-presentation)

 7.  [Contacts](#-contacts)
  
</details>


# 🏠 **Domotic House with ESP32 master - slave**

This project implements a **smart home automation system** using a network of ESP32 microcontrollers.
The system follows a **master-slave architecture**:
- **Master ESP32:** Central hub coordinating communication and control logic (e.g., sensors, user inputs).
- **Slave ESP32s:** Nodes handling localized tasks (e.g., room-specific lighting, temperature monitoring).
- **Stack:** Firmware is written in **MicroPython** for rapid development and IoT-focused functionality.
[back to top](#top)
# 🛠️ **Requirements**
## 🐍**Software Requirements**
To get started with this project, you will require the following software.
- MicroPython interpreter
- MQTT library
- Python libraries for device drivers
- Web server software
- JSON handling library
[back to top](#top)
## 🖥️ **Hardware Requirements**
To get started with this project, you will need the following hardware:
- ESP32 microcontroller
- ST7789 display
- BME680 sensor
- Wi-Fi module
- General I/O devices
[back to top](#top)
# 🗂️ **Project Structure**

```
domotica_esp32/
│
├──Domotic_House_project/                       # Project root
│   ├──connections/                                 # networking
│   │   ├── client.py                                   # client script
│   │   ├── hub.py                                      # hub script
│   │   ├── index.html                                  # web interface
│   │   └── states.json                                 # data storage
│   │
│   ├──master/                                      # master control
│   │   ├── lib/                                        # library
│   │   │   ├── screen file/                                # screen management
│   │   │   │    └── xpt2046.py                                 # devide driver  
│   │   │   ├── st7789/                                     # display driver
│   │   │   │    └── st7789py.py                                    # device driver
│   │   │   ├── umqtt/                                      # mqtt library
│   │   │   │    ├── robust.py                                  # robust connection
│   │   │   │    └── simple.py                                  # simple connection
│   │   │   └── bitmap                                      # image data
│   │   └── master.py                                   # master script
│   │   
│   ├──micropython_utils/                           # micropython utils
│   │   ├── ESP32_GENERIC-20250415-v1.25.0.bin          # firmware
│   │   └── ESP32_GENERIC_S3-20250415-v1.25.0.bin       # firmware
│   │
│   ├──slaves/                                      # slave devices
│   │   ├── climate/                                    # climate control
│   │   │   ├── lib/                                        # library
│   │   │   │    ├── bme680/                                    # sensor library
│   │   │   │    │    ├── __init__.py                               # initialization 
│   │   │   │    │    ├── bme680.py                                 # sensor script
│   │   │   │    │    └── constants.py                              # config
│   │   │   │    └──umqtt/                                  # mqtt library
│   │   │   │         ├── robust.py                             # robust connection
│   │   │   │         └── simple.py                             # simple connection
│   │   │   └── climate.py                              # climate script
│   │   │ 
│   │   ├── lights/                                     # light control
│   │   │   ├── lib/                                        # library
│   │   │   │    └──umqtt/                                      # mqtt library
│   │   │   │         ├── robust.py                                 # robust connection
│   │   │   │         └── simple.py                                 # simple connection
│   │   │   └── lights.py                               # light script
│   │   │
│   │   └──shutters/                                    #s hutter control
│   │       ├── lib/                                        # library
│   │       │    └──umqtt/                                      # mqtt library
│   │       │         ├── robust.py                                 # robust connection
│   │       │         └── simple.py                                 # simple connection
│   │       └── slave_shutters.py                       # shutter scripot
│   │
│   └──utils/                                       # utility script
│       ├── mqtt_retry.py                               # MQTT retry script
│       └── wifi_config_tool.py                         # WiFi configuration tool
│   
└── README.md                                   # Documentation 
```
[back to top](#top)
# 🔍 **Project Explanation**
This project is a home automation system built using MicroPython and ESP32 microcontrollers.  
It controls various devices such as lights, shutters, and climate settings through a network using MQTT communication.  
The system includes a web interface for monitoring and control, with data stored in states.json.  
Device drivers (e.g., st7789 for displays, bme680 for sensors) and utility scripts (e.g., wifi_config_tool.py) support the functionality, making it a flexible and scalable solution for domotic application.
# 🚀 **How to Start**
1. Ensure you have the required software and hardware as listed in the Requirements section.
2. Flash the ESP32 with the appropriate firmware (e.g., ESP32_GENERIC_28259415-v1.25.0.bin).
3. Set up the hardware:
    - Connect the ST7789 display and BME680 sensor to the ESP32.
    - Configure Wi-Fi settings using wifi_config_tool.py.
    - Wire the lights, shutters, climate control and allarm devices to the ESP32 I/O pins.
4. Upload the project files to the ESP32 and run master.py to start the system.
5. Access the web interface via index.html to begin controlling and monitoring your devices.
[back to top](#top)
# 📹 **Video and Presentation**
[back to top](#top)
# 🌐 **Contacts**
Alessandro Morelato - alessandro.morelato@studenti.unitn.it - @morelatoalessandro  
Daniel Poli - daniel.poli@studenti.unitn.it - @PoliDaniel01  
Matteo Scoropan - matteo.scoropan@studenti.unitn.it - @Matteosco  
Sebastiano Quaglio - sebastiano.quaglio@studenti.unitn.it - @quaglio03  
[back to top](#top)