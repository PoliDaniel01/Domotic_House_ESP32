"""
Main ESP32 code
This ESP32 will deal with the connection with all of the other client boards
It is built as a microserver, dealing with the connection
It keeps state info in a separated file state.json
"""

import network
import json
import uasyncio as asyncio
from microdot_asyncio import Microdot, Response, redirect, send_file
from umqtt.simple import MQTTClient

# Config
MQTT_BROKER = 'test.mosquitto.org'
CLIENT_ID = 'smart-home-hub'


SECRET_API_KEY = "53757065722d5365637265742d4b6579"
STATE_FILE = "states.json"

#html files
INDEX_HTML = "better.html"


# Wi-Fi credentials
SSID = "wifiname"
PASSWORD = "wifipsw"
HOSTNAME = "smart-home-server"


# States file logic
def save_states(states):
	try:
		with open(STATE_FILE, 'w') as f:
			json.dump(states, f)
		print("data saved on flash")
	except Exception as e:
		print(f"Error saving state: {e}")

def load_states():
	try:
		with open(STATE_FILE, 'r') as f:
			states = json.load(f)
			print("data loaded")
			return states
	except Exception as e:
		print(f"State file not found. Error: {e}")
		# Set up a default state
		return {'1': 'OFF', '2': 'OFF'}


#read html code for page
def load_html(FILE):
	try:
		with open(FILE, 'r') as f:
			page = f.read()
		return page
	except Exception as e:
		print(f"Error loading html file. Error: {e}")
		return "<div><p>device not available</p></div>"


# Load states when starting
states = load_states()

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

#MQTT callback
def subscription_callback(topic, msg):
	global states
	topic_str = topic.decode()
	msg.str = msg.decode()
	print('Received message')
	parts = topic_str.split('/')
	if len(parts) == 4 and parts[0] == 'home' and parts[3] == 'state':
		category, device_id = parts[1], parts[2]
		if category in states and device_id in states[category]:
			states[category][device_id] = msg_str
			save_states(states)

# server init
app = Microdot()

# Authentication decorator
def require_api_key(func):
	"""
	This decorator serves as protector for APIs end points.
	It checks presence and correctnesses of API_KEY in request header
	"""
	async def wrapper(request, *args, **kwargs):
		api_key = request.headers.get('X-API-Key')
		if api_key and api_key == SECRET_API_KEY:
			# key is valid, proceed
			return await func(request, *args, **kwargs)
		else:
			return Response(body = 'Unauthorized', status_code=401)
	return wrapper


# Routes definition
"""
	/ 					=> main page, used for user connection
	/update 			=> update a state, used by boards or user to change devices status
	/status-all 		=> returns all of the statuses for different devices
	/status/<device_id> => gets the current status for a device, 
							useful to make sure that boards know if they should turn-off their devices
"""

@app.route('/')
async def index(request):
	"""
	Actual user connection end-point, does not need a key 
	To use a key one should implement a log-in process and 
	maybe even a cloud-iot connection to secure the process
	"""
	return send_file(INDEX_HTML, template_args={'clima': states['clima'], 'lights': states['lights'], 'api_key': SECRET_API_KEY})


@app.route('/update')
@require_api_key
async def update(request):
	device_id = request.args.get('id')
	new_state = request.args.get('state')

	if device_id in states['lights']:
		topic = f'home/lights/{device_id}/set'
		print(f"Publishing to {topic}: {new_state}")
		mqtt_client.publish(topic, new_state)
	elif device_id in states['clima']:
		topic = f'home/clima/{device_id}/set'
		print(f"Publishing to {topic}: {new_state}")
		mqtt_client.publish(topic, new_state)
	return redirect('/')


@app.route('/status/<device_id>')
@require_api_key
async def get_status(request, device_id):
	for sector in states.keys():
		if device_id in states[sector]:
			state = states[sector][device_id]
			return Response(body=state, headers={"Content-Type": "text/plain"})
	return Response(body="Device ID not Found", status_code=404)


@app.route('/status-all')
@require_api_key
async def get_status(request):
	return Response(body=json.dumps(states), headers={"Content-Type": "application/json"})



async def check_mqtt_messages():
	"""
	A background task to constantly check for new MQTT messages.
	"""
	while True:
		mqtt_client.check_msg()
		await asyncio.sleep(1)


#main functions, Asynchronous so that it is not blocking
async def main():
	connect_wifi(SSID, PASSWORD)

	global mqtt_client
	mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
	mqtt_client.set_callback(subscription_callback)
	mqtt_client.connect()
	print('Connected to MQTT Broker.')

	# Subscribe to all state updates
	mqtt_client.subscribe('home/lights/+/state')
	mqtt_client.subscribe('home/clima/+/state')
	print('Subscribed to state topics.')

	# Create tasks for the web server and MQTT client
	server_task = app.start_server(port=80, debug=True)
	mqtt_task = asyncio.create_task(check_mqtt_messages())
    
	await asyncio.gather(server_task, mqtt_task)


try:
	asyncio.run(main())
except KeyboardInterrupt:
	print("Server interrupted")

