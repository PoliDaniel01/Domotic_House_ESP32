from machine import Pin, I2C
import time
import network
from umqtt.simple import MQTTClient
from bme680 import BME680_I2C
from collections import deque

# ===========================
# CONFIG
# ===========================
WIFI_SSID = ""
WIFI_PASS = ""
MQTT_BROKER = ""

TOPIC_RISC_CMD = b"home/led/riscaldamento/command"
TOPIC_RISC_STATE = b"home/led/riscaldamento/state"

TOPIC_ARIA_CMD = b"home/led/aria_condizionata/command"
TOPIC_ARIA_STATE = b"home/led/aria_condizionata/state"

TOPIC_TEMP_STAT = b"home/status/temperature"
TOPIC_AUTO_MODE = b"home/auto_mode/command"
TOPIC_DES_TEMP = b"home/desired_temperature/command"

# ===========================
# RELÈ
# ===========================
rele_risc = Pin(10, Pin.OUT)
rele_risc.value(0)

rele_cond = Pin(11, Pin.OUT)
rele_cond.value(0)

state_risc = False
state_cond = False

last_state_risc = None
last_state_cond = None

client = None

# ===========================
# PULSANTI
# ===========================
button_risc = Pin(4, Pin.IN, Pin.PULL_UP)
button_cond = Pin(5, Pin.IN, Pin.PULL_UP)

event_queue = deque([], 50)

def handle_button_risc(pin):
    global auto_mode
    auto_mode = False
    event_queue.append(("TOGGLE_RISC", time.ticks_ms()))

def handle_button_cond(pin):
    global auto_mode
    auto_mode = False
    event_queue.append(("TOGGLE_COND", time.ticks_ms()))

button_risc.irq(trigger=Pin.IRQ_FALLING, handler=handle_button_risc)
button_cond.irq(trigger=Pin.IRQ_FALLING, handler=handle_button_cond)

# ===========================
# BME680 INIT
# ===========================
try:
    i2c = I2C(0, sda=Pin(8), scl=Pin(9))
    bme = BME680_I2C(i2c=i2c)
    print("✅ BME680 inizializzato correttamente.")
except Exception as e:
    print("⚠️ Errore inizializzazione BME680:", e)
    bme = None

# ===========================
# LEGGI TEMPERATURA
# ===========================
def read_temperature_sensor():
    try:
        if bme:
            temp = bme.temperature
            print(f"→ Temperatura letta dal BME680: {temp:.1f} °C")
            if temp < -40 or temp > 100:
                print("⚠️ Temperatura fuori range. Ignoro lettura.")
                return None
            return temp
        else:
            return None
    except Exception as e:
        print("⚠️ Errore lettura BME680:", e)
        return None

# ===========================
# PUBBLICA TEMPERATURA
# ===========================
def publish_temperature():
    temp = read_temperature_sensor()
    if temp is not None:
        payload = f"{temp:.1f}".encode()
        try:
            client.publish(TOPIC_TEMP_STAT, payload, retain=True)
            print("→ Temperatura pubblicata su MQTT:", payload.decode())
        except Exception as e:
            print("Errore publish temperatura:", e)

# ===========================
# LOGICA AUTO CON HYSTERESIS
# ===========================
desired_temperature = 22
auto_mode = False

def check_auto_mode(temp):
    global state_risc, state_cond
    if temp is None:
        print("⚠️ Nessuna temperatura per AUTO.")
        return

    print(f"→ AUTO_MODE LOGIC temp={temp} target={desired_temperature}")

    # Hysteresis logic
    if state_risc:
        if temp > desired_temperature + 0.5:
            set_riscaldamento(False)
    elif state_cond:
        if temp < desired_temperature - 0.5:
            set_aria(False)
    else:
        if temp < desired_temperature - 0.5:
            set_riscaldamento(True)
        elif temp > desired_temperature + 0.5:
            set_aria(True)

# ===========================
# FUNZIONI RELÈ
# ===========================
def set_riscaldamento(onoff):
    global state_risc, state_cond
    if onoff:
        if state_cond:
            set_aria(False)
            print("⚠️ AUTO: spengo aria per accendere riscaldamento")
        state_risc = True
        rele_risc.value(1)
        publish_state_risc()
        print("→ Riscaldamento ACCESO")
    else:
        state_risc = False
        rele_risc.value(0)
        publish_state_risc()
        print("→ Riscaldamento SPENTO")

def set_aria(onoff):
    global state_cond, state_risc
    if onoff:
        if state_risc:
            set_riscaldamento(False)
            print("⚠️ AUTO: spengo riscaldamento per accendere aria")
        state_cond = True
        rele_cond.value(1)
        publish_state_cond()
        print("→ Aria condizionata ACCESA")
    else:
        state_cond = False
        rele_cond.value(0)
        publish_state_cond()
        print("→ Aria condizionata SPENTA")

# ===========================
# MQTT CALLBACK
# ===========================
def mqtt_callback(topic, msg):
    global auto_mode, desired_temperature
    print("MQTT message received:", topic, msg)

    if topic == TOPIC_RISC_CMD:
        auto_mode = False
        set_riscaldamento(msg == b"ON")

    elif topic == TOPIC_ARIA_CMD:
        auto_mode = False
        set_aria(msg == b"ON")

    elif topic == TOPIC_AUTO_MODE:
        auto_mode = (msg == b"ON")
        print("→ AUTO_MODE", auto_mode)
        if auto_mode:
            temp_now = read_temperature_sensor()
            check_auto_mode(temp_now)

    elif topic == TOPIC_DES_TEMP:
        try:
            desired_temperature = float(msg.decode())
            print("→ Temperatura desiderata aggiornata:", desired_temperature)
            if auto_mode:
                temp_now = read_temperature_sensor()
                check_auto_mode(temp_now)
        except Exception as e:
            print("⚠️ Errore parsing temperatura desiderata:", e)

    elif topic == TOPIC_TEMP_STAT:
        try:
            temp_slave = float(msg.decode())
            if auto_mode:
                check_auto_mode(temp_slave)
        except:
            pass

# ===========================
# PUBBLICA STATI
# ===========================
def publish_state_risc():
    global last_state_risc
    val = b"ON" if state_risc else b"OFF"
    if val != last_state_risc:
        try:
            client.publish(TOPIC_RISC_STATE, val, retain=True)
            last_state_risc = val
            print("→ Stato riscaldamento pubblicato:", val)
        except Exception as e:
            print("Errore publish riscaldamento:", e)

def publish_state_cond():
    global last_state_cond
    val = b"ON" if state_cond else b"OFF"
    if val != last_state_cond:
        try:
            client.publish(TOPIC_ARIA_STATE, val, retain=True)
            last_state_cond = val
            print("→ Stato aria pubblicato:", val)
        except Exception as e:
            print("Errore publish aria:", e)

# ===========================
# CONNECT WIFI
# ===========================
def connect_wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(WIFI_SSID, WIFI_PASS)
    while not sta.isconnected():
        print("Connessione WiFi...")
        time.sleep(1)
    print("✅ WiFi connesso:", sta.ifconfig())

# ===========================
# CONNECT MQTT
# ===========================
def connect_mqtt():
    global client
    client = MQTTClient("esp32-slave-clima", MQTT_BROKER)
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(TOPIC_RISC_CMD)
    client.subscribe(TOPIC_ARIA_CMD)
    client.subscribe(TOPIC_TEMP_STAT)
    client.subscribe(TOPIC_AUTO_MODE)
    client.subscribe(TOPIC_DES_TEMP)
    print("✅ MQTT connesso e sottoscritto.")

# ===========================
# MAIN LOOP
# ===========================
def main():
    connect_wifi()
    connect_mqtt()

    publish_state_risc()
    publish_state_cond()
    publish_temperature()

    last_temp_time = time.ticks_ms()
    debounce_times = {"TOGGLE_RISC": 0, "TOGGLE_COND": 0}

    while True:
        try:
            client.check_msg()
        except Exception as e:
            print("MQTT error:", e)
            try:
                client.disconnect()
            except:
                pass
            time.sleep(2)
            connect_mqtt()

        while event_queue:
            evt, evt_time = event_queue.popleft()
            if time.ticks_diff(evt_time, debounce_times[evt]) > 300:
                debounce_times[evt] = evt_time

                if evt == "TOGGLE_RISC":
                    auto_mode = False
                    set_riscaldamento(not state_risc)

                elif evt == "TOGGLE_COND":
                    auto_mode = False
                    set_aria(not state_cond)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_temp_time) >= 5 * 60 * 1000:
            publish_temperature()
            last_temp_time = now

        time.sleep(0.05)

# 🚀 AVVIO
main()
