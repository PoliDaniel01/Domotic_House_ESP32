"""
Main script for the ESP32 board controlling the window shutters.

This script is responsible for:
- Controlling a motor to move shutters up and down.
- Handling physical button presses for manual control.
- Using interrupts for button handling for maximum efficiency.
- Using asynchronous tasks to manage motor run-time without blocking.
- Communicating with the master board via MQTT to receive commands and report state.
"""

# Standard library imports
import time
import uasyncio

# MicroPython-specific imports
from machine import Pin, reset

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
MQTT_CLIENT_ID = "esp32-shutters-slave"

# --- Hardware Pin Configuration ---
PIN_BTN_UP = 9
PIN_BTN_DOWN = 8
PIN_MOTOR_UP = 5
PIN_MOTOR_DOWN = 4

# --- Application Settings ---
MOTOR_RUN_TIME_MS = 2000  # Milliseconds to run the motor for a full open/close

# --- MQTT Topics ---
TOPIC_CMD = b"home/actuator/tapparella/set"
TOPIC_STATE = b"home/actuator/tapparella/state" # Reports open, closed, moving
MQTT_SUBSCRIPTIONS = [TOPIC_CMD]


class ShuttersManager:
    """
    Manages the state and hardware for the window shutters.
    """
    def __init__(self):
        """Initializes the ShuttersManager."""
        self.mqtt_client = None
        self._last_irq_time = 0

        # State machine: 'open', 'closed', 'moving_up', 'moving_down', 'unknown'
        self.state = "unknown"
        self.motor_task = None  # To hold the reference to the running motor task

        self._setup_hardware()

        self.btn_up_triggered_event = uasyncio.Event()
        self.btn_down_triggered_event = uasyncio.Event()

    def _setup_hardware(self):
        """Initializes GPIO pins for motors and buttons."""
        self.motor_up = Pin(PIN_MOTOR_UP, Pin.OUT, value=0)
        self.motor_down = Pin(PIN_MOTOR_DOWN, Pin.OUT, value=0)

        # Attach interrupts for buttons
        self.btn_up = Pin(PIN_BTN_UP, Pin.IN, Pin.PULL_UP)
        self.btn_down = Pin(PIN_BTN_DOWN, Pin.IN, Pin.PULL_UP)
        self.btn_up.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_button_press)
        self.btn_down.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_button_press)
        
        print("Shutters: Hardware pins initialized and interrupts attached.")

    def set_mqtt_client(self, client):
        """
        Sets the MQTT client instance after it has been connected.

        :param client: The connected MQTT client.
        :type client: umqtt.simple.MQTTClient
        """
        self.mqtt_client = client

    def _publish_state(self):
        """Publishes the shutter's current state to MQTT."""
        if not self.mqtt_client:
            return
        try:
            self.mqtt_client.publish(TOPIC_STATE, self.state.encode(), retain=True)
            print(f"Shutters: → MQTT: Published state: {self.state}")
        except Exception as e:
            print(f"Shutters: MQTT publish error: {e}")

    def move_shutter(self, direction):
        """
        Initiates the shutter movement by creating an asynchronous task.

        :param direction: The direction to move ('up' or 'down').
        :type direction: str
        """
        # Prevent starting a new move if one is already in progress
        if self.motor_task is not None:
            print("Shutters: Motor is already running. Ignoring command.")
            return

        # Prevent moving if already in the target state
        if (direction == "up" and self.state == "open") or \
           (direction == "down" and self.state == "closed"):
            print(f"Shutters: Shutter is already {self.state}. Ignoring command.")
            return

        print(f"Shutters: Starting shutter move: {direction}")
        self.motor_task = uasyncio.create_task(self._run_motor(direction))

    async def _run_motor(self, direction):
        """
        Asynchronous task to run the motor for a fixed duration.
        This function should not be called directly.

        :param direction: The direction of movement ('up' or 'down').
        :type direction: str
        """
        # 1. Set state to moving and publish
        self.state = "moving_up" if direction == "up" else "moving_down"
        self._publish_state()

        # 2. Activate the correct motor
        motor_pin = self.motor_up if direction == "up" else self.motor_down
        motor_pin.on()

        # 3. Wait for the configured run time (non-blocking)
        await uasyncio.sleep_ms(MOTOR_RUN_TIME_MS)

        # 4. Stop the motor
        motor_pin.off()

        # 5. Set the final state and publish
        self.state = "open" if direction == "up" else "closed"
        self._publish_state()

        # 6. Clear the task reference to allow new moves
        self.motor_task = None
        print(f"Shutters: Shutter move '{direction}' complete.")

    def mqtt_callback(self, topic, msg):
        """
        Callback for handling incoming MQTT messages.

        :param topic: The topic the message was received on.
        :type topic: bytes
        :param msg: The message payload.
        :type msg: bytes
        """
        if topic == TOPIC_CMD:
            direction = msg.decode().strip().lower()
            print(f"Shutters: MQTT command received: {direction}")
            if direction in ["up", "down"]:
                self.move_shutter(direction)

    def _is_debounced(self, min_interval_ms=1000):
        """Checks if the time since last interrpt is sufficient"""
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self._last_irq_time) < 1000: # 1s debounce
            return False
        self._last_irq_time = current_time
        return True


    def handle_button_press(self, pin):
        """
        ISR for the up/down buttons.

        :param pin: The Pin object that triggered the interrupt.
        :type pin: machine.Pin
        """
        if self._is_debounced():
            if pin == self.btn_up:
                self.btn_up_triggered_event.set()
            elif pin == self.btn_down:
                self.btn_down_triggered_event.set()


async def mqtt_loop(client):
    """Periodically checks for incoming MQTT messages."""
    while True:
        try:
            client.check_msg()
        except Exception as e:
            print(f"Shutters: MQTT check_msg error: {e}. Resetting...")
            await uasyncio.sleep(5)
            reset()
        await uasyncio.sleep_ms(200)


async def button_handler_task(manager):
    """
    Asynchronous task to handle logic after a button press.

    This task safely waits for an event from the ISR, then performs
    the state changes and MQTT publishing.

    :param manager: The instance of ShutterstManager class.
    """
    while True:
        if manager.btn_up_triggered_event.is_set():
            manager.btn_up_triggered_event.clear()
            manager.move_shutter("up")
        elif manager.btn_down_triggered_event.is_set():
            manager.btn_down_triggered_event.clear()
            manager.move_shutter("down")

        # Wait a short period before checking again to yield control.
        await uasyncio.sleep_ms(50)

async def main():
    """The main asynchronous entry point of the application."""
    try:
        manager = ShuttersManager()
        wifi.connect_wifi(WIFI_SSID, WIFI_PASS)
        mqtt_client = mqtt.connect_mqtt(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            callback=manager.mqtt_callback,
            subscriptions=MQTT_SUBSCRIPTIONS
        )
        manager.set_mqtt_client(mqtt_client)
        
        # Report initial state as unknown, master can command it to a known state
        manager._publish_state()
        
        print("Shutters: Application running. Starting tasks.")
        # The only background task needed is the MQTT loop.
        # Motor control is handled by tasks created on-demand.
        await uasyncio.gather(
            mqtt_loop(mqtt_client),
            button_handler_task(manager),
        )

    except Exception as e:
        print(f"Shutters: A fatal error occurred in main: {e}")
        await uasyncio.sleep(10)
        reset()

# Run the application
if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print("Shutters: Application stopped by user.")

