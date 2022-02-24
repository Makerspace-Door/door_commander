import json
from json import loads
from logging import getLogger
from numbers import Number

from decorated_paho_mqtt import GenericMqttEndpoint, pack_topic
from django.conf import settings
from django.utils.functional import lazy
from icecream import ic
from paho.mqtt.client import MQTTMessage
from pymaybe import maybe

from django.conf import settings
from doors.models import Door
import lazy_object_proxy

MQTT_CLIENT_KWARGS = settings.MQTT_CLIENT_KWARGS
MQTT_SERVER_KWARGS = settings.MQTT_SERVER_KWARGS
MQTT_PASSWORD_AUTH = settings.MQTT_PASSWORD_AUTH
MQTT_TLS = settings.MQTT_TLS

log = getLogger(__name__)


class MqttDoorCommanderEndpoint(GenericMqttEndpoint):
    def __init__(self, client_kwargs: dict, password_auth: dict, server_kwargs: dict, tls: bool):
        super().__init__(client_kwargs, password_auth, server_kwargs, tls)

        self._doors_presence = dict()
        """This is indexed by mqtt id"""

    @property
    def doors_presence(self):
        return self._doors_presence

    @property
    def is_connected(self):
        """This is only informational, please use qos=1 or qos=2 if you require a message to be sent."""
        return self._mqttc.is_connected()

    @GenericMqttEndpoint.subscribe_decorator("door/+/presence", qos=2)
    # door_id is automatically filled in with the value for the "+" by the decorator
    def update_presence(self, door_id, *, client, userdata, message: MQTTMessage):
        try:
            # This is faked by paho upon receipt, we could use the current time ourselves just as well.
            #  It will not be able to recognize connection delay.
            locally_faked_timestamp: float = message.timestamp

            topic: str = message.topic
            retained = message.retain
            props = maybe(message.properties).json()
            timestamp = props.timestamp
            parsed_payload = loads(message.payload)
            # door_id, = unpack_topic("door/+/presence", message.topic)
            #ic(topic,
            #   props,
            #   locally_faked_timestamp,
            #   timestamp,
            #   retained,
            #   message.payload,
            #   parsed_payload,
            #   door_id)

            self._doors_presence[door_id] = bool(parsed_payload)

            #ic(self._doors_presence)
        except:
            log.error("Failed to parse door presence message.")

    def open(self, mqtt_id, timeout: Number):
        payload = dict(not_after=timeout)
        self.publish("door/+/open", mqtt_id, qos=2, retain=False, payload=json.dumps(payload))

    def door_name(self, mqtt_id, name):
        topic = pack_topic("door/+/display_name", mqtt_id)
        return self._mqttc.publish(topic, json.dumps(name), qos=2,retain=True)

def start_connection():
    door_commander_mqtt = MqttDoorCommanderEndpoint(
        client_kwargs=MQTT_CLIENT_KWARGS,
        password_auth=MQTT_PASSWORD_AUTH,
        server_kwargs=MQTT_SERVER_KWARGS,
        tls=MQTT_TLS
    )
    door_commander_mqtt.connect()
    return door_commander_mqtt

door_commander_mqtt: MqttDoorCommanderEndpoint = lazy_object_proxy.Proxy(start_connection)
