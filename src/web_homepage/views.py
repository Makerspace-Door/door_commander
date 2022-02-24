import ipaddress
import logging
from os import WIFSIGNALED
import time

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from icecream import ic
from ipware import get_client_ip

from doors.mqtt import door_commander_mqtt
from django.conf import settings
from doors.models import PERMISSION_OPEN_DOOR, PERMISSION_LOCATION_OVERRIDE, Door
from clientipaddress.mqtt import wifi_locator_mqtt

log = logging.getLogger(__name__)
log_ip = logging.getLogger(__name__ + ".ip")


IPWARE_KWARGS = getattr(settings, 'IPWARE_KWARGS', None)
PERMITTED_IP_NETWORKS = getattr(settings, 'PERMITTED_IP_NETWORKS', None)

def home(request):
    context = get_request_context(request)
    doors = {door.id: door.display_name for door in (Door.objects.all())}
    has_allowed_location, allowed_location_reason = \
        check_has_allowed_location(request)

    doors_status = fetch_status()
    context.update(dict(
        doors=doors,
        doors_status=doors_status,
        has_allowed_location=has_allowed_location
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
    return is_allowed


def check_has_allowed_location(request):
    if IPWARE_KWARGS is None or PERMITTED_IP_NETWORKS is None:
        return True, "not configured"
    else:
        ip = get_client_ip(request, **IPWARE_KWARGS)
        log_ip.debug(ic.format('ip', ip))
        # log_ip.debug(ic.format(request.META))
        # log_ip.debug(ic.format(request.headers))
        has_correct_location = False
        reason = []
        if ip:
            networks = wifi_locator_mqtt.ip_networks
            for locator_mqtt_id, locator_ip_networks in networks.items():
                for locator_ip_network in locator_ip_networks:
                    if ip in locator_ip_network:
                        has_correct_location = True
                        reason.append("in locator networks")
                log_ip.debug(ic.format('locator_ip_networks', locator_ip_networks))
            if any((ipaddress.ip_address(ip) in network for network in PERMITTED_IP_NETWORKS)):
                has_correct_location = True
                reason.append("in permitted networks")
            if request.user.has_perm(PERMISSION_LOCATION_OVERRIDE):
                has_correct_location = True
                reason.append("permission overwrite")
        return has_correct_location, ", ".join(reason)


@require_POST  # for CSRF protection
@login_required
@permission_required(PERMISSION_OPEN_DOOR)  # this is just a safeguard, there are more requirements.
def open(request, door_id):
    if not check_can_open_door(request):
        raise PermissionDenied("You are not allowed to open the door.")
    if not check_has_allowed_location(request)[0]:
        messages.error(request, "You are in the wrong location. Consider joining the ZAM Wi-Fi.")
        return redirect(home)

    assert door_commander_mqtt
    door = Door.objects.get(pk=door_id)
    mqtt_id = door.mqtt_id

    door_commander_mqtt.open(mqtt_id, timeout=time.time() + 30)

    log.warn(ic.format(
        request.user,
        get_client_ip(request, **IPWARE_KWARGS),
        door,
        door.display_name))

    return redirect(home)
