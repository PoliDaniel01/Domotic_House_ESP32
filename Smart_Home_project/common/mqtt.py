# smarthome/common/mqtt.py

from umqtt.simple import MQTTClient

def connect_mqtt(client_id, broker, callback, subscriptions=None):
    """
    Connects to an MQTT broker and subscribes to topics.

    :param client_id: The unique client ID for the MQTT connection.
    :type client_id: str
    :param broker: The address of the MQTT broker.
    :type broker: str
    :param callback: The function to call when a message is received.
    :type callback: function
    :param subscriptions: A list of topics to subscribe to.
    :type subscriptions: list, optional
    :return: The MQTT client object.
    :rtype: MQTTClient
    """
    client = MQTTClient(client_id, broker)
    client.set_callback(callback)
    
    print(f"Connecting to MQTT broker at {broker}...")
    client.connect()
    print("Successfully connected to MQTT broker.")
    
    if subscriptions:
        for topic in subscriptions:
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic.decode()}")
            
    return client

