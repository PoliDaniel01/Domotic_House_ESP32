from machine import Pin, SPI
import time
import network
from umqtt.simple import MQTTClient
from st7789 import ST7789, color565
import vga1_8x8 as font
from xpt2046 import Touch

# ==============================
# HARD RESET + INIT RAW ST7789
# ==============================

spi_disp = SPI(1, baudrate=10000000, sck=Pin(14), mosi=Pin(13))
dc = Pin(2, Pin.OUT)
cs = Pin(15, Pin.OUT)
rst = Pin(33, Pin.OUT)
bl = Pin(21, Pin.OUT)

bl.value(1)

cs.value(1)
rst.value(0)
time.sleep_ms(200)
rst.value(1)
time.sleep_ms(200)

def write_cmd(cmd):
    dc.value(0)
    cs.value(0)
    spi_disp.write(bytearray([cmd]))
    cs.value(1)

def write_data(data):
    dc.value(1)
    cs.value(0)
    spi_disp.write(bytearray([data]))
    cs.value(1)

write_cmd(0x01)
time.sleep_ms(150)
write_cmd(0x11)
time.sleep_ms(150)
write_cmd(0x3A)
write_data(0x55)
write_cmd(0x29)
time.sleep_ms(50)

print("Display inizializzato via init RAW!")

display = ST7789(
    spi_disp,
    240,
    320,
    dc=dc,
    reset=rst,
    cs=cs,
    rotation=1
)

spi_touch = SPI(2, baudrate=1000000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
cs_touch = Pin(33, Pin.OUT)
touch = Touch(spi_touch, cs_touch)

# ===========================
# CONFIGURAZIONE
# ===========================
WIFI_SSID = "WIFI-NAME"
WIFI_PASS = "Password"
MQTT_BROKER = "broker"

STANDBY_TIMEOUT = 60

client = None

led_states = {
    "soggiorno": False,
    "cucina": False,
    "camera": False,
    "aria_condizionata": False,
    "riscaldamento": False,
}

PAGE_MAIN = "main"
PAGE_LUCI = "luci"
PAGE_RISCALDAMENTO = "riscaldamento"
PAGE_TAPPARELLE = "tapparelle"

current_page = PAGE_MAIN
last_touch_time = 0
standby = False

# ===========================
# DRAW FUNCTIONS
# ===========================

def draw_page():
    display.fill(color565(0,0,0))
    
    if current_page == PAGE_MAIN:
        draw_main_page()
    elif current_page == PAGE_LUCI:
        draw_luci_page()
    elif current_page == PAGE_RISCALDAMENTO:
        draw_riscaldamento_page()
    elif current_page == PAGE_TAPPARELLE:
        draw_tapparelle_page()

def draw_main_page():
    display.text(font, "MENU PRINCIPALE", 40, 10, color565(255,255,255), color565(0,0,0))

    buttons = [
        ("LUCI", 20, 50),
        ("RISCALDAMENTO", 20, 110),
        ("TAPPARELLE", 20, 170),
    ]

    for label, x, y in buttons:
        display.fill_rect(x, y, 200, 40, color565(50,50,50))
        display.rect(x, y, 200, 40, color565(255,255,255))
        display.text(font, label, x+10, y+15, color565(255,255,255), color565(50,50,50))

def draw_luci_page():
    display.text(font, "LUCI CASA", 60, 5, color565(255,255,255), color565(0,0,0))

    buttons = {
        "soggiorno": (20, 40, 100, 40),
        "cucina": (20, 100, 100, 40),
        "camera": (20, 160, 100, 40),
    }

    for name, (x, y, w, h) in buttons.items():
        stato_color = color565(255,0,255) if led_states[name] else color565(0,255,255)
        display.fill_rect(x, y, w, h, color565(0,0,0))
        display.rect(x, y, w, h, color565(255,255,255))
        display.text(font, name.upper(), x + 5, y + 15, color565(255,255,255), color565(0,0,0))
        display.fill_rect(x + w + 10, y + 10, 20, 20, stato_color)

    # Nuovo bottone SPEGNI TUTTO
    display.fill_rect(20, 200, 120, 40, color565(255,0,0))
    display.rect(20, 200, 120, 40, color565(255,255,255))
    display.text(font, "SPEGNI TUTTO", 25, 215, color565(255,255,255), color565(255,0,0))

    # BACK spostato a destra
    display.fill_rect(160, 200, 60, 40, color565(100,100,100))
    display.rect(160, 200, 60, 40, color565(255,255,255))
    display.text(font, "BACK", 165, 215, color565(255,255,255), color565(100,100,100))

def draw_riscaldamento_page():
    display.text(font, "RISCALDAMENTO", 40, 5, color565(255,255,255), color565(0,0,0))

    buttons = {
        "aria_condizionata": (20, 60, 180, 40),
        "riscaldamento": (20, 120, 180, 40),
    }

    for name, (x, y, w, h) in buttons.items():
        stato_color = color565(0,255,0) if led_states[name] else color565(255,0,0)
        display.fill_rect(x, y, w, h, color565(0,0,0))
        display.rect(x, y, w, h, color565(255,255,255))
        display.text(font, name.upper(), x + 5, y + 15, color565(255,255,255), color565(0,0,0))
        display.fill_rect(x + w + 10, y + 10, 20, 20, stato_color)

    display.fill_rect(20, 200, 100, 40, color565(100,100,100))
    display.rect(20, 200, 100, 40, color565(255,255,255))
    display.text(font, "BACK", 30, 215, color565(255,255,255), color565(100,100,100))

def draw_tapparelle_page():
    display.text(font, "TAPPARELLE", 60, 5, color565(255,255,255), color565(0,0,0))
    display.fill_rect(20, 200, 100, 40, color565(100,100,100))
    display.rect(20, 200, 100, 40, color565(255,255,255))
    display.text(font, "BACK", 30, 215, color565(255,255,255), color565(100,100,100))

# ===========================
# TOUCH CHECK
# ===========================

def check_touch():
    global current_page, last_touch_time, standby

    pos = touch.get_touch()
    if pos:
        last_touch_time = time.time()

        if standby:
            standby = False
            bl.value(1)
            draw_page()
            print("Wakeup!")
            return

        x, y = pos
        x, y = y, x

        if current_page == PAGE_MAIN:
            if 20 <= x <= 220 and 50 <= y <= 90:
                current_page = PAGE_LUCI
            elif 20 <= x <= 220 and 110 <= y <= 150:
                current_page = PAGE_RISCALDAMENTO
            elif 20 <= x <= 220 and 170 <= y <= 210:
                current_page = PAGE_TAPPARELLE
            draw_page()
            return

        if current_page == PAGE_LUCI:
            # SPEGNI TUTTO
            if 20 <= x <= 140 and 200 <= y <= 240:
                for name in ["soggiorno", "cucina", "camera"]:
                    led_states[name] = False
                    publish_led_state(name)
                draw_page()
                return

            # BACK
            if 160 <= x <= 220 and 200 <= y <= 240:
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
                    led_states[name] = not led_states[name]
                    publish_led_state(name)
                    draw_page()
                    return

        if current_page == PAGE_RISCALDAMENTO:
            if 20 <= x <= 120 and 200 <= y <= 240:
                current_page = PAGE_MAIN
                draw_page()
                return

            buttons = {
                "aria_condizionata": (20, 60, 180, 40),
                "riscaldamento": (20, 120, 180, 40),
            }
            for name, (bx, by, bw, bh) in buttons.items():
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    # blocco reciproco
                    if name == "aria_condizionata":
                        if led_states["riscaldamento"]:
                            print("⚠️ Spengo riscaldamento per accendere aria.")
                            led_states["riscaldamento"] = False
                            publish_led_state("riscaldamento")
                            time.sleep(0.5)
                        led_states[name] = not led_states[name]
                        publish_led_state(name)
                        draw_page()
                        return

                    if name == "riscaldamento":
                        if led_states["aria_condizionata"]:
                            print("⚠️ Spengo aria condizionata per accendere riscaldamento.")
                            led_states["aria_condizionata"] = False
                            publish_led_state("aria_condizionata")
                            time.sleep(0.5)
                        led_states[name] = not led_states[name]
                        publish_led_state(name)
                        draw_page()
                        return

        if current_page == PAGE_TAPPARELLE:
            if 20 <= x <= 120 and 200 <= y <= 240:
                current_page = PAGE_MAIN
                draw_page()
                return

# ===========================
# MQTT
# ===========================

def publish_led_state(name):
    if client:
        topic = f"home/led/{name}"
        value = b"ON" if led_states[name] else b"OFF"
        try:
            client.publish(topic, value, retain=True)
            print(f"→ MQTT invio {topic} = {value}")
        except Exception as e:
            print("MQTT publish error:", e)
    else:
        print("MQTT client not connected!")

def mqtt_callback(topic, msg):
    topic_str = topic.decode()
    msg_str = msg.decode()
    print(f"MQTT message received: topic={topic_str}, msg={msg_str}")

    key = topic_str.split("/")[-1]

    if key in led_states:
        led_states[key] = (msg_str in ["ON", "AUTO_ON"])
        draw_page()

# ===========================
# WIFI + MQTT CONNECTION
# ===========================

def connect_wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(WIFI_SSID, WIFI_PASS)
    while not sta.isconnected():
        time.sleep(0.5)
    print("WiFi connected:", sta.ifconfig())

def connect_mqtt():
    global client
    try:
        client = MQTTClient("esp32-leds", MQTT_BROKER)
        client.set_callback(mqtt_callback)
        client.connect()
        for key in led_states.keys():
            client.subscribe(f"home/led/{key}".encode())
        print("Connected to MQTT broker and subscribed to topics")
    except Exception as e:
        print("MQTT connection error:", e)
        client = None

# ===========================
# MAIN LOOP
# ===========================

def main():
    global standby, last_touch_time

    connect_wifi()
    connect_mqtt()

    draw_page()
    last_touch_time = time.time()

    while True:
        check_touch()

        if client:
            try:
                client.check_msg()
            except Exception as e:
                print("MQTT check_msg error:", e)

        if not standby:
            if time.time() - last_touch_time > STANDBY_TIMEOUT:
                standby = True
                bl.value(0)
                display.fill(color565(0, 0, 0))
                print("Display in standby")

        time.sleep(0.05)

if __name__ == "__main__":
    main()
