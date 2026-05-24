import json
import time
import threading
import yaml

import paho.mqtt.client as mqtt

from state_manager import state

# =====================================================
# LOAD CONFIG
# =====================================================

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

mqtt_config = config["mqtt"]

MQTT_BROKER = mqtt_config["broker"]
MQTT_PORT = mqtt_config["port"]

MQTT_TOPIC = mqtt_config["telemetry_topic"]

client = mqtt.Client()

# =====================================================
# MQTT CALLBACKS
# =====================================================

def on_connect(client, userdata, flags, rc):

    print("MQTT connected", rc)

    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):

    try:

        payload = json.loads(
            msg.payload.decode()
        )

        print("Telemetry:", payload)

        state.sensor_online = True

        state.last_sensor_update = time.time()

        state.low_sensor_wet = payload.get(
            "low_sensor_wet",
            False
        )

        state.high_sensor_wet = payload.get(
            "high_sensor_wet",
            False
        )

    except Exception as e:

        print("MQTT parse error:", e)

client.on_connect = on_connect
client.on_message = on_message

# =====================================================
# START MQTT THREAD
# =====================================================

def start_mqtt():

    client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        60
    )

    client.loop_forever()

mqtt_thread = threading.Thread(
    target=start_mqtt
)

mqtt_thread.daemon = True