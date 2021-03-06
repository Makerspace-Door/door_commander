import json
import logging

from doors.mqtt import door_commander_mqtt
from doors.models import Door

log = logging.getLogger(__name__)


def publish_door_names(sync=False):
    for door in Door.objects.all():
        publish_door_name(door,sync)


def publish_door_name(door,sync=False):
    log.info("publishing door names for door {}".format(door.id))
    pub = door_commander_mqtt.door_name(door.mqtt_id, door.display_name)
    if sync:
        pub.wait_for_publish()
