"""
Main script for the ESP32 board controlling the lights.

This script is responsible for:
- Controlling multiple lights connected to its GPIO pins.
- Handling physical button presses to toggle the lights.
- Connecting to Wi-Fi and an MQTT broker to receive commands and report state.
- Using interrupts for button handling to be more efficient than polling.
"""

# Standard library imports
import time
import uasyncio

# MicroPython-specific imports
from machine import Pin

# Local application/library specific imports
from smarthome.common import wifi, mqtt

# ==============================
# CONFIGURATION
# ==============================
# --- Wi-Fi Configuration ---
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

# --- MQTT Configuration ---
MQTT_BROKER = "YOUR_MQTT_BROKER_IP"
MQTT_CLIENT_ID = "esp32-lights-slave"

# --- Hardware and Device Mapping ---
# This dictionary maps a light's name to its specific configuration.
LIGHTS_CONFIG = {
    "soggiorno": {"led_pin": 4, "btn_pin": 21},
    "cucina":    {"led_pin": 16, "btn_pin": 22},
    "camera":    {"led_pin": 17, "btn_pin": 23},
}

# --- MQTT Topic Generation ---
# Automatically create the topics based on the lights' names.
MQTT_COMMAND_TOPICS = {f"home/led/{name}/command".encode(): name for name in LIGHTS_CONFIG}
MQTT_STATE_TOPICS = {name: f"home/led/{name}/state".encode() for name in LIGHTS_CONFIG}
MQTT_SUBSCRIPTIONS = list(MQTT_COMMAND_TOPICS.keys())


class LightsManager:
    """
    Manages the state and hardware for all lights connected to this board.
    """
    def __init__(self, config):
        """
        Initializes the LightsManager.

        :param config: A dictionary defining the lights and their pins.
        :type config: dict
        """
        self.config = config
        self.states = {name: False for name in config}
        self.pins = {}
        self.mqtt_client = None
        self._last_irq_time = 0 # For debouncing all buttons

        self._setup_pins()

    def _setup_pins(self):
        """Initializes GPIO pins for LEDs and buttons based on the config."""
        for name, pin_map in self.config.items():
            led = Pin(pin_map["led_pin"], Pin.OUT, value=0)
            btn = Pin(pin_map["btn_pin"], Pin.IN, Pin.PULL_UP)
            
            # Set up the interrupt for the button
            btn.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_button_press)
            
            self.pins[name] = {"led": led, "btn": btn}
        print("Lights: Hardware pins initialized and interrupts attached.")

    def set_mqtt_client(self, client):
        """
        Sets the MQTT client instance after it has been connected.

        :param client: The connected MQTT client.
        :type client: umqtt.simple.MQTTClient
        """
        self.mqtt_client = client

    def set_light_state(self, name, new_state, source="mqtt"):
        """
        Sets the state of a light and updates its physical LED.

        :param name: The name of the light to change.
        :type name: str
        :param new_state: The new state (True for ON, False for OFF).
        :type new_state: bool
        :param source: The origin of the state change ('mqtt' or 'button').
        :type source: str
        """
        if name not in self.states:
            print(f"Lights Attempted to set state for unknown light: {name}")
            return
            
        if self.states[name] != new_state:
            self.states[name] = new_state
            self.pins[name]["led"].value(1 if new_state else 0)
            print(f"Lights Light '{name}' turned {'ON' if new_state else 'OFF'} (source: {source})")
            self.publish_state(name)
        else:
            print(f"Lights Light '{name}' state is already {'ON' if new_state else 'OFF'}. No change.")

    def publish_state(self, name):
        """
        Publishes the current state of a specific light to its MQTT state topic.

        :param name: The name of the light whose state will be published.
        :type name: str
        """
        if not self.mqtt_client:
            print("Lights: MQTT client not available. Cannot publish state.")
            return
            
        topic = MQTT_STATE_TOPICS.get(name)
        if not topic:
            print(f"Lights: No state topic found for light '{name}'.")
            return
            
        msg = b"ON" if self.states[name] else b"OFF"
        try:
            self.mqtt_client.publish(topic, msg, retain=True)
            print(f"→ MQTT: Published {topic.decode()} = {msg.decode()}")
        except Exception as e:
            print(f"Lights: MQTT publish error for {name}: {e}")

    def publish_all_states(self):
        """Publishes the current state of all lights to MQTT."""
        print("Lights: Publishing initial state for all lights...")
        for name in self.states:
            self.publish_state(name)

    def mqtt_callback(self, topic, msg):
        """
        Callback function for handling incoming MQTT messages.

        :param topic: The topic the message was received on.
        :type topic: bytes
        :param msg: The message payload.
        :type msg: bytes
        """
        name = MQTT_COMMAND_TOPICS.get(topic)
        if name:
            new_state = (msg == b"ON")
            self.set_light_state(name, new_state, source="mqtt")

    def handle_button_press(self, pin):
        """
        Interrupt Service Routine (ISR) for button presses.
        
        This function is called by the hardware when a button pin goes from high to low.
        It includes a debounce mechanism to prevent multiple triggers from a single press.

        :param pin: The Pin object that triggered the interrupt.
        :type pin: machine.Pin
        """
        # Debounce: Ignore interrupts that occur too close to each other.
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self._last_irq_time) < 300: # 300ms debounce
            return
        self._last_irq_time = current_time

        # Find which button was pressed
        for name, pin_map in self.pins.items():
            if pin_map["btn"] == pin:
                # Toggle the state
                new_state = not self.states[name]
                self.set_light_state(name, new_state, source="button")
                break


async def main():
    """The main asynchronous entry point of the application."""
    try:
        # 1. Initialize manager
        manager = LightsManager(LIGHTS_CONFIG)
        
        # 2. Connect to network
        wifi.connect_wifi(WIFI_SSID, WIFI_PASS)

        # 3. Connect to MQTT
        mqtt_client = mqtt.connect_mqtt(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            callback=manager.mqtt_callback,
            subscriptions=MQTT_SUBSCRIPTIONS
        )
        manager.set_mqtt_client(mqtt_client)
        
        # 4. Publish initial states
        manager.publish_all_states()
        
        # 5. Keep the main loop running to check for MQTT messages
        print("Lights: Application running. Waiting for button presses and MQTT messages.")
        while True:
            try:
                # check_msg() is blocking, but with a short sleep, it yields control
                # allowing other async tasks (if any) to run. In this simple case,
                # it's just to keep the connection alive and process messages.
                mqtt_client.check_msg()
            except Exception as e:
                print(f"Lights: MQTT check_msg error: {e}. Reconnecting...")
                time.sleep(5)
                machine.reset()
            await uasyncio.sleep_ms(100)

    except Exception as e:
        print(f"Lights: A fatal error occurred: {e}")
        time.sleep(10)
        machine.reset()

# Run the application
if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print("Lights: Application stopped by user.")

