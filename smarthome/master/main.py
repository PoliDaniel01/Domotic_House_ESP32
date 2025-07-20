"""
Main script for the master ESP32 board in the smart home system.

This script is responsible for:
- Driving the ST7789 display and handling XPT2046 touch input.
- Providing a user interface to control various smart home devices.
- Running a Microdot web server for remote control via Wi-Fi.
- Communicating with other ESP32 boards (slaves) via MQTT.
- Managing device states and persisting them to a file.
"""

# Standard library imports
import json
import time
import uasyncio as asyncio

# MicroPython-specific imports
from machine import reset
from machine import Pin, SPI

# Local application/library specific imports
from smarthome.common import wifi, mqtt
from smarthome.common.webserver import WebServer
from smarthome.common.display import DisplayManager


# ==============================
# CONFIGURATION
# ==============================

# --- Wi-Fi Configuration ---
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

# --- MQTT Configuration ---
MQTT_BROKER = "YOUR_MQTT_BROKER_IP"
MQTT_CLIENT_ID = "esp32-master-display"


# --- Application Settings ---
STANDBY_TIMEOUT = 60  # Seconds before display goes into standby
STATE_FILE = "states.json" # File to store persistent states

# --- Hardware Pin Configuration ---
PIN_DISP_BL = 21



# --- MQTT Topics ---
# This dictionary maps device names to their command topics.
MQTT_COMMAND_TOPICS = {
    "soggiorno": "home/led/soggiorno/command",
    "cucina": "home/led/cucina/command",
    "camera": "home/led/camera/command",
    "aria_condizionata": "home/led/aria_condizionata/command",
    "riscaldamento": "home/led/riscaldamento/command",
    "allarme": "home/sensor/alarm/set",
    "tapparella": "home/actuator/tapparella/set"
}


# Topics to subscribe to for state updates from slaves.
MQTT_SUBSCRIPTIONS = [
    b"home/led/+/state",
    b"home/status/temperature",
    b"home/sensor/alarm/state",
]


class StateManager:
    """
    Manages the state of all devices and application settings.

    This class handles loading states from and saving states to a JSON file,
    ensuring persistence across reboots.
    """
    def __init__(self, state_file):
        """
        Initializes the StateManager.

        :param state_file: The path to the file used for state persistence.
        :type state_file: str
        """
        self._state_file = state_file
        self.states = self._load_states()

    def _load_states(self):
        """
        Loads device states from the JSON file.

        If the file doesn't exist or is invalid, it returns a default state.

        :return: A dictionary containing the device states.
        :rtype: dict
        """
        try:
            with open(self._state_file, "r") as f:
                states = json.load(f)
                print("Master: States loaded from file.")
                return states
        except (OSError, ValueError) as e:
            print(f"Master: Could not load state file '{self._state_file}': {e}. Using defaults.")
            return {
                "soggiorno": False,
                "cucina": False,
                "camera": False,
                "aria_condizionata": False,
                "riscaldamento": False,
                "allarme": False,
                "auto_mode": False,
                "desired_temperature": 22.0
            }

    def save_states(self):
        """
        Saves the current device states to the JSON file.
        """
        try:
            with open(self._state_file, "w") as f:
                json.dump(self.states, f)
            print("Master: States saved to file.")
        except OSError as e:
            print(f"Master: Error saving states to '{self._state_file}': {e}")

    def get_state(self, key, default=None):
        """
        Gets the state of a specific device or setting.

        :param key: The key for the state to retrieve.
        :type key: str
        :param default: The default value to return if the key is not found.
        :return: The value of the state.
        """
        return self.states.get(key, default)

    def set_state(self, key, value, save=True):
        """
        Sets the state of a device or setting.

        :param key: The key for the state to set.
        :type key: str
        :param value: The new value for the state.
        :param save: Whether to immediately save the states to the file.
        :type save: bool
        """
        self.states[key] = value
        if save:
            self.save_states()


class DeviceManager:
    """
    Manages device logic, state changes, and MQTT communication.
    """
    def __init__(self, state_manager, mqtt_command_topics):
        """
        Initializes the DeviceManager.

        :param state_manager: An instance of StateManager.
        :type state_manager: StateManager
        :param mqtt_command_topics: Dictionary mapping device names to MQTT topics
        :type mqtt_command_topics: dict
        """
        self.state_manager = state_manager
        self.mqtt_command_topics = mqtt_command_topics
        self.mqtt_client = None
        self.published_states = {}
        self._ui_update_callback = None

    def set_mqtt_client(self, client):
        """
        Sets the MQTT client instance after it has been connected.

        :param client: The connected MQTT client.
        :type client: MQTTClient
        """
        self.mqtt_client = client

    def set_ui_update_callback(self, callback):
        """
        Sets a callback function to notify UI of state changes.

        :param callback: Function to call when UI should be updated
        """
        self._ui_update_callback = callback

    def set_device_state(self, name, new_state):
        """
        Sets the state of a device and publishes the change via MQTT.

        :param name: The name of the device (e.g., "soggiorno").
        :type name: str
        :param new_state: The new state (True for ON, False for OFF).
        :type new_state: bool
        """
        print(f"Master: [STATE] Setting {name} to {'ON' if new_state else 'OFF'}")
        self.state_manager.set_state(name, new_state, save=True)
        
        # If climate control is manually changed, disable auto mode
        if name in ["aria_condizionata", "riscaldamento"]:
            self.state_manager.set_state("auto_mode", False, save=True)
            
        self._publish_state(name)

        if self._ui_update_callback:
            self._ui_update_callback()

    def _publish_state(self, name):
        """
        Publishes a device's state to its MQTT command topic.

        :param name: The name of the device.
        :type name: str
        """
        if not self.mqtt_client:
            print("Master: MQTT client not available. Cannot publish state.")
            return

        topic = MQTT_COMMAND_TOPICS.get(name)
        if not topic:
            print(f"Master: No command topic found for device '{name}'.")
            return
            
        value = b"ON" if self.state_manager.get_state(name) else b"OFF"
        
        # Special case for shutters
        if name == "tapparella":
            return # Shutters are handled differently

        # Publish only if state has changed since last publish
        if self.published_states.get(name) != value:
            try:
                self.mqtt_client.publish(topic, value, retain=True)
                self.published_states[name] = value
                print(f"Master: → MQTT: Published {topic} = {value.decode()}")
            except Exception as e:
                print(f"Master: MQTT publish error for {name}: {e}")
        else:
            print(f"Master: → MQTT: State for {name} unchanged, skipping publish.")
            
    def publish_all_states(self):
        """Publishes the current state of all devices to MQTT."""
        for name in MQTT_COMMAND_TOPICS.keys():
            if name != "tapparella": # Don't publish shutter state on startup
                self._publish_state(name)

    def pubblish_shutter_command(self, direction):
        """
        Publishes a shutter command (up/down)

        :param direction: "up" or "down"
        :type direction: str
        """
        if not self.mqtt_client:
            return

        topic = self.mqtt_command_topics.get("tapparella")
        if topic and direction in ["up", "down"]:
            try:
                self.mqtt_client.publish(topic, direction.encode())
                self.state_manager.set_state("tapparella_state", f"moving_{direction}")
                print("Master: → MQTT: Shutter command {direction}")
            except Exception as e:
                print("Master: MQTT shutter publish error: {e}")

    def mqtt_callback(self, topic, msg):
        """
        Callback function for handling incoming MQTT messages.

        :param topic: The topic the message was received on.
        :type topic: bytes
        :param msg: The message payload.
        :type msg: bytes
        """
        topic_str = topic.decode()
        msg_str = msg.decode().strip().lower()
        print(f"Master: MQTT received: {topic_str} = {msg_str}")

        updated = False
        
        # Handle temperature updates
        if topic_str == "home/status/temperature":
            try:
                temp = float(msg_str)
                self.state_manager.set_state('current_temperature', temp, save=False)
                if self.state_manager.get_state("auto_mode"):
                    self.evaluate_auto_logic()
                updated = True
            except (ValueError, TypeError):
                print(f"Master: Invalid temperature value received: {msg_str}")

        # Handle state updates from other devices
        elif topic_str.endswith("/state"):
            parts = topic_str.split('/')
            if len(parts) >= 3:
                device_name = parts[-2]
                if device_name in self.state_manager.states:
                    new_state = (msg_str == "on")
                    self.state_manager.set_state(device_name, new_state, save=True)
                    updated = True
        
        if updated and self._ui_update_callback:
            self._ui_update_callback()

    def evaluate_auto_logic(self):
        """Evaluates and acts on the climate auto mode logic."""
        if not self.state_manager.get_state("auto_mode"):
            return

        current_temp = self.state_manager.get_state("current_temperature")
        desired_temp = self.state_manager.get_state("desired_temperature")

        if current_temp is None:
            print("Master: AUTO: No temperature data, skipping.")
            return

        print(f"Master: AUTO: Evaluating. Current={current_temp}, Target={desired_temp}")
        
        # Hysteresis thresholds
        heat_on_thresh = desired_temp - 0.5
        ac_on_thresh = desired_temp + 0.5

        # Turn on heating
        if current_temp < heat_on_thresh:
            if not self.state_manager.get_state("riscaldamento"):
                self.set_device_state("riscaldamento", True)
            if self.state_manager.get_state("aria_condizionata"):
                self.set_device_state("aria_condizionata", False)
        # Turn on AC
        elif current_temp > ac_on_thresh:
            if not self.state_manager.get_state("aria_condizionata"):
                self.set_device_state("aria_condizionata", True)
            if self.state_manager.get_state("riscaldamento"):
                self.set_device_state("riscaldamento", False)
        # Turn everything off (within comfort zone)
        else:
            if self.state_manager.get_state("riscaldamento"):
                self.set_device_state("riscaldamento", False)
            if self.state_manager.get_state("aria_condizionata"):
                self.set_device_state("aria_condizionata", False)


async def main():
    """The main asynchronous entry point of the application."""
    try:
        # 1. Connect to network
        wifi.connect_wifi(WIFI_SSID, WIFI_PASS)

        # 2. Initialize managers
        state_manager = StateManager(STATE_FILE)
        device_manager = DeviceManager(state_manager)

        # 3. Inizialize display with configuration
        display_manager = DisplayManager(
            state_manager, 
            device_manager,
            standby_timeout=STANDBY_TIMEOUT)

        # 4. Initialize web server
        web_server = WebServer(state_manager, device_manager)

        # 5. Set up cross-references
        device_manager.set_ui_update_callback(display_manager.draw_page)

        # 6. Connect to MQTT
        mqtt_client = mqtt.connect_mqtt(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            callback=device_manager.mqtt_callback,
            subscriptions=MQTT_SUBSCRIPTIONS
        )
        device_manager.set_mqtt_client(mqtt_client)
        
        # 7. Publish initial states and draw UI
        device_manager.publish_all_states()
        display_manager.draw_page()
        
        # 8. Evaluate auto logic on startup
        if state_manager.get_state("auto_mode"):
            device_manager.evaluate_auto_logic()

        # 9. Start all concurrent tasks
        print("Master: Starting all system tasks.")
        await asyncio.gather(
            display_manager.standby_task(),
            display_manager.touch_loop(),
            web_server.run(),
            mqtt_check_loop(mqtt_client)
        )

    except Exception as e:
        print(f"Master: A fatal error occurred: {e}")
        # Consider a safe shutdown or reboot here
        time.sleep(10)
        machine.reset()


async def mqtt_check_loop(client):
    """Periodically checks for incoming MQTT messages."""
    while True:
        try:
            client.check_msg()
        except Exception as e:
            print(f"Master: MQTT check_msg error: {e}. Reconnecting...")
            time.sleep(5)
            reset() 
        await asyncio.sleep(1)



# Run the application
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Master: Application stopped by user.")
    finally:
        # Clean up resources
        Pin(PIN_DISP_BL, Pin.OUT).value(0)

