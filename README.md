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

# 🛠️ **Requirements**
## 🐍**Software Requirements**


## 🖥️ **Hardware Requirements**


## 🔧 **Setting up the hardware**

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

# 🔍 **Project Explanation**

# 🚀 **How to Start**


# 📹 **Video and Presentation**

# 🌐 **Contacts**

