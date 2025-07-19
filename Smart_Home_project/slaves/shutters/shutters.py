from machine import Pin
import network
import time
from umqtt.simple import MQTTClient
import machine

# === CONFIGURAZIONE ===
WIFI_SSID = ""
WIFI_PASS = ""
MQTT_BROKER = ""  # Consigliato: usa IP se possibile
MQTT_CLIENT_ID = "esp32-tapparella"
TOPIC_CMD = b"home/actuator/tapparella/set"
TOPIC_STATE = b"home/actuator/tapparella/state"

# === PIN ===
BTN_UP = Pin(9, Pin.IN, Pin.PULL_UP)
BTN_DOWN = Pin(8, Pin.IN, Pin.PULL_UP)
MOTOR_UP = Pin(5, Pin.OUT)
MOTOR_DOWN = Pin(4, Pin.OUT)

# === STATO ===
shutter_state = "idle"
mqtt_client = None

# === CONNESSIONE WIFI ===
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    print("🔌 Connessione Wi-Fi...")
    while not wlan.isconnected():
        print(".", end="")
        time.sleep(0.5)
    print("\n✅ Wi-Fi connesso:", wlan.ifconfig())

# === PUBBLICA STATO ===
def publish_state():
    if mqtt_client:
        try:
            mqtt_client.publish(TOPIC_STATE, shutter_state)
            print(f"→ Stato tapparella MQTT: {shutter_state}")
        except Exception as e:
            print("⚠️ Errore pubblicazione MQTT:", e)

# === MUOVI TAPPARELLE ===
def move_shutter(direction):
    global shutter_state

    MOTOR_UP.off()
    MOTOR_DOWN.off()

    if direction == "up" and shutter_state != "open":
        print("🔼 Apro le tapparelle...")
        MOTOR_UP.on()
        time.sleep(2)
        MOTOR_UP.off()
        shutter_state = "open"
    elif direction == "down" and shutter_state != "closed":
        print("🔽 Chiudo le tapparelle...")
        MOTOR_DOWN.on()
        time.sleep(2)
        MOTOR_DOWN.off()
        shutter_state = "closed"
    elif direction == "stop":
        print("⏹️ Stop tapparelle")
        shutter_state = "idle"

    publish_state()

# === CALLBACK MQTT ===
def mqtt_callback(topic, msg):
    print(f"📥 MQTT: {topic} = {msg}")
    if topic == TOPIC_CMD:
        direction = msg.decode().lower()
        if direction in ["up", "down", "stop"]:
            move_shutter(direction)

# === CONNETTI MQTT ===
def connect_mqtt():
    global mqtt_client
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
    mqtt_client.set_callback(mqtt_callback)
    mqtt_client.connect()
    mqtt_client.subscribe(TOPIC_CMD)
    print("📡 MQTT connesso e sottoscritto")

# === MAIN LOOP ===
def main():
    global mqtt_client
    connect_wifi()
    connect_mqtt()

    MOTOR_UP.off()
    MOTOR_DOWN.off()

    last_up = 1
    last_down = 1

    while True:
        try:
            mqtt_client.check_msg()
        except OSError as e:
            print("⚠️ Errore MQTT. Riconnessione in corso...")
            try:
                connect_mqtt()
            except Exception as e:
                print("❌ Fallita riconnessione MQTT:", e)
                time.sleep(5)

        # Controllo pulsanti fisici
        up = BTN_UP.value()
        down = BTN_DOWN.value()

        if up == 0 and last_up == 1:
            print("🔘 Pulsante SU premuto")
            move_shutter("up")

        if down == 0 and last_down == 1:
            print("🔘 Pulsante GIÙ premuto")
            move_shutter("down")

        last_up = up
        last_down = down

        time.sleep(0.1)

# === AVVIO ===
if __name__ == "__main__":
    main()
