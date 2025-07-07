from machine import Pin
import time
import network
from umqtt.simple import MQTTClient

# ===========================
# CONFIGURAZIONE
# ===========================
WIFI_SSID = "----"
WIFI_PASS = "----"
MQTT_BROKER = "----"

TOPIC_RISCALDAMENTO = b"home/led/riscaldamento"
TOPIC_ARIA_COND = b"home/led/aria_condizionata"

# ===========================
# PIN
# ===========================
rele_risc = Pin(10, Pin.OUT)
rele_risc.value(0)

rele_cond = Pin(11, Pin.OUT)
rele_cond.value(0)

btn_risc = Pin(5, Pin.IN, Pin.PULL_UP)
btn_cond = Pin(4, Pin.IN, Pin.PULL_UP)

# Stato pulsanti (debounce)
last_btn_risc = 1
last_btn_cond = 1
last_btn_time = time.ticks_ms()

# Stato luci
state_risc = False
state_cond = False

client = None

# ===========================
# MQTT CALLBACK
# ===========================
def mqtt_callback(topic, msg):
    global state_risc, state_cond

    print("MQTT message received:", topic, msg)

    if topic == TOPIC_RISCALDAMENTO:
        if msg == b"ON":
            # Spegni aria se accendo riscaldamento
            if state_cond:
                state_cond = False
                rele_cond.value(0)
                client.publish(TOPIC_ARIA_COND, b"OFF", retain=True)
                print("⚠️ Aria spenta per accendere riscaldamento")

            state_risc = True
            rele_risc.value(1)
            print("→ Riscaldamento acceso via MQTT")

        elif msg == b"OFF":
            state_risc = False
            rele_risc.value(0)
            print("→ Riscaldamento spento via MQTT")

    elif topic == TOPIC_ARIA_COND:
        if msg == b"ON":
            # Spegni riscaldamento se accendo aria
            if state_risc:
                state_risc = False
                rele_risc.value(0)
                client.publish(TOPIC_RISCALDAMENTO, b"OFF", retain=True)
                print("⚠️ Riscaldamento spento per accendere aria")

            state_cond = True
            rele_cond.value(1)
            print("→ Aria condizionata accesa via MQTT")

        elif msg == b"OFF":
            state_cond = False
            rele_cond.value(0)
            print("→ Aria condizionata spenta via MQTT")

# ===========================
# WIFI
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
# MQTT
# ===========================
def connect_mqtt():
    global client
    client = MQTTClient("esp32-slave-clima", MQTT_BROKER)
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(TOPIC_RISCALDAMENTO)
    client.subscribe(TOPIC_ARIA_COND)
    print("✅ MQTT connesso e sottoscritto ai topic:")
    print("   ", TOPIC_RISCALDAMENTO)
    print("   ", TOPIC_ARIA_COND)

# ===========================
# MAIN LOOP
# ===========================
def main():
    global last_btn_risc, last_btn_cond, last_btn_time
    global state_risc, state_cond

    connect_wifi()
    connect_mqtt()

    while True:
        # Check messaggi MQTT
        try:
            client.check_msg()
        except Exception as e:
            print("MQTT check_msg error:", e)
            time.sleep(1)
            connect_mqtt()

        # Lettura pulsanti (debounce)
        now = time.ticks_ms()

        # Pulsante riscaldamento
        btn_val = btn_risc.value()
        if btn_val == 0 and last_btn_risc == 1:
            if time.ticks_diff(now, last_btn_time) > 200:
                if not state_risc:
                    # Accendo riscaldamento → spengo aria
                    if state_cond:
                        state_cond = False
                        rele_cond.value(0)
                        client.publish(TOPIC_ARIA_COND, b"OFF", retain=True)
                        print("⚠️ Aria spenta per accendere riscaldamento")

                    state_risc = True
                    rele_risc.value(1)
                    client.publish(TOPIC_RISCALDAMENTO, b"ON", retain=True)
                    print("→ Riscaldamento acceso da pulsante")
                else:
                    # Spengo riscaldamento
                    state_risc = False
                    rele_risc.value(0)
                    client.publish(TOPIC_RISCALDAMENTO, b"OFF", retain=True)
                    print("→ Riscaldamento spento da pulsante")
                last_btn_time = now
        last_btn_risc = btn_val

        # Pulsante aria condizionata
        btn_val = btn_cond.value()
        if btn_val == 0 and last_btn_cond == 1:
            if time.ticks_diff(now, last_btn_time) > 200:
                if not state_cond:
                    # Accendo aria → spengo riscaldamento
                    if state_risc:
                        state_risc = False
                        rele_risc.value(0)
                        client.publish(TOPIC_RISCALDAMENTO, b"OFF", retain=True)
                        print("⚠️ Riscaldamento spento per accendere aria")

                    state_cond = True
                    rele_cond.value(1)
                    client.publish(TOPIC_ARIA_COND, b"ON", retain=True)
                    print("→ Aria accesa da pulsante")
                else:
                    # Spengo aria
                    state_cond = False
                    rele_cond.value(0)
                    client.publish(TOPIC_ARIA_COND, b"OFF", retain=True)
                    print("→ Aria spenta da pulsante")
                last_btn_time = now
        last_btn_cond = btn_val

        time.sleep(0.05)

# Run
main()
