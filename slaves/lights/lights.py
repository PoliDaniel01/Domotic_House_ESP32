from machine import Pin
import time
import network
from umqtt.simple import MQTTClient

# ===========================
# CONFIGURAZIONE
# ===========================
WIFI_SSID = "-----"
WIFI_PASS = "-----"
MQTT_BROKER = "-----"

TOPIC_SOGGIORNO = b"home/led/soggiorno"
TOPIC_CUCINA    = b"home/led/cucina"
TOPIC_CAMERA    = b"home/led/camera"

TOPICS = {
    TOPIC_SOGGIORNO: "soggiorno",
    TOPIC_CUCINA:    "cucina",
    TOPIC_CAMERA:    "camera",
}

# ===========================
# PIN LED E PULSANTI
# ===========================

# LED OUTPUT
led_pins = {
    "soggiorno": Pin(4, Pin.OUT),
    "cucina": Pin(16, Pin.OUT),
    "camera": Pin(17, Pin.OUT)
}

# Spegni tutto all'avvio
for pin in led_pins.values():
    pin.value(0)

# Stato interno
led_states = {
    "soggiorno": False,
    "cucina": False,
    "camera": False,
}

# Pulsanti INPUT (con pull-up)
btn_pins = {
    "soggiorno": Pin(21, Pin.IN, Pin.PULL_UP),
    "cucina":    Pin(22, Pin.IN, Pin.PULL_UP),
    "camera":    Pin(23, Pin.IN, Pin.PULL_UP),
}

# Stato precedente dei pulsanti per debounce
btn_states = {
    name: 1 for name in btn_pins
}

# Timer ultimo cambio
btn_times = {
    name: time.ticks_ms() for name in btn_pins
}

client = None

# ===========================
# PUBBLICA STATO
# ===========================
def publish_state(name):
    if client:
        topic = f"home/led/{name}".encode()
        msg = b"ON" if led_states[name] else b"OFF"
        try:
            client.publish(topic, msg, retain=True)
            print(f"Published {topic}: {msg}")
        except Exception as e:
            print(f"Errore publish MQTT: {e}")

# ===========================
# PUBBLICA TUTTI GLI STATI
# ===========================
def publish_all_states():
    for name in led_states:
        publish_state(name)

# ===========================
# MQTT CALLBACK
# ===========================
def mqtt_callback(topic, msg):
    topic_str = topic.decode()
    msg_str = msg.decode()

    print("MQTT received:", topic_str, msg_str)

    if topic in TOPICS:
        name = TOPICS[topic]
        new_state = msg_str in ["ON", "AUTO_ON"]

        if led_states[name] != new_state:
            led_states[name] = new_state
            led_pins[name].value(1 if new_state else 0)
            publish_state(name)
            print(f"→ Luce {name.upper()} {'accesa' if new_state else 'spenta'}")
        else:
            print(f"Stato {name.upper()} già {msg_str}, nessuna modifica.")

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
    client = MQTTClient("esp32-luci", MQTT_BROKER)
    client.set_callback(mqtt_callback)
    client.connect()
    for topic in TOPICS:
        client.subscribe(topic)
    print("MQTT connesso e sottoscritto a:")
    for topic in TOPICS:
        print("   ", topic)

    # All'avvio pubblica subito lo stato corrente
    publish_all_states()

# ===========================
# MAIN LOOP
# ===========================
def main():
    connect_wifi()
    connect_mqtt()

    while True:
        # Ricezione MQTT
        if client:
            try:
                client.check_msg()
            except Exception as e:
                print("Errore MQTT:", e)

        # Lettura pulsanti
        for name, pin in btn_pins.items():
            current = pin.value()
            if current == 0 and btn_states[name] == 1:
                now = time.ticks_ms()
                if time.ticks_diff(now, btn_times[name]) > 200:  # debounce

                    print(f"Pulsante {name} premuto!")

                    # Toggle stato
                    led_states[name] = not led_states[name]
                    led_pins[name].value(1 if led_states[name] else 0)

                    # Pubblica su MQTT
                    publish_state(name)
                    print(f"→ {name.upper()} {'accesa' if led_states[name] else 'spenta'}")

                    btn_times[name] = now

            btn_states[name] = current

        time.sleep(0.05)

# Run
main()
