from machine import Pin, I2C
import time
import network
from umqtt.simple import MQTTClient
from bme680 import BME680_I2C

# ===========================
# CONFIG
# ===========================
WIFI_SSID = ""
WIFI_PASS = ""
MQTT_BROKER = ""

TOPIC_RISCALDAMENTO_CMD = b"home/led/riscaldamento/command"
TOPIC_RISCALDAMENTO_STATE = b"home/led/riscaldamento/state"

TOPIC_ARIA_CMD = b"home/led/aria_condizionata/command"
TOPIC_ARIA_STATE = b"home/led/aria_condizionata/state"

TOPIC_TEMPERATURE_STAT = b"home/status/temperature"

# ===========================
# RELÈ
# ===========================
rele_risc = Pin(10, Pin.OUT)
rele_risc.value(0)

rele_cond = Pin(11, Pin.OUT)
rele_cond.value(0)

state_risc = False
state_cond = False

client = None

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
            client.publish(TOPIC_TEMPERATURE_STAT, payload, retain=True)
            print("→ Temperatura pubblicata su MQTT:", payload.decode())
        except Exception as e:
            print("Errore publish temperatura:", e)

# ===========================
# LOGICA AUTO
# ===========================
desired_temperature = 22  # Default
auto_mode = False         # Default (puoi salvarlo su file se vuoi renderlo persistente)

def check_auto_mode(temp):
    global state_risc, state_cond
    if temp is None:
        print("⚠️ Nessuna temperatura disponibile per AUTO.")
        return

    print("=== CHECK AUTO MODE ===")
    print("AUTO_MODE =", auto_mode)
    print("desired_temperature =", desired_temperature)
    print("temperature_slave =", temp)
    print("=======================")

    if auto_mode:
        if temp < desired_temperature - 0.5:
            if not state_risc:
                if state_cond:
                    state_cond = False
                    rele_cond.value(0)
                    publish_state_cond()
                    print("→ AUTO: spengo aria condizionata")
                state_risc = True
                rele_risc.value(1)
                publish_state_risc()
                print("→ AUTO: accendo riscaldamento")
        elif temp > desired_temperature + 0.5:
            if not state_cond:
                if state_risc:
                    state_risc = False
                    rele_risc.value(0)
                    publish_state_risc()
                    print("→ AUTO: spengo riscaldamento")
                state_cond = True
                rele_cond.value(1)
                publish_state_cond()
                print("→ AUTO: accendo aria condizionata")
        else:
            if state_risc:
                state_risc = False
                rele_risc.value(0)
                publish_state_risc()
                print("→ AUTO: temperatura OK, spengo riscaldamento")
            if state_cond:
                state_cond = False
                rele_cond.value(0)
                publish_state_cond()
                print("→ AUTO: temperatura OK, spengo aria condizionata")

# ===========================
# MQTT CALLBACK
# ===========================
def mqtt_callback(topic, msg):
    global state_risc, state_cond, auto_mode, desired_temperature
    print("MQTT message received:", topic, msg)

    if topic == TOPIC_RISCALDAMENTO_CMD:
        auto_mode = False
        if msg == b"ON":
            if state_cond:
                state_cond = False
                rele_cond.value(0)
                publish_state_cond()
                print("⚠️ Aria spenta per accendere riscaldamento")

            state_risc = True
            rele_risc.value(1)
            print("→ Riscaldamento acceso via MQTT")

        elif msg == b"OFF":
            state_risc = False
            rele_risc.value(0)
            print("→ Riscaldamento spento via MQTT")

        publish_state_risc()

    elif topic == TOPIC_ARIA_CMD:
        auto_mode = False
        if msg == b"ON":
            if state_risc:
                state_risc = False
                rele_risc.value(0)
                publish_state_risc()
                print("⚠️ Riscaldamento spento per accendere aria")

            state_cond = True
            rele_cond.value(1)
            print("→ Aria condizionata accesa via MQTT")

        elif msg == b"OFF":
            state_cond = False
            rele_cond.value(0)
            print("→ Aria condizionata spenta via MQTT")

        publish_state_cond()

    elif topic == b"home/led/auto_mode/command":
        if msg == b"ON":
            auto_mode = True
            print("✅ AUTO MODE attivato")
            temp_now = read_temperature_sensor()
            check_auto_mode(temp_now)
        else:
            auto_mode = False
            print("✅ AUTO MODE disattivato")

    elif topic == b"home/led/desired_temperature/command":
        try:
            desired_temperature = float(msg.decode())
            print(f"✅ Temperatura desiderata impostata a {desired_temperature} °C")
            if auto_mode:
                temp_now = read_temperature_sensor()
                check_auto_mode(temp_now)
        except Exception as e:
            print("⚠️ Errore parsing temperatura desiderata:", e)

    elif topic == TOPIC_TEMPERATURE_STAT:
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
    val = b"ON" if state_risc else b"OFF"
    try:
        client.publish(TOPIC_RISCALDAMENTO_STATE, val, retain=True)
        print("→ Stato riscaldamento pubblicato:", val)
    except Exception as e:
        print("Errore publish stato riscaldamento:", e)

def publish_state_cond():
    val = b"ON" if state_cond else b"OFF"
    try:
        client.publish(TOPIC_ARIA_STATE, val, retain=True)
        print("→ Stato aria condizionata pubblicato:", val)
    except Exception as e:
        print("Errore publish stato aria:", e)

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
    client.subscribe(TOPIC_RISCALDAMENTO_CMD)
    client.subscribe(TOPIC_ARIA_CMD)
    client.subscribe(TOPIC_TEMPERATURE_STAT)
    client.subscribe(b"home/led/auto_mode/command")
    client.subscribe(b"home/led/desired_temperature/command")
    print("✅ MQTT connesso e sottoscritto ai topic.")

# ===========================
# MAIN LOOP
# ===========================
def main():
    connect_wifi()
    connect_mqtt()

    publish_state_risc()
    publish_state_cond()
    print("✅ Stati iniziali pubblicati su MQTT.")

    publish_temperature()

    last_temp_time = time.ticks_ms()
    last_msg_time = time.ticks_ms()

    while True:
        now = time.ticks_ms()

        try:
            client.check_msg()
            last_msg_time = now
        except Exception as e:
            print("MQTT check_msg error:", e)
            time.sleep(1)
            connect_mqtt()
            last_msg_time = now

        if time.ticks_diff(now, last_msg_time) > 30_000:
            print("⚠️ Nessun messaggio MQTT da 30 secondi → riconnetto MQTT...")
            try:
                client.disconnect()
            except:
                pass
            connect_mqtt()
            last_msg_time = now

        if time.ticks_diff(now, last_temp_time) >= 5 * 60 * 1000:
            publish_temperature()
            last_temp_time = now

        time.sleep(0.05)

# Run
main()
