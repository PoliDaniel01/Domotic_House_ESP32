import network
import time
import urequests
from machine import Pin


# configuration
DEVICE_ID = '1'		
CLIENT_ID = f'device_client_{DEVICE_ID}'
MQTT_BROKER = 'test.mosquitto.org'

SSID = ""
PASSWORD = ""

# secret API_KEY
SECRET_API_KEY = "53757065722d5365637265742d4b6579"

#Wi-Fi connection
def connect_wifi(ssid, password):
	"""Connects to Wi-Fi and waits until the connection is established."""
	wlan = network.WLAN(network.STA_IF)
	wlan.active(True)
	if not wlan.isconnected():
		print(f'Connecting to network {ssid}...')
		wlan.connect(ssid, password)
		# Wait for connection
	    while not wlan.isconnected():
			print('.')
			time.sleep(1)

	ip_address = wlan.ifconfig()[0]
	print(f'Connection successful. IP address: {ip_address}')
	return wlan

# MQTT Callback
def subscription_callback(topic, msg):
	"""Handles commands received from the broker."""
	command = msg.decode()
	print(f'Received command: {command}')
	if command == 'ON':
		led.on()
	elif command == 'OFF':
		led.off()
	# After changing state, report back
	publish_state()

# --- MQTT Helper Functions ---
def connect_and_subscribe():
	global mqtt_client
	mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
	mqtt_client.set_callback(subscription_callback)
	mqtt_client.connect()

	# Subscribe to the command topic for this specific light
	command_topic = f'home/lights/{LIGHT_ID}/set'
	mqtt_client.subscribe(command_topic)
	print(f'Connected to MQTT and subscribed to {command_topic}')

def publish_state():
	"""Publishes the current state of the LED."""
	state = 'ON' if led.value() == 1 else 'OFF'
	state_topic = f'home/lights/{LIGHT_ID}/state'
	print(f'Publishing to {state_topic}: {state}')
	mqtt_client.publish(state_topic, state)

# --- Interrupt Handler for Physical Switch ---
def switch_handler(pin):
	pass

##########################################
# Specific board hardware and functions
# Insert here 
##########################################

# server communications functions
def report_state_to_server(DEVICE_ID, DEVICE_STATE):
	"""
	Communicate to server a new state of the device.
	It is called from the interrupt handler of the specific device
	eg. When button gets relised: Toggle Light, send message to server
	"""
	try:
		url = f"{SERVER_HOSTNAME}/update?id={DEVICE_ID}&state={DEVICE_STATE}"
		headers = {'X-API-Key': SECRET_API_KEY}

		print(f"send state to: {url}")

		response = urequests.get(url, headers=headers)
		response.close()
	except Exception as e:
		print(f"Error in sending state to server: {e}")


connect_wifi(SSID, PASSWORD)

#Main loop
while True:
	try:
		mqtt_client.wait_msg()


	except Exception as e:
		print(f"Error: {e}")
		print("Reconnecting")
		time.sleep(5)
		connect_and_subscribe()
