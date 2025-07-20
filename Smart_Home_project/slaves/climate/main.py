"""
Main script for the ESP32 board managing climate control.

This script is responsible for:
- Reading temperature data from a BME680 sensor.
- Controlling heating and air conditioning relays.
- Handling physical button presses for manual control.
- Implementing an "auto mode" with hysteresis to maintain a desired temperature.
- Communicating with the master board via MQTT for commands and state reporting.
"""

# Standard library imports
import time
import uasyncio

# MicroPython-specific imports
from machine import Pin, I2C

# Third-party library imports
try:
    from bme680 import BME680_I2C
except ImportError:
    print("Lights: Warning: 'bme680' library not found. Climate sensor will not work.")
    BME680_I2C = None

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
MQTT_CLIENT_ID = "esp32-climate-slave"

# --- Hardware Pin Configuration ---
PIN_I2C_SDA = 8
PIN_I2C_SCL = 9
PIN_RELE_RISC = 10  # Heating relay
PIN_RELE_COND = 11  # Air Conditioning relay
PIN_BTN_RISC = 4
PIN_BTN_COND = 5

# --- Application Settings ---
TEMP_PUBLISH_INTERVAL = 300  # Seconds (5 minutes)
HYSTERESIS_OFFSET = 0.5      # Degrees Celsius

# --- MQTT Topics ---
TOPIC_RISC_CMD = b"home/led/riscaldamento/command"
TOPIC_RISC_STATE = b"home/led/riscaldamento/state"
TOPIC_ARIA_CMD = b"home/led/aria_condizionata/command"
TOPIC_ARIA_STATE = b"home/led/aria_condizionata/state"
TOPIC_TEMP_STAT = b"home/status/temperature"
TOPIC_AUTO_MODE_CMD = b"home/auto_mode/command"
TOPIC_DES_TEMP_CMD = b"home/desired_temperature/command"

MQTT_SUBSCRIPTIONS = [
    TOPIC_RISC_CMD,
    TOPIC_ARIA_CMD,
    TOPIC_AUTO_MODE_CMD,
    TOPIC_DES_TEMP_CMD,
]


class ClimateManager:
    """
    Manages the climate control system, including sensor, relays, and logic.
    """
    def __init__(self):
        """Initializes the ClimateManager."""
        self.mqtt_client = None
        self._last_irq_time = 0

        # State variables
        self.state_risc = False
        self.state_cond = False
        self.auto_mode = False
        self.desired_temperature = 22.0
        
        self._setup_hardware()

    def _setup_hardware(self):
        """Initializes all hardware components (sensor, relays, buttons)."""
        # Relays
        self.rele_risc = Pin(PIN_RELE_RISC, Pin.OUT, value=0)
        self.rele_cond = Pin(PIN_RELE_COND, Pin.OUT, value=0)

        # Buttons with interrupts
        self.btn_risc = Pin(PIN_BTN_RISC, Pin.IN, Pin.PULL_UP)
        self.btn_cond = Pin(PIN_BTN_COND, Pin.IN, Pin.PULL_UP)
        self.btn_risc.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_button_press)
        self.btn_cond.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_button_press)

        # BME680 Sensor
        self.bme_sensor = None
        if BME680_I2C:
            try:
                i2c = I2C(0, sda=Pin(PIN_I2C_SDA), scl=Pin(PIN_I2C_SCL))
                self.bme_sensor = BME680_I2C(i2c=i2c)
                print("Climate: BME680 sensor initialized.")
            except Exception as e:
                print(f"Climate: Failed to initialize BME680 sensor: {e}")
        else:
            print("Climate: BME680 library not available, continuing without sensor.")

    def set_mqtt_client(self, client):
        """
        Sets the MQTT client instance after it has been connected.

        :param client: The connected MQTT client.
        :type client: umqtt.simple.MQTTClient
        """
        self.mqtt_client = client

    def _publish_state(self, topic, state):
        """
        Generic method to publish a state to an MQTT topic.

        :param topic: The MQTT topic to publish to.
        :type topic: bytes
        :param state: The state to publish (True for ON, False for OFF).
        :type state: bool
        """
        if not self.mqtt_client:
            return
        msg = b"ON" if state else b"OFF"
        try:
            self.mqtt_client.publish(topic, msg, retain=True)
            print(f"Climate: → MQTT: Published {topic.decode()} = {msg.decode()}")
        except Exception as e:
            print(f"Climate: MQTT publish error for {topic.decode()}: {e}")

    def set_heating(self, new_state, source="mqtt"):
        """
        Controls the heating relay. Ensures AC is off if heating is turned on.

        :param new_state: The new state for the heating (True for ON, False for OFF).
        :type new_state: bool
        :param source: The origin of the command ('mqtt', 'button', 'auto').
        :type source: str
        """
        if self.state_risc == new_state:
            return # No change needed

        if new_state and self.state_cond:
            self.set_conditioning(False, source="auto_override")

        self.state_risc = new_state
        self.rele_risc.value(1 if new_state else 0)
        print(f"Climate: Heating turned {'ON' if new_state else 'OFF'} (source: {source})")
        self._publish_state(TOPIC_RISC_STATE, new_state)

    def set_conditioning(self, new_state, source="mqtt"):
        """
        Controls the AC relay. Ensures heating is off if AC is turned on.

        :param new_state: The new state for the AC (True for ON, False for OFF).
        :type new_state: bool
        :param source: The origin of the command ('mqtt', 'button', 'auto').
        :type source: str
        """
        if self.state_cond == new_state:
            return # No change needed

        if new_state and self.state_risc:
            self.set_heating(False, source="auto_override")

        self.state_cond = new_state
        self.rele_cond.value(1 if new_state else 0)
        print(f"Climate: A/C turned {'ON' if new_state else 'OFF'} (source: {source})")
        self._publish_state(TOPIC_ARIA_STATE, new_state)

    def read_and_publish_temperature(self):
        """Reads temperature from the sensor and publishes it to MQTT."""
        if not self.bme_sensor:
            return
        
        try:
            temp = self.bme_sensor.temperature
            if -40 < temp < 100: # Sanity check
                payload = f"{temp:.1f}".encode()
                self.mqtt_client.publish(TOPIC_TEMP_STAT, payload, retain=True)
                print(f"Climate:  Temperature published: {payload.decode()} C")
                return temp
            else:
                print(f"Climate: Unrealistic temperature reading: {temp}. Ignoring.")
        except Exception as e:
            print(f"Climate: Error reading BME680 sensor: {e}")
        return None

    def evaluate_auto_logic(self, current_temp):
        """
        Evaluates and acts on the climate auto mode logic based on temperature.

        :param current_temp: The current temperature reading.
        :type current_temp: float
        """
        if not self.auto_mode or current_temp is None:
            return

        print(f"Climate: AUTO: Evaluating. Current={current_temp:.1f}C, Target={self.desired_temperature:.1f}C")

        # Hysteresis logic
        if current_temp < self.desired_temperature - HYSTERESIS_OFFSET:
            self.set_heating(True, source="auto")
        elif current_temp > self.desired_temperature + HYSTERESIS_OFFSET:
            self.set_conditioning(True, source="auto")
        else: # Temperature is within the comfort zone
            self.set_heating(False, source="auto")
            self.set_conditioning(False, source="auto")

    def mqtt_callback(self, topic, msg):
        """
        Callback function for handling incoming MQTT messages.

        :param topic: The topic the message was received on.
        :type topic: bytes
        :param msg: The message payload.
        :type msg: bytes
        """
        print(f"Climate: MQTT received: {topic.decode()} = {msg.decode()}")
        
        if topic == TOPIC_RISC_CMD:
            self.auto_mode = False
            self.set_heating(msg == b"ON", source="mqtt")
        elif topic == TOPIC_ARIA_CMD:
            self.auto_mode = False
            self.set_conditioning(msg == b"ON", source="mqtt")
        elif topic == TOPIC_AUTO_MODE_CMD:
            self.auto_mode = (msg == b"ON")
            print(f"Climate: Auto mode set to: {self.auto_mode}")
            # Immediately evaluate logic if auto mode is turned on
            if self.auto_mode:
                temp = self.read_and_publish_temperature()
                self.evaluate_auto_logic(temp)
        elif topic == TOPIC_DES_TEMP_CMD:
            try:
                self.desired_temperature = float(msg)
                print(f"Climate: Desired temperature set to: {self.desired_temperature}")
                if self.auto_mode:
                    temp = self.read_and_publish_temperature()
                    self.evaluate_auto_logic(temp)
            except (ValueError, TypeError):
                print(f"Climate: Invalid desired temperature value: {msg}")

    def handle_button_press(self, pin):
        """
        Interrupt Service Routine (ISR) for button presses.
        
        :param pin: The Pin object that triggered the interrupt.
        :type pin: machine.Pin
        """
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self._last_irq_time) < 300: # 300ms debounce
            return
        self._last_irq_time = current_time

        # A button press always disables auto mode
        self.auto_mode = False
        print("Climate: Button pressed, auto mode disabled.")

        if pin == self.btn_risc:
            self.set_heating(not self.state_risc, source="button")
        elif pin == self.btn_cond:
            self.set_conditioning(not self.state_cond, source="button")

    def publish_initial_states(self):
        """Publishes the initial state of all controlled devices."""
        self._publish_state(TOPIC_RISC_STATE, self.state_risc)
        self._publish_state(TOPIC_ARIA_STATE, self.state_cond)
        self.read_and_publish_temperature()


async def temperature_loop(manager):
    """Periodically reads and publishes the temperature."""
    while True:
        temp = manager.read_and_publish_temperature()
        manager.evaluate_auto_logic(temp)
        await uasyncio.sleep(TEMP_PUBLISH_INTERVAL)


async def mqtt_loop(client):
    """Periodically checks for incoming MQTT messages."""
    while True:
        try:
            client.check_msg()
        except Exception as e:
            print(f"Climate: MQTT check_msg error: {e}. Reconnecting...")
            time.sleep(5)
            machine.reset()
        await uasyncio.sleep_ms(200)


async def main():
    """The main asynchronous entry point of the application."""
    try:
        manager = ClimateManager()
        wifi.connect_wifi(WIFI_SSID, WIFI_PASS)
        mqtt_client = mqtt.connect_mqtt(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            callback=manager.mqtt_callback,
            subscriptions=MQTT_SUBSCRIPTIONS
        )
        manager.set_mqtt_client(mqtt_client)
        manager.publish_initial_states()
        
        print("Climate: Application running. Starting tasks.")
        await uasyncio.gather(
            temperature_loop(manager),
            mqtt_loop(mqtt_client),
        )

    except Exception as e:
        print(f"Climate: A fatal error occurred in main: {e}")
        time.sleep(10)
        machine.reset()

# Run the application
if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print("Climate: Application stopped by user.")

