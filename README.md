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

This

This project implements a **smart home automation system** using a network of ESP32 microcontrollers.
The system follows a **master-slave architecture**:
- **Master ESP32:** Central hub coordinating communication and control logic (e.g., sensors, user inputs).
- **Slave ESP32s:** Nodes handling localized tasks (e.g., room-specific lighting, temperature monitoring).
- **Stack:** Firmware is written in **MicroPython** for rapid development and IoT-focused functionality.

# 🛠️ **Requirements**
## 🐍**Software Requirements**


## 🖥️ **Hardware Requirements**


### 🔧 **Setting up the hardware**

# 🗂️ **Project Structure**

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
└── README.md                                    # Main 
```

# 🔍 **Project Explanation**

# 🚀 **How to Start**


# 📹 **Video and Presentation**

# 🌐 **Contacts**

