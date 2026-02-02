#!/usr/bin/env python3
import time
import json
import sys
import os
from configparser import ConfigParser
import paho.mqtt.client as mqtt
from senseair_s8 import SenseairS8

# Load configuration
config = ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), 'config.ini')

if not os.path.exists(config_file):
    print(f"Error: Configuration file not found at {config_file}")
    sys.exit(1)

config.read(config_file)

# MQTT Configuration
MQTT_BROKER = config.get('mqtt', 'broker')
MQTT_PORT = config.getint('mqtt', 'port')
MQTT_USERNAME = config.get('mqtt', 'username')
MQTT_PASSWORD = config.get('mqtt', 'password')

# Sensor Configuration
SENSOR_PORT = config.get('sensor', 'port')
DEVICE_ID = config.get('sensor', 'device_id')
DEVICE_NAME = config.get('sensor', 'device_name')

# Home Assistant Configuration
DISCOVERY_PREFIX = config.get('homeassistant', 'discovery_prefix')
STATE_TOPIC = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/state"
DISCOVERY_TOPIC = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/co2/config"
AVAILABILITY_TOPIC = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/availability"

# Polling Configuration
POLL_INTERVAL = config.getint('polling', 'interval')

# Initialize sensor
sensor = SenseairS8(port=SENSOR_PORT)

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        # Publish online status
        mqttc.publish(AVAILABILITY_TOPIC, "online", retain=True)
        publish_discovery()
    else:
        print(f"Failed to connect, return code {rc}")

def publish_discovery():
    """Publish Home Assistant MQTT discovery configuration"""
    discovery_payload = {
        "name": "CO2",
        "device_class": "carbon_dioxide",
        "state_topic": STATE_TOPIC,
        "unit_of_measurement": "ppm",
        "value_template": "{{ value_json.co2 }}",
        "unique_id": f"{DEVICE_ID}_co2",
        "availability_topic": AVAILABILITY_TOPIC,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": {
            "identifiers": [DEVICE_ID],
            "name": DEVICE_NAME,
            "model": "Senseair S8",
            "manufacturer": "Senseair"
        }
    }

    mqttc.publish(DISCOVERY_TOPIC, json.dumps(discovery_payload), retain=True)
    print("Published discovery configuration")

def read_co2():
    return sensor.co2()

# Setup MQTT client
mqttc = mqtt.Client()
mqttc.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
mqttc.on_connect = on_connect

# Set Last Will and Testament - MUST be set before connect()
mqttc.will_set(AVAILABILITY_TOPIC, "offline", retain=True)

mqttc.connect(MQTT_BROKER, MQTT_PORT)
mqttc.loop_start()

# Main loop
try:
    while True:
        co2 = read_co2()
        if co2:
            payload = json.dumps({"co2": co2})
            mqttc.publish(STATE_TOPIC, payload)
            print(f"CO₂: {co2} ppm")
        time.sleep(POLL_INTERVAL)
except KeyboardInterrupt:
    print("\nShutting down...")
    # Publish offline status before disconnecting
    mqttc.publish(AVAILABILITY_TOPIC, "offline", retain=True)
    mqttc.loop_stop()
    mqttc.disconnect()
