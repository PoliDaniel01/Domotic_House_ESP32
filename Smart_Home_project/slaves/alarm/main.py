"""
Main script for the ESP32 board managing the alarm system.

This script is responsible for:
- Monitoring sensor inputs (e.g., door/window contacts).
- Handling a physical reset button.
- Activating an indicator LED when the alarm is triggered.
- Using interrupts for all physical inputs for efficient operation.
- Communicating with the master board via MQTT to be armed/disarmed and to report its state.
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
MQTT_CLIENT_ID = "esp32-alarm-slave"

# --- Hardware Pin Configuration ---
PIN_SENSORS = [1, 2]
PIN_RESET_BTN = 3
PIN_LED = 4

# --- MQTT Topics ---
TOPIC_STATE_REPORT = b"home/sensor/alarm/state"  # To report triggered/disarmed
TOPIC_ARM_CMD = b"home/sensor/alarm/set"         # To receive arm/disarm commands

MQTT_SUBSCRIPTIONS = [TOPIC_ARM_CMD]


class AlarmManager:
    """
    Manages the state and logic of the alarm system.
    """
    def __init__(self):
        """Initializes the AlarmManager."""
        self.mqtt_client = None
        self._last_irq_time = 0

        # State machine variables
        self.is_armed = False      # Is the alarm ready to be triggered?
        self.is_triggered = False  # Is the alarm currently going off?

        self._setup_hardware()

        # To handle interrupts properly
        self.sensor_triggered_event = uasyncio.Event()
        self.reset_pressed_event = uasyncio.Event()

    def _setup_hardware(self):
        """Initializes GPIO pins for sensors, button, and LED."""
        self.led = Pin(PIN_LED, Pin.OUT, value=0)
        
        self.sensors = []
        for pin in PIN_SENSORS:
            self.sensors.append(Pin(pin, Pin.IN, Pin.PULL_UP))
        # Attach interrupts to all sensor pins
        for sensor_pin in self.sensors:
            sensor_pin.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_sensor_trigger)
            
        # Attach interrupt for the reset button
        self.reset_btn = Pin(PIN_RESET_BTN, Pin.IN, Pin.PULL_UP)
        self.reset_btn.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_reset_press)
        
        print("Alarm: Hardware pins initialized and interrupts attached.")

    def set_mqtt_client(self, client):
        """
        Sets the MQTT client instance after it has been connected.

        :param client: The connected MQTT client.
        :type client: umqtt.simple.MQTTClient
        """
        self.mqtt_client = client

    def _publish_state(self, state_msg):
        """
        Publishes the alarm's current state to MQTT.

        :param state_msg: The message to publish (e.g., b"triggered", b"disarmed").
        :type state_msg: bytes
        """
        if not self.mqtt_client:
            return
        try:
            self.mqtt_client.publish(TOPIC_STATE_REPORT, state_msg, retain=True)
            print(f"Alarm: → MQTT: Published state: {state_msg.decode()}")
        except Exception as e:
            print(f"Alarm: MQTT publish error: {e}")

    def arm_system(self):
        """Arms the alarm system, making it ready to be triggered."""
        if not self.is_armed:
            self.is_armed = True
            print("Alarm: Alarm system ARMED.")
            # Short blink to confirm arming
            self.led.on()
            await uasyncio.sleep_ms(100) # non blocking
            self.led.off()

    def disarm_system(self):
        """Disarms the alarm, stopping any active trigger and preventing new ones."""
        if self.is_armed or self.is_triggered:
            self.is_armed = False
            self.is_triggered = False
            self.led.off() # Ensure LED is off
            print("Alarm: Alarm system DISARMED.")
            self._publish_state(b"disarmed")

    def trigger_alarm(self):
        """Activates the alarm trigger state."""
        if not self.is_triggered:
            self.is_triggered = True
            print("Alarm: ALARM TRIGGERED!")
            self._publish_state(b"triggered")
            # The async blinking task will take over the LED.

    def mqtt_callback(self, topic, msg):
        """
        Callback for handling incoming MQTT arm/disarm commands.

        :param topic: The topic the message was received on.
        :type topic: bytes
        :param msg: The message payload.
        :type msg: bytes
        """
        if topic == TOPIC_ARM_CMD:
            command = msg.decode().strip().lower()
            print(f"Alarm: MQTT command received: {command}")
            if command == "on":
                self.arm_system()
            elif command == "off":
                self.disarm_system()

    def _is_debounced(self, min_interval_ms=1000):
        """Checks if the time since last interrpt is sufficient"""
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self._last_irq_time) < 1000: # 1s debounce
            return False
        self._last_irq_time = current_time
        return True


    def handle_sensor_trigger(self, pin):
        """
        ISR for sensor pins. Triggers the alarm only if the system is armed.

        :param pin: The Pin object that triggered the interrupt.
        :type pin: machine.Pin
        """
        if not self.is_armed or self.is_triggered:
            return # Ignore sensor if disarmed or already triggered

        if self._is_debounced():
            self.sensor_triggered_event.set()

    def handle_reset_press(self, pin):
        """
        ISR for the reset button. Disarms the system.

        :param pin: The Pin object that triggered the interrupt.
        :type pin: machine.Pin
        """
        if self._is_debounced():
            self.reset_pressed_event.set()


async def led_blink_task(manager):
    """Asynchronous task to blink the LED when the alarm is triggered."""
    while True:
        if manager.is_triggered:
            manager.led.toggle()
            await uasyncio.sleep_ms(500)
        else:
            # If not triggered, ensure LED is off and wait efficiently.
            manager.led.off()
            await uasyncio.sleep_ms(100)


async def mqtt_loop(client):
    """Periodically checks for incoming MQTT messages."""
    while True:
        try:
            client.check_msg()
        except Exception as e:
            print(f"Alarm: MQTT check_msg error: {e}. Resetting...")
            await uasyncio.sleep(5)
            reset()
        await uasyncio.sleep_ms(200)


async def event_handler_task(manager):
    """Event handler, manages manager's interrupts flags. It's asynchronous so it's not blocking"""
    while True:
        if manager.sensor_triggered_event.is_set():
            manager.sensor_triggered_event.clear()
            if manager.is_armed and not manager.is_triggered:
                manager.trigger_alarm()
        if manager.reset_pressed_event.is_set():
            manager.reset_pressed_event.clear()
            print("Alarm: Reset button pressed.")
            manager.disarm_system()

        await uasyncio.sleep_ms(50)


async def main():
    """The main asynchronous entry point of the application."""
    try:
        manager = AlarmManager()
        wifi.connect_wifi(WIFI_SSID, WIFI_PASS)
        mqtt_client = mqtt.connect_mqtt(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            callback=manager.mqtt_callback,
            subscriptions=MQTT_SUBSCRIPTIONS
        )
        manager.set_mqtt_client(mqtt_client)
        
        # Report initial state as disarmed
        manager._publish_state(b"disarmed")
        
        print("Alarm: Application running. Starting tasks.")
        await uasyncio.gather(
            led_blink_task(manager),
            mqtt_loop(mqtt_client),
            event_handler_task(manager),
        )

    except Exception as e:
        print(f"Alarm: A fatal error occurred in main: {e}")
        await uasyncio.sleep(10)
        reset()

# Run the application
if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print("Alarm: Application stopped by user.")

