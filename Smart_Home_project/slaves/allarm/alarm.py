from machine import Pin
from time import sleep_ms
import network
from umqtt.simple import MQTTClient

# === CONFIG ===
WIFI_SSID = ""
WIFI_PASS = ""
MQTT_BROKER = ""  # Sostituibile con IP

MQTT_CLIENT_ID = "esp32-allarme"
TOPIC_STATE = b"home/sensor/alarm/state"
TOPIC_CMD = b"home/sensor/alarm/set"

# === PIN ===
button1 = Pin(1, Pin.IN, Pin.PULL_UP)
button2 = Pin(2, Pin.IN, Pin.PULL_UP)
reset_button = Pin(3, Pin.IN, Pin.PULL_UP)
led = Pin(4, Pin.OUT)
led.value(0)

# === VARIABILI ===
alarm_triggered = False
triggered_by_button = False  # 💡 lampeggia solo se attivato da pulsante
last_alarm_command = "off"
led_state = False
mqtt_client = None

# === CONNESSIONE WIFI ===
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    print("🔌 Connessione Wi-Fi...")
    while not wlan.isconnected():
        print(".", end="")
        sleep_ms(500)
    print("\n✅ Wi-Fi connesso:", wlan.ifconfig())

# === PUBBLICA STATO ===
def publish_state(state):
    if mqtt_client:
        try:
            mqtt_client.publish(TOPIC_STATE, state)
            print(f"📤 Stato pubblicato: {state}")
        except Exception as e:
            print("⚠️ Errore pubblicazione MQTT:", e)

# === CALLBACK MQTT ===
def mqtt_callback(topic, msg):
    global alarm_triggered, last_alarm_command, triggered_by_button
    topic_str = topic.decode()
    msg_str = msg.decode().strip().lower().replace('"', '').replace("'", "")
    print(f"📥 MQTT ricevuto: {topic_str} = {repr(msg_str)}")

    if topic_str == "home/sensor/alarm/set":
        last_alarm_command = msg_str
        print(f"🔄 Stato master aggiornato: {msg_str}")
        if msg_str == "off":
            if alarm_triggered:
                alarm_triggered = False
                triggered_by_button = False
                led.value(0)
                publish_state(b"disarmed")
        elif msg_str == "on":
            print("✅ Allarme autorizzato dal master (ma non attivato)")

# === CONNESSIONE MQTT ===
def connect_mqtt():
    global mqtt_client
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
    mqtt_client.set_callback(mqtt_callback)
    mqtt_client.connect()
    mqtt_client.subscribe(TOPIC_CMD)
    print("📡 MQTT connesso e sottoscritto")

# === MAIN LOOP ===
try:
    connect_wifi()
    connect_mqtt()

    loop_counter = 0

    while True:
        try:
            mqtt_client.check_msg()
        except OSError as e:
            print("⚠️ Errore MQTT, provo a riconnettermi...")
            try:
                mqtt_client.connect()
                mqtt_client.subscribe(TOPIC_CMD)
                print("🔁 Riconnesso a MQTT")
            except Exception as e:
                print("❌ Errore riconnessione MQTT:", e)
                sleep_ms(5000)

        # Debug ogni 2 secondi
        loop_counter += 1
        if loop_counter >= 20:
            print(f"🔍 Stato master: {last_alarm_command} | Triggered: {alarm_triggered}")
            loop_counter = 0

        # RESET
        if reset_button.value() == 0 and alarm_triggered:
            print("🔁 RESET premuto: allarme disattivato")
            alarm_triggered = False
            triggered_by_button = False
            led.value(0)
            publish_state(b"disarmed")
            sleep_ms(300)

        # Pulsanti fisici (se autorizzato)
        if last_alarm_command == "on":
            if not alarm_triggered and (button1.value() == 0 or button2.value() == 0):
                print("🚨 Allarme attivato da pulsante")
                alarm_triggered = True
                triggered_by_button = True
                led.value(1)
                publish_state(b"triggered")
                sleep_ms(300)
        else:
            if button1.value() == 0 or button2.value() == 0:
                print("🚫 Pulsante ignorato: allarme disabilitato dal master")

        # LED lampeggia solo se attivato da pulsante
        if alarm_triggered and triggered_by_button:
            led_state = not led_state
            led.value(led_state)
            sleep_ms(500)
        else:
            led.value(0)
            sleep_ms(50)

except KeyboardInterrupt:
    led.value(0)
    if mqtt_client:
        mqtt_client.disconnect()
