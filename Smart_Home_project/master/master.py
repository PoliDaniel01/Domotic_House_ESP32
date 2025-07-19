from machine import Pin, SPI
import time
import network
from umqtt.simple import MQTTClient
from st7789 import ST7789, color565
import vga1_8x8 as font
from xpt2046 import Touch
import json
import uasyncio as asyncio
from microdot_asyncio import Microdot, Response, redirect

# ==============================
# INIT DISPLAY
# ==============================

spi_disp = SPI(1, baudrate=10000000, sck=Pin(14), mosi=Pin(13))
dc = Pin(2, Pin.OUT)
cs = Pin(15, Pin.OUT)
rst = Pin(33, Pin.OUT) # WARNING: This pin (GPIO33) is also used for cs_touch. This will cause a hardware conflict.
bl = Pin(21, Pin.OUT)

bl.value(1) # Turn on backlight

cs.value(1) # De-assert CS for display
rst.value(0) # Reset display
time.sleep_ms(200)
rst.value(1) # Release reset
time.sleep_ms(200)

def write_cmd(cmd):
    dc.value(0) # Command mode
    cs.value(0) # Assert CS
    spi_disp.write(bytearray([cmd]))
    cs.value(1) # De-assert CS

def write_data(data):
    dc.value(1) # Data mode
    cs.value(0) # Assert CS
    spi_disp.write(bytearray([data]))
    cs.value(1) # De-assert CS

# Basic ST7789 initialization sequence
write_cmd(0x01) # Software Reset
time.sleep_ms(150)
write_cmd(0x11) # Sleep Out
time.sleep_ms(150)
write_cmd(0x3A) # Interface Pixel Format
write_data(0x55) # 16-bit/pixel
write_cmd(0x29) # Display On
time.sleep_ms(50)

print("Display inizializzato via init RAW!")

# Initialize ST7789 display driver
display = ST7789(
    spi_disp,
    240, # Width
    320, # Height
    dc=dc,
    reset=rst,
    cs=cs,
    rotation=1 # Rotate display by 90 degrees
)

# Initialize SPI for touch controller
spi_touch = SPI(2, baudrate=1000000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
cs_touch = Pin(33, Pin.OUT) # WARNING: This pin (GPIO33) is also used for rst. This will cause a hardware conflict.
touch = Touch(spi_touch, cs_touch)

# ===========================
# CONFIGURATION
# ===========================
WIFI_SSID = "TIM-65236427"
WIFI_PASS = "TORONTO2019"
MQTT_BROKER = "MacBookAirProMax-Air-di-Matteo-152.local" # Local MQTT broker address

STANDBY_TIMEOUT = 60 # Seconds before display goes into standby
STATE_FILE = "states.json" # File to store persistent states

current_temperature = None

client = None # MQTT client instance
published_states = {} # Dictionary to track published MQTT states
temperature_slave = None # Current temperature from slave device
desired_temperature = 22 # Desired temperature for auto mode

need_auto_logic = False # Flag for auto logic re-evaluation (not currently used)
pending_mqtt_publish = [] # List of pending MQTT messages (not currently used)

tapparella_state = None # State of the roller shutter (up/down)
tapparella_last_change = 0 # Timestamp of last roller shutter change

# ===========================
# STATES FILE MANAGEMENT
# ===========================
def load_states():
    global desired_temperature
    try:
        with open(STATE_FILE, "r") as f:
            states = json.load(f)
            desired_temperature = states.get("DES_TEMP", 22) # Load desired temperature
            # Remove old temporary keys if they exist in the saved state
            for k in ["TEMP", "HUMIDITY", "DES_TEMP"]:
                if k in states:
                    del states[k]
            print("✅ Stati caricati da states.json")
            return states
    except Exception as e:
        print(f"⚠️ Nessun file states.json o errore di lettura: {e}. Uso default.")
        return {
            "soggiorno": False,
            "cucina": False,
            "camera": False,
            "aria_condizionata": False,
            "riscaldamento": False,
            "allarme": False,
            "auto_mode": False
        }

def save_states():
    try:
        # Create a clean dictionary to save, excluding temporary display states
        clean_states = {
            k: v for k, v in led_states.items()
            if k not in ["TEMP", "HUMIDITY"]
        }
        clean_states["DES_TEMP"] = desired_temperature # Add desired temperature to saved states
        with open(STATE_FILE, "w") as f:
            json.dump(clean_states, f)
        print("✅ Stati salvati.")
    except Exception as e:
        print(f"⚠️ Errore salvataggio states.json: {e}")

led_states = load_states() # Load initial states on startup

# ===========================
# UI PAGE DEFINITIONS
# ===========================
PAGE_MAIN = "main"
PAGE_LUCI = "luci"
PAGE_RISCALDAMENTO = "riscaldamento"
PAGE_AUTO_SETTINGS = "auto_settings"
PAGE_TAPPARELLE = "tapparelle"
PAGE_ALLARME = "allarme"

current_page = PAGE_MAIN # Initial page
last_touch_time = 0 # Timestamp of last touch event
standby = False # Standby mode flag

# ===========================
# DRAWING FUNCTIONS
# ===========================
def draw_page():
    display.fill(color565(0,0,0)) # Clear display with black background

    # Display current temperature if available
    if temperature_slave is not None:
        display.text(
            font,
            "T:{:.1f}C".format(temperature_slave),
            240 - 70, # X position (right aligned)
            0, # Y position (top)
            color565(255,255,255), # Text color (white)
            color565(0,0,0) # Background color (black)
        )
    
    # Draw content based on current page
    if current_page == PAGE_MAIN:
        draw_main_page()
    elif current_page == PAGE_LUCI:
        draw_luci_page()
    elif current_page == PAGE_RISCALDAMENTO:
        draw_riscaldamento_page()
    elif current_page == PAGE_AUTO_SETTINGS:
        draw_auto_settings_page()
    elif current_page == PAGE_TAPPARELLE:
        draw_tapparelle_page()
    elif current_page == PAGE_ALLARME:
        draw_allarme_page()

def draw_main_page():
    display.fill(0)  # Pulisce lo schermo

    # Titolo
    display.text(font, "MENU PRINCIPALE", 40, 10, color565(255, 255, 255), color565(0, 0, 0))

    # Mostra temperatura in alto a destra
    if current_temperature is not None:
        temp_str = "{:.1f}°C".format(current_temperature)
    else:
        temp_str = "--.-°C"
    display.text(font, temp_str, 260, 10, color565(255, 255, 255))
    buttons = [
        ("LUCI", 20, 40),
        ("RISCALDAMENTO", 20, 90),
        ("TAPPARELLE", 20, 140),
        ("ALLARME", 20, 190)
    ]
    for label, x, y in buttons:
        display.fill_rect(x, y, 200, 40, color565(50, 50, 50))  # Background
        display.rect(x, y, 200, 40, color565(255, 255, 255))    # Contorno
        display.text(font, label, x + 10, y + 15, color565(255, 255, 255), color565(50, 50, 50))  # Testo
def draw_luci_page():
    display.text(font, "LUCI CASA", 60, 5, color565(255,255,255), color565(0,0,0))
    buttons = {
        "soggiorno": (20, 40, 100, 40),
        "cucina": (20, 100, 100, 40),
        "camera": (20, 160, 100, 40),
    }
    for name, (x, y, w, h) in buttons.items():
        stato_color = color565(0,255,0) if led_states[name] else color565(255,0,0) # Green for ON, Red for OFF
        display.fill_rect(x, y, w, h, color565(50,50,50)) # Button background
        display.rect(x, y, w, h, color565(255,255,255)) # Button border
        display.text(font, name.upper(), x + 5, y + 15, color565(255,255,255), color565(50,50,50)) # Button text
        display.fill_rect(x + w + 10, y + 10, 20, 20, stato_color) # Status indicator (colored square)

    # "Turn All Off" button
    display.fill_rect(20, 200, 120, 40, color565(255,0,0)) # Red background
    display.rect(20, 200, 120, 40, color565(255,255,255))
    display.text(font, "SPEGNI TUTTO", 25, 215, color565(255,255,255), color565(255,0,0))

    # "BACK" button
    display.fill_rect(160, 200, 60, 40, color565(100,100,100)) # Grey background
    display.rect(160, 200, 60, 40, color565(255,255,255))
    display.text(font, "BACK", 165, 215, color565(255,255,255), color565(100,100,100))

def draw_riscaldamento_page():
    display.text(font, "RISCALDAMENTO", 40, 5, color565(255,255,255), color565(0,0,0))

    # "AUTO" button to go to auto settings
    display.fill_rect(20, 40, 180, 40, color565(50,50,50))
    display.rect(20, 40, 180, 40, color565(255,255,255))
    display.text(font, "AUTO", 60, 55, color565(255,255,255), color565(50,50,50))

    buttons = {
        "aria_condizionata": (20, 90, 180, 40),
        "riscaldamento": (20, 140, 180, 40),
    }
    for name, (x, y, w, h) in buttons.items():
        stato_color = color565(0,255,0) if led_states[name] else color565(255,0,0) # Green for ON, Red for OFF
        display.fill_rect(x, y, w, h, color565(50,50,50)) # Button background
        display.rect(x, y, w, h, color565(255,255,255)) # Button border
        display.text(font, name.upper(), x + 5, y + 15, color565(255,255,255), color565(50,50,50)) # Button text
        display.fill_rect(x + w + 10, y + 10, 20, 20, stato_color) # Status indicator

    # "BACK" button
    display.fill_rect(20, 200, 100, 40, color565(100,100,100))
    display.rect(20, 200, 100, 40, color565(255,255,255))
    display.text(font, "BACK", 30, 215, color565(255,255,255), color565(100,100,100))

def draw_auto_settings_page():
    display.text(font, "AUTO SETTINGS", 40, 5, color565(255,255,255), color565(0,0,0))

    # Auto Mode Toggle button
    auto_on = led_states.get("auto_mode", False)
    auto_color = color565(0,255,0) if auto_on else color565(255,0,0)
    display.fill_rect(20, 50, 180, 40, auto_color)
    display.rect(20, 50, 180, 40, color565(255,255,255))
    display.text(font, "AUTO MODE", 30, 65, color565(0,0,0), auto_color)

    # Desired Temperature display
    display.text(font, f"SET: {desired_temperature} C", 60, 110, color565(255,255,255), color565(0,0,0))
    
    # Temperature Increase button
    display.fill_rect(30, 150, 50, 40, color565(50,50,50))
    display.text(font, "+", 45, 165, color565(255,255,255), color565(50,50,50))
    
    # Temperature Decrease button
    display.fill_rect(140, 150, 50, 40, color565(50,50,50))
    display.text(font, "-", 155, 165, color565(255,255,255), color565(50,50,50))

    # "BACK" button
    display.fill_rect(20, 200, 100, 40, color565(100,100,100))
    display.rect(20, 200, 100, 40, color565(255,255,255))
    display.text(font, "BACK", 30, 215, color565(255,255,255), color565(100,100,100))

def draw_tapparelle_page():
    global tapparella_state, tapparella_last_change

    display.text(font, "TAPPARELLE", 60, 5, color565(255,255,255), color565(0,0,0))

    now = time.time()
    # Reset tapparella_state after 2 seconds to show momentary press feedback
    if tapparella_state and (now - tapparella_last_change > 2):
        tapparella_state = None
        # Redraw to clear the momentary highlight
        draw_page() # This might cause flicker, better to redraw only the button area

    # Dynamic colors based on momentary state
    su_color = color565(0,255,0) if tapparella_state == "up" else color565(50,50,50) # Green for active, Grey otherwise
    giu_color = color565(0,255,0) if tapparella_state == "down" else color565(50,50,50) # Green for active, Grey otherwise

    # "UP" button
    display.fill_rect(40, 60, 160, 40, su_color)
    display.rect(40, 60, 160, 40, color565(255, 255, 255))
    display.text(font, "SU", 110, 75, color565(255, 255, 255), su_color)

    # "DOWN" button
    display.fill_rect(40, 120, 160, 40, giu_color)
    display.rect(40, 120, 160, 40, color565(255, 255, 255))
    display.text(font, "GIU", 105, 135, color565(255, 255, 255), giu_color)

    # "BACK" button
    display.fill_rect(20, 200, 100, 40, color565(100,100,100))
    display.rect(20, 200, 100, 40, color565(255,255,255))
    display.text(font, "BACK", 30, 215, color565(255,255,255), color565(100,100,100))

def draw_allarme_page():
    display.text(font, "ALLARME", 80, 5, color565(255,255,255), color565(0,0,0))
    stato_color = color565(0,255,0) if led_states["allarme"] else color565(255,0,0) # Green for ON, Red for OFF
    stato_txt = "DISATTIVA" if led_states["allarme"] else "ATTIVA" # Text changes based on state

    display.fill_rect(40, 80, 160, 40, stato_color)
    display.rect(40, 80, 160, 40, color565(255,255,255))
    display.text(font, stato_txt, 60, 95, color565(0,0,0), stato_color)

    # "BACK" button
    display.fill_rect(20, 200, 100, 40, color565(100,100,100))
    display.rect(20, 200, 100, 40, color565(255,255,255))
    display.text(font, "BACK", 30, 215, color565(255,255,255), color565(100,100,100))

# ===========================
# Function to modify device state
# This function is duplicated in the original code, one here and one in the webserver section.
# It should be unified.
# ===========================
def set_device_state(name, onoff):
    print(f"[STATE] {name} → {'ON' if onoff else 'OFF'} (via Touch/Web)")
    led_states[name] = onoff

    # Disattiva modalità automatica se si agisce manualmente sul clima
    if name in ["aria_condizionata", "riscaldamento"]:
        led_states["auto_mode"] = False

    published_states[name] = None  # Forza pubblicazione su MQTT
    publish_led_state(name)

    # Pubblica anche lo stato dell'allarme se cambia
    if name == "allarme":
        topic = b"home/led/allarme/state"
        msg = b"ON" if onoff else b"OFF"
        mqtt_callback(topic, msg)  # Aggiorna localmente
        try:
            if client:
                client.publish(topic, msg, retain=True)
                print(f"MQTT: allarme → {msg.decode()} inviato")
        except Exception as e:
            print("MQTT publish error (allarme):", e)

    save_states()
    draw_page()
# ===========================
# TOUCH HANDLING
# ===========================
def check_touch():
    global current_page, last_touch_time, standby, desired_temperature, tapparella_state, tapparella_last_change

    pos = touch.get_touch()
    if pos:
        last_touch_time = time.time()

        if standby:
            standby = False
            bl.value(1) # Turn backlight on
            draw_page() # Redraw current page
            return

        x, y = pos
        # Touch coordinates are often swapped or rotated depending on display/touch orientation
        # The original code swaps them, so we keep that.
        x, y = y, x

        # Main Page Navigation
        if current_page == PAGE_MAIN:
            if 20 <= x <= 220 and 40 <= y <= 80: # LUCI
                current_page = PAGE_LUCI
            elif 20 <= x <= 220 and 90 <= y <= 130: # RISCALDAMENTO
                current_page = PAGE_RISCALDAMENTO
            elif 20 <= x <= 220 and 140 <= y <= 180: # TAPPARELLE
                current_page = PAGE_TAPPARELLE
            elif 20 <= x <= 220 and 190 <= y <= 230: # ALLARME
                current_page = PAGE_ALLARME
            draw_page()
            return

        # Luci Page Interactions
        if current_page == PAGE_LUCI:
            if 20 <= x <= 140 and 200 <= y <= 240: # SPEGNI TUTTO
                for name in ["soggiorno", "cucina", "camera"]:
                    set_device_state(name, False)
                return
            if 160 <= x <= 220 and 200 <= y <= 240: # BACK
                current_page = PAGE_MAIN
                draw_page()
                return
            buttons = {
                "soggiorno": (20, 40, 100, 40),
                "cucina": (20, 100, 100, 40),
                "camera": (20, 160, 100, 40),
            }
            for name, (bx, by, bw, bh) in buttons.items():
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    set_device_state(name, not led_states[name])
                    return

        # Riscaldamento Page Interactions
        if current_page == PAGE_RISCALDAMENTO:
            if 20 <= x <= 200 and 40 <= y <= 80: # AUTO (navigate to auto settings)
                current_page = PAGE_AUTO_SETTINGS
                draw_page()
                return

            if 20 <= x <= 120 and 200 <= y <= 240: # BACK
                current_page = PAGE_MAIN
                draw_page()
                return

            buttons = {
                "aria_condizionata": (20, 90, 180, 40),
                "riscaldamento": (20, 140, 180, 40),
            }
            for name, (bx, by, bw, bh) in buttons.items():
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    # Logic to prevent both AC and Heating from being ON simultaneously
                    if name == "aria_condizionata" and led_states["riscaldamento"]:
                        set_device_state("riscaldamento", False)
                    if name == "riscaldamento" and led_states["aria_condizionata"]:
                        set_device_state("aria_condizionata", False)
                    set_device_state(name, not led_states[name])
                    return

        # Auto Settings Page Interactions
        if current_page == PAGE_AUTO_SETTINGS:
            if 20 <= x <= 200 and 50 <= y <= 90: # TOGGLE AUTO MODE
                led_states["auto_mode"] = not led_states.get("auto_mode", False)
                save_states()
                evaluate_auto_logic() # Re-evaluate auto logic immediately
                draw_page()
                return

            if 30 <= x <= 80 and 150 <= y <= 190: # TEMP UP
                desired_temperature = min(desired_temperature + 1, 26) # Max temp 26
                save_states()
                if led_states["auto_mode"]:
                    evaluate_auto_logic()
                draw_page()
                return

            if 140 <= x <= 190 and 150 <= y <= 190: # TEMP DOWN
                desired_temperature = max(desired_temperature - 1, 18) # Min temp 18
                save_states()
                if led_states["auto_mode"]:
                    evaluate_auto_logic()
                draw_page()
                return

            if 20 <= x <= 120 and 200 <= y <= 240: # BACK
                current_page = PAGE_RISCALDAMENTO
                draw_page()
                return

        # Tapparelle Page Interactions
        if current_page == PAGE_TAPPARELLE:
            if 40 <= x <= 200 and 60 <= y <= 100: # SU (UP)
                client.publish("home/actuator/tapparella/set", "up")
                tapparella_state = "up" # Set momentary state for visual feedback
                tapparella_last_change = time.time()
                print("MQTT: tapparella → SU")
                draw_page() # Redraw to show momentary state
                return

            if 40 <= x <= 200 and 120 <= y <= 160: # GIU (DOWN)
                client.publish("home/actuator/tapparella/set", "down")
                tapparella_state = "down" # Set momentary state for visual feedback
                tapparella_last_change = time.time()
                print("MQTT: tapparella → GIU")
                draw_page() # Redraw to show momentary state
                return

            if 20 <= x <= 120 and 200 <= y <= 240: # BACK
                current_page = PAGE_MAIN
                draw_page()
                return

        # Allarme Page Interactions
        if current_page == PAGE_ALLARME:
            if 40 <= x <= 200 and 80 <= y <= 120: # TOGGLE ALLARME
                led_states["allarme"] = not led_states["allarme"]
                mqtt_callback( # Simulate MQTT callback for immediate UI update
                    b"home/led/allarme/state",
                    b"ON" if led_states["allarme"] else b"OFF"
                )
                save_states()
                draw_page()
                return
            if 20 <= x <= 120 and 200 <= y <= 240: # BACK
                current_page = PAGE_MAIN
                draw_page()
                return

# ===========================
# MQTT FUNCTIONS
# ===========================
def publish_led_state(name):
    global published_states
    if client:
        topic = f"home/led/{name}/command"
        value = b"ON" if led_states[name] else b"OFF"
        # Only publish if the state has changed from the last published state
        if published_states.get(name) != value:
            try:
                client.publish(topic, value, retain=True) # Publish with retain flag
                published_states[name] = value # Update last published state
                print(f"→ MQTT invio {topic} = {value}")
            except Exception as e:
                print("MQTT publish error:", e)
        else:
            print(f"→ MQTT state for {name} unchanged, skipping publish.")


def publish_all_states():
    # Publish initial states of all controlled devices
    for key in led_states.keys():
        # Exclude 'auto_mode' from direct publishing commands as it's a local setting
        if key not in ["auto_mode"]:
            publish_led_state(key)
def mqtt_callback(topic, msg):
    global current_temperature, desired_temperature
    topic_str = topic.decode()
    msg_str = msg.decode().strip().lower().replace('"', '').replace("'", "")
    print(f"📨 MQTT ricevuto: {topic_str} = {msg_str}")

    updated = False

    if topic_str.endswith("/state"):
        key = topic_str.split("/")[-2]
        if key in led_states:
            led_states[key] = (msg_str == "on")
            save_states()
            updated = True

            # ✅ SOLO INVIA COMANDO, NON ATTIVA NULLA
            if key == "allarme":
                stato = b'on' if led_states["allarme"] else b'off'
                print(f"↪️ Invio comando allarme a slave: {stato}")
                client.publish("home/sensor/alarm/set", stato)
    elif topic_str == "home/status/temperature":
        try:
            current_temperature = float(msg_str)
            global temperature_slave
            temperature_slave = current_temperature
            updated = True
            if led_states.get("auto_mode", False):
                evaluate_auto_logic()
        except Exception as e:
            print("⚠️ Errore parsing temperatura:", e)

    elif topic_str == "home/auto_mode/command":
        led_states["auto_mode"] = (msg_str == "on")
        updated = True
        save_states()
        if led_states["auto_mode"]:
            evaluate_auto_logic()

    elif topic_str == "home/desired_temperature/command":
        try:
            desired_temperature = float(msg_str)
            updated = True
            save_states()
            if led_states.get("auto_mode", False):
                evaluate_auto_logic()
        except Exception as e:
            print("⚠️ Errore parsing temperatura desiderata:", e)

    elif topic_str == "home/sensor/alarm/set":
        # Sincronizza stato allarme da comando web/master
        led_states["allarme"] = (msg_str == "on")
        print("🔁 Stato allarme aggiornato da comando master →", led_states["allarme"])
        save_states()
        updated = True

    elif topic_str == "home/sensor/alarm/state":
        # Riceve stato dallo slave (triggered/disarmed)
        if msg_str == "triggered":
            led_states["allarme"] = True
        elif msg_str == "disarmed":
            led_states["allarme"] = False
        print("🔁 Stato allarme aggiornato da slave →", led_states["allarme"])
        save_states()
        updated = True

    if updated:
        draw_page()
# ===========================
def evaluate_auto_logic():
    if not led_states.get("auto_mode", False):
        print("→ Auto mode is OFF, skipping auto logic.")
        return

    if temperature_slave is None:
        print("→ Nessuna temperatura letta, skip logica auto.")
        return

    print(f"→ Eseguo logica AUTO. Temp slaave={temperature_slave:.1f} °C, target={desired_temperature:.1f} °C")
    
    # Turn on heating if temperature is too low
    if temperature_slave < desired_temperature - 0.5:
        if not led_states["riscaldamento"]:
            set_device_state("riscaldamento", True)
        if led_states["aria_condizionata"]: # Ensure AC is off if heating is on
            set_device_state("aria_condizionata", False)
    # Turn on AC if temperature is too high
    elif temperature_slave > desired_temperature + 0.5:
        if not led_states["aria_condizionata"]:
            set_device_state("aria_condizionata", True)
        if led_states["riscaldamento"]: # Ensure heating is off if AC is on
            set_device_state("riscaldamento", False)
    # Turn off both if temperature is within desired range
    else:
        if led_states["riscaldamento"]:
            set_device_state("riscaldamento", False)
        if led_states["aria_condizionata"]:
            set_device_state("aria_condizionata", False)

# ===========================
# WIFI + MQTT CONNECTION FUNCTIONS
# ===========================


def connect_wifi():
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
        time.sleep(1)
    sta.active(False)
    time.sleep(1)
    sta.active(True)
    sta.connect(WIFI_SSID, WIFI_PASS)
    timeout = time.time() + 15  # timeout di 15 secondi
    while not sta.isconnected():
        if time.time() > timeout:
            raise RuntimeError("Connessione Wi-Fi non riuscita")
        time.sleep(0.5)
    print("WiFi connected:", sta.ifconfig())
    
def connect_mqtt():
    global client
    try:
        client = MQTTClient("esp32-master-display", MQTT_BROKER)
        client.set_callback(mqtt_callback)
        client.connect()

        # Sottoscrizione a tutti i topic rilevanti
        client.subscribe(b"home/led/#")
        client.subscribe(b"home/riscaldamento/state")
        client.subscribe(b"home/aria_condizionata/state")
        client.subscribe(b"home/status/temperature")
        client.subscribe(b"home/sensor/alarm/state")  # ✅ Stato allarme letto dallo slave
        client.subscribe(b"home/auto_mode/command")
        client.subscribe(b"home/desired_temperature/command")
        
        print("✅ MQTT connesso e sottoscritto a tutti i topic.")
    except Exception as e:
        print("❌ Errore connessione MQTT:", e)
        client = None

# ===========================
# WEBSERVER (Microdot)
# ===========================
app = Microdot()

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="5">
    <title>ESP32 Smart Home</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin: 0; background: #f5f6fa; font-family: Arial, sans-serif; color: #2f3640; }
        header { background: #0984e3; padding: 20px; text-align: center; color: white; font-size: 24px; }
        .container { padding: 20px; max-width: 600px; margin: auto; }
        .card { background: white; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
        .card h3 { margin-top: 0; }
        .status { font-weight: bold; margin: 10px 0; }
        .btn { display: inline-block; padding: 10px 20px; text-decoration: none; color: white; border-radius: 4px; margin-right: 10px; font-size: 14px;}
        .on { background: #00b894; } /* Green */
        .off { background: #d63031; } /* Red */
        hr { margin: 15px 0; border: none; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <header>ESP32 Smart Home</header>
    <div class="container">
        <div class="card">
            <h3>Clima</h3>
            <p>Temperatura Slave: <span class="status">{{TEMP}} °C</span></p>
            <p>Temp. desiderata: <span class="status">{{DES_TEMP}} °C</span></p>
            <p>Modalità AUTO: <span class="status">{{AUTO_MODE}}</span></p>
            <a href="/toggle_auto" class="btn {{AUTO_MODE_CLASS}}">Toggle AUTO</a>
            <hr>
            <a href="/temp_up" class="btn on">+1 °C</a>
            <a href="/temp_down" class="btn off">-1 °C</a>
        </div>
        {{LIGHTS}}
        <div class="card">
            <h3>Riscaldamento</h3>
            <p>Aria Condizionata: <span class="status">{{ARIA_STATE}}</span></p>
            <a href="/update?id=aria_condizionata&state=ON" class="btn on">Accendi</a>
            <a href="/update?id=aria_condizionata&state=OFF" class="btn off">Spegni</a>
            <hr>
            <p>Riscaldamento: <span class="status">{{RISC_STATE}}</span></p>
            <a href="/update?id=riscaldamento&state=ON" class="btn on">Accendi</a>
            <a href="/update?id=riscaldamento&state=OFF" class="btn off">Spegni</a>
        </div>
        <div class="card">
            <h3>Tapparelle</h3>
            <a href="/tapparella_up" class="btn on">SU</a>
            <a href="/tapparella_down" class="btn off">GIU</a>
        </div>
        <div class="card">
            <h3>Allarme</h3>
            <p>Stato: <span class="status">{{ALLARME_STATE}}</span></p>
            <a href="/toggle_allarme" class="btn {{ALLARME_CLASS}}">Toggle Allarme</a>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
async def index(request):
    html = HTML_TEMPLATE

    # Replace dynamic content in HTML template
    temp_str = f"{temperature_slave:.1f}" if temperature_slave is not None else "N/A"
    html = html.replace("{{TEMP}}", temp_str)
    html = html.replace("{{DES_TEMP}}", str(desired_temperature))

    auto_mode = led_states.get("auto_mode", False)
    html = html.replace("{{AUTO_MODE}}", "ON" if auto_mode else "OFF")
    html = html.replace("{{AUTO_MODE_CLASS}}", "on" if auto_mode else "off")

    aria = led_states.get("aria_condizionata", False)
    risc = led_states.get("riscaldamento", False)
    html = html.replace("{{ARIA_STATE}}", "ON" if aria else "OFF")
    html = html.replace("{{RISC_STATE}}", "ON" if risc else "OFF")

    allarme_state = led_states.get("allarme", False)
    html = html.replace("{{ALLARME_STATE}}", "ON" if allarme_state else "OFF")
    html = html.replace("{{ALLARME_CLASS}}", "on" if allarme_state else "off")

    # Dynamically generate HTML for light controls
    lights_html = ""
    for name, state in led_states.items():
        if name in ["aria_condizionata", "riscaldamento", "auto_mode", "allarme", "tapparelle"]:
            continue
        state_str = "ON" if state else "OFF"
        lights_html += f"""
        <div class="card">
            <h3>{name.upper()}</h3>
            <p>Stato: <span class="status">{state_str}</span></p>
            <a href="/update?id={name}&state=ON" class="btn on">Accendi</a>
            <a href="/update?id={name}&state=OFF" class="btn off">Spegni</a>
        </div>
        """
    html = html.replace("{{LIGHTS}}", lights_html)

    return Response(body=html, headers={"Content-Type": "text/html"})

@app.route("/toggle_auto")
async def toggle_auto(request):
    led_states["auto_mode"] = not led_states.get("auto_mode", False)
    save_states()
    evaluate_auto_logic() # Re-evaluate auto logic immediately
    draw_page() # Update display
    return redirect("/")

@app.route("/temp_up")
async def temp_up(request):
    global desired_temperature
    desired_temperature = min(desired_temperature + 1, 26)
    save_states()
    if led_states["auto_mode"]:
        evaluate_auto_logic()
    draw_page() # Update display
    return redirect("/")

@app.route("/temp_down")
async def temp_down(request):
    global desired_temperature
    desired_temperature = max(desired_temperature - 1, 18)
    save_states()
    if led_states["auto_mode"]:
        evaluate_auto_logic()
    draw_page() # Update display
    return redirect("/")

@app.route("/tapparella_up")
async def tapparella_up(request):
    global tapparella_state, tapparella_last_change
    if client:
        client.publish("home/actuator/tapparella/set", "up")
        tapparella_state = "up"
        tapparella_last_change = time.time()
        print("MQTT: tapparella → SU (via Web)")
    draw_page()
    return redirect("/")
@app.route("/tapparella_down")
async def tapparella_down(request):
    global tapparella_state, tapparella_last_change
    if client:
        client.publish("home/actuator/tapparella/set", "down")
        tapparella_state = "down"
        tapparella_last_change = time.time()
        print("MQTT: tapparella → GIU (via Web)")
    draw_page() # Update display
    return redirect("/")

@app.route("/toggle_allarme")
async def toggle_allarme(request):
    led_states["allarme"] = not led_states["allarme"]

    # ✅ Pubblica per lo slave
    client.publish("home/sensor/alarm/set", b"on" if led_states["allarme"] else b"off", retain=True)

    # ✅ Pubblica per aggiornare stato visibile (interfaccia e altri)
    client.publish("home/led/allarme/state", b"ON" if led_states["allarme"] else b"OFF", retain=True)
    client.publish("home/led/allarme/command", b"ON" if led_states["allarme"] else b"OFF", retain=True)

    # ✅ Simula ricezione per aggiornare display locale
    mqtt_callback(
        b"home/led/allarme/state",
        b"ON" if led_states["allarme"] else b"OFF"
    )

    save_states()
    draw_page()
    return redirect("/")
@app.route("/update")
async def update(req):
    device = req.args.get("id")
    state = req.args.get("state")
    print(f"[HTTP] Richiesta /update → id={device}, state={state}")
    if device in led_states and state in ["ON", "OFF"]:
        set_device_state(device, state == "ON")
        return redirect("/")  # ✅ Importantissimo!
    else:
        return Response("Invalid request", status_code=400)
# ===========================
# MAIN ASYNC TASKS
# ===========================
async def standby_task():
    global standby, last_touch_time
    while True:
        if not standby:
            if time.time() - last_touch_time > STANDBY_TIMEOUT:
                standby = True
                bl.value(0) # Turn backlight off
                display.fill(color565(0, 0, 0)) # Clear display
                print("Display in standby")
        await asyncio.sleep(0.1) # Check every 100ms

async def mqtt_loop():
    while True:
        if client:
            try:
                client.check_msg() # Process incoming MQTT messages
            except Exception as e:
                print("MQTT check_msg error:", e)
                # Attempt to reconnect if there's an MQTT error
                connect_mqtt() 
        else:
            # If client is not connected, try to connect
            connect_mqtt()
        await asyncio.sleep(1) # Check MQTT every second

async def touch_loop():
    while True:
        check_touch() # Handle touch events
        # Refresh tapparella page if momentary state is active
        if current_page == PAGE_TAPPARELLE and tapparella_state:
            if time.time() - tapparella_last_change > 2:
                # This logic is already handled in draw_tapparelle_page,
                # but redrawing here ensures the state is cleared visually.
                # A more efficient way would be to only redraw the specific button.
                draw_page() 
        await asyncio.sleep(0.05) # Check touch every 50ms
        
async def web_server_task():
    server = await asyncio.start_server(app._handle, "0.0.0.0", 80)
    print("✅ Web server in ascolto su porta 80")
    await server.wait_closed()
async def main():
    connect_wifi() # Connect to Wi-Fi
    connect_mqtt() # Connect to MQTT broker
    publish_all_states() # Publish initial states to MQTT
    draw_page() # Initial draw of the display
    
    # Evaluate auto logic on startup if auto mode is enabled
    if led_states.get("auto_mode", False):
        evaluate_auto_logic()
    
    global last_touch_time
    last_touch_time = time.time() # Initialize last touch time

    # Start all asynchronous tasks concurrently
    await asyncio.gather(
        web_server_task(),  
        mqtt_loop(),
        standby_task(),
        touch_loop()
    )

try:
    asyncio.run(main()) # Run the main asynchronous loop
except KeyboardInterrupt:
    print("Server interrupted")
finally:
    # Clean up resources if necessary (e.g., turn off backlight)
    bl.value(0)
    print("Application stopped.")


