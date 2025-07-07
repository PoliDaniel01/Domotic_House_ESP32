import time
from umqtt.simple import MQTTClient as BaseMQTTClient

class MQTTClient(BaseMQTTClient):
    DELAY = 2
    DEBUG = True

    def delay(self, i):
        time.sleep(self.DELAY)

    def log(self, in_reconnect, e):
        if self.DEBUG:
            if in_reconnect:
                print("MQTT reconnect error:", e)
            else:
                print("MQTT error:", e)

    def reconnect(self):
        i = 0
        while True:
            try:
                return super().connect(False)
            except OSError as e:
                self.log(True, e)
                i += 1
                self.delay(i)

    def publish(self, topic, msg, retain=False, qos=0):
        while True:
            try:
                return super().publish(topic, msg, retain, qos)
            except OSError as e:
                self.log(False, e)
                self.reconnect()

    def wait_msg(self):
        while True:
            try:
                return super().wait_msg()
            except OSError as e:
                self.log(False, e)
                self.reconnect()

    def check_msg(self, attempts=2):
        while attempts:
            self.sock.setblocking(False)
            try:
                return super().wait_msg()
            except OSError as e:
                self.log(False, e)
                self.reconnect()
            attempts -= 1
