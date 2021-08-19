import http
import ipaddress
import json
import logging
import random
import time

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import redirect, render
from django.http import HttpResponseNotFound
from django.shortcuts import render

from django.http import HttpResponse
from django.template.context_processors import request
from django.views.decorators.http import require_POST
from icecream import ic
from paho.mqtt.client import Client
from pymaybe import maybe
from ipware import get_client_ip

from door_commander import wsgi, settings
from door_commander.mqtt import MqttDoorCommanderEndpoint, door_commander_mqtt
from door_commander.settings import IPWARE_KWARGS, PERMITTED_IP_NETWORKS
from web_homepage.models import Door

log = logging.getLogger(__name__)
log_ip = logging.getLogger(__name__+".ip")



def home(request):
    context = get_request_context(request)
    doors = {door.id: door.display_name for door in (Door.objects.all())}

    doors_status = fetch_status()
    context.update(dict(
        doors=doors,
        doors_status=doors_status,
    ))
    return render(request, 'web_homepage/index.html', context=context)
    # return redirect("https://betreiberverein.de/impressum/")


def fetch_status():
    return {
        (
            door.display_name,
            door_commander_mqtt.doors_presence.get(door.mqtt_id),
        ) for door in (Door.objects.all())
    }


def get_request_context(request):
    context = dict(
        can_open_door=check_can_open_door(request)
    )
    return context


def check_can_open_door(request):
    is_authenticated = request.user.is_authenticated
    has_permission = request.user.has_perm(PERMISSION_OPEN_DOOR)
    has_allowed_location = check_has_allowed_location(request)
    is_allowed = is_authenticated and has_permission  # and has_allowed_location
    log.debug(ic.format(is_authenticated, has_permission, has_allowed_location, is_allowed))
    return is_allowed


def check_has_allowed_location(request):
    ip, is_public = get_client_ip(request, **IPWARE_KWARGS)
    log_ip.debug(ic.format(ip, is_public))
    log_ip.debug(ic.format(request.META))
    log_ip.debug(ic.format(request.headers))
    log_ip.debug(ic.format(settings.IPWARE_KWARGS, settings._nginx_address))
    has_correct_location = False
    if ip:
        # Allow requests from the local network of the server
        if not is_public:
            has_correct_location = True
        if any((ipaddress.ip_address(ip) in network for network in PERMITTED_IP_NETWORKS)):
            has_correct_location = True
        if request.user.has_perm(PERMISSION_LOCATION_OVERRIDE):
            has_correct_location = True
    return has_correct_location


PERMISSION_OPEN_DOOR = 'door_controller.open_door'
PERMISSION_LOCATION_OVERRIDE = 'door_controller.assume_correct_location'


@require_POST  # for CSRF protection
@login_required
@permission_required(PERMISSION_OPEN_DOOR)  # this is just a safeguard, there are more requirements.
def open(request, door_id):
    if not check_can_open_door(request):
        raise PermissionDenied("You are not allowed to open the door.")

    assert door_commander_mqtt
    door = Door.objects.get(pk=door_id)
    mqtt_id = door.mqtt_id

    door_commander_mqtt.open(mqtt_id, timeout=time.time() + 30)

    context = dict(message=str())
    return render(request, 'web_homepage/open.html', context=context)
