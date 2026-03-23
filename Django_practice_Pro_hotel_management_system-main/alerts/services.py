import math
import random
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from HotelApp.models import Room

from .models import IoTDevice, RoomConditionAlert, SensorReading


ALERT_COPY = {
    "temperature": {
        "warning": ("Temperature Drift", "Temperature is outside the preferred comfort band."),
        "critical": ("Critical Temperature Event", "Temperature has moved into an unsafe operating range."),
    },
    "gas": {
        "warning": ("Gas Leak Suspected", "Gas concentration is above the early warning threshold."),
        "critical": ("Gas Leak Critical", "Gas concentration is at a critical level and requires urgent action."),
    },
    "motion": {
        "warning": ("Unexpected Motion", "Movement was detected in a room that should be inactive."),
        "critical": ("Security Motion Alert", "Tamper-level motion was detected in a room that should be secured."),
    },
    "device": {
        "warning": ("Device Delay", "The room monitor has not reported recently."),
        "critical": ("Device Offline", "The room monitor appears to be offline."),
    },
}


def room_expected_occupancy(room):
    return room.status in {"occupied", "maintenance"} or room.housekeeping_status == "in_progress"


def _clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def configured_abnormal_room_rate():
    try:
        rate = float(getattr(settings, "IOT_SIM_ABNORMAL_ROOM_RATE", 0.2))
    except (TypeError, ValueError):
        rate = 0.2
    return _clamp(rate, 0.01, 0.9)


def _room_anomaly_probability(room):
    probability = configured_abnormal_room_rate()

    status_adjustments = {
        "available": -0.02,
        "reserved": -0.01,
        "occupied": 0.01,
        "maintenance": 0.08,
    }
    housekeeping_adjustments = {
        "clean": -0.01,
        "dirty": 0.03,
        "in_progress": 0.01,
    }

    probability += status_adjustments.get(room.status, 0)
    probability += housekeeping_adjustments.get(room.housekeeping_status, 0)
    if room.floor >= 3:
        probability += 0.01

    return _clamp(probability, 0.05, 0.55)


def _pick_anomaly_type(rng, room, expected_occupancy):
    if room.status == "maintenance":
        weights = [("temperature", 0.48), ("gas", 0.22), ("motion", 0.30)]
    elif expected_occupancy:
        weights = [("temperature", 0.42), ("gas", 0.18), ("motion", 0.40)]
    else:
        weights = [("temperature", 0.45), ("gas", 0.16), ("motion", 0.39)]
    return _weighted_choice(rng, weights)


def ensure_iot_devices(room_queryset=None):
    rooms = list(room_queryset if room_queryset is not None else Room.objects.all().order_by("floor", "room_number"))
    if not rooms:
        return []

    existing_by_room = {
        device.room_id: device
        for device in IoTDevice.objects.filter(room__in=rooms).select_related("room")
    }
    devices_to_create = []
    for room in rooms:
        if room.id in existing_by_room:
            continue
        devices_to_create.append(
            IoTDevice(
                room=room,
                device_identifier=f"IOT-{room.room_number}",
                simulation_enabled=True,
            )
        )
    if devices_to_create:
        IoTDevice.objects.bulk_create(devices_to_create)

    return list(IoTDevice.objects.select_related("room").order_by("room__floor", "room__room_number"))


def _blend(previous_value, target_value, weight=0.35):
    return (previous_value * (1 - weight)) + (target_value * weight)


def _weighted_choice(rng, weighted_pairs):
    total = sum(weight for _, weight in weighted_pairs)
    pick = rng.uniform(0, total)
    upto = 0
    for value, weight in weighted_pairs:
        upto += weight
        if upto >= pick:
            return value
    return weighted_pairs[-1][0]


def _active_alert_map(device):
    return {
        alert.alert_type: alert
        for alert in RoomConditionAlert.objects.filter(device=device, is_active=True)
    }


def simulate_device_payload(device, *, now=None, latest_reading=None):
    now = now or timezone.now()
    room = device.room
    expected_occupancy = room_expected_occupancy(room)
    active_alerts = _active_alert_map(device)
    slot = int(now.timestamp() // max(device.sampling_interval_seconds, 15))
    rng = random.Random(f"{device.device_identifier}:{slot}:{room.status}:{room.housekeeping_status}")
    planned_anomaly = None if active_alerts else (
        _pick_anomaly_type(rng, room, expected_occupancy)
        if rng.random() < _room_anomaly_probability(room)
        else None
    )

    local_now = timezone.localtime(now)
    fractional_hour = local_now.hour + (local_now.minute / 60)
    circadian_wave = math.sin((fractional_hour / 24) * (2 * math.pi) - (math.pi / 3))

    base_temp = 22.4 + (circadian_wave * 1.6) + (room.floor * 0.12)
    if room.status == "occupied":
        base_temp += 0.9
    elif room.status == "maintenance":
        base_temp += 1.8
    elif room.status == "reserved":
        base_temp += 0.3

    if latest_reading:
        temperature_c = _blend(latest_reading.temperature_c, base_temp, weight=0.32) + rng.uniform(-0.5, 0.6)
    else:
        temperature_c = base_temp + rng.uniform(-0.8, 0.8)

    if "temperature" in active_alerts:
        if active_alerts["temperature"].severity == "critical":
            temperature_c = max(temperature_c, rng.uniform(31.5, 35.8))
        else:
            temperature_c = max(temperature_c, rng.uniform(28.1, 30.4))
    elif planned_anomaly == "temperature":
        if rng.random() < 0.78:
            temperature_c = rng.uniform(28.3, 32.8)
        else:
            temperature_c = rng.uniform(15.2, 18.4)

    gas_level = int(rng.uniform(4, 22))
    if latest_reading:
        gas_level = int(round(_blend(latest_reading.gas_level, gas_level, weight=0.45)))

    if "gas" in active_alerts:
        if active_alerts["gas"].severity == "critical":
            gas_level = max(gas_level, rng.randint(device.gas_critical_threshold, device.gas_critical_threshold + 70))
        else:
            gas_level = max(gas_level, rng.randint(device.gas_warning_threshold, device.gas_critical_threshold - 5))
    elif planned_anomaly == "gas":
        if rng.random() < 0.24:
            gas_level = rng.randint(device.gas_critical_threshold, device.gas_critical_threshold + 60)
        else:
            gas_level = rng.randint(device.gas_warning_threshold, device.gas_critical_threshold - 5)

    if expected_occupancy:
        motion_state = _weighted_choice(
            rng,
            [("idle", 0.23), ("brief", 0.44), ("active", 0.30), ("tamper", 0.03)],
        )
    else:
        motion_state = _weighted_choice(
            rng,
            [("idle", 0.90), ("brief", 0.08), ("active", 0.015), ("tamper", 0.005)],
        )

    if "motion" in active_alerts:
        motion_state = "tamper" if active_alerts["motion"].severity == "critical" else "active"
    elif planned_anomaly == "motion":
        motion_state = "tamper" if expected_occupancy or rng.random() < 0.28 else "active"

    return {
        "temperature_c": round(temperature_c, 1),
        "gas_level": max(gas_level, 0),
        "motion_state": motion_state,
        "occupancy_expected": expected_occupancy,
        "recorded_at": now,
    }


def evaluate_payload(device, payload):
    room = device.room
    issues = []
    temperature_c = payload["temperature_c"]
    gas_level = payload["gas_level"]
    motion_state = payload["motion_state"]
    occupancy_expected = payload["occupancy_expected"]

    low_warning = device.temperature_min_normal - 2.0
    low_critical = device.temperature_min_normal - 4.0
    high_warning = device.temperature_max_normal + 1.5
    high_critical = device.temperature_max_normal + 3.5

    if temperature_c <= low_critical or temperature_c >= high_critical:
        issues.append(
            {
                "type": "temperature",
                "severity": "critical",
                "message": (
                    f"Room {room.room_number} temperature is {temperature_c}°C, "
                    f"outside the safe operating range."
                ),
            }
        )
    elif temperature_c <= low_warning or temperature_c >= high_warning:
        issues.append(
            {
                "type": "temperature",
                "severity": "warning",
                "message": (
                    f"Room {room.room_number} temperature is drifting at {temperature_c}°C "
                    f"and should be checked."
                ),
            }
        )

    if gas_level >= device.gas_critical_threshold:
        issues.append(
            {
                "type": "gas",
                "severity": "critical",
                "message": (
                    f"Room {room.room_number} gas concentration reached {gas_level} ppm. "
                    f"Immediate HSE response is recommended."
                ),
            }
        )
    elif gas_level >= device.gas_warning_threshold:
        issues.append(
            {
                "type": "gas",
                "severity": "warning",
                "message": (
                    f"Room {room.room_number} gas concentration is {gas_level} ppm, above the warning threshold."
                ),
            }
        )

    if not occupancy_expected and motion_state == "tamper":
        issues.append(
            {
                "type": "motion",
                "severity": "critical",
                "message": (
                    f"Tamper-level motion was detected in Room {room.room_number} while it should be secured."
                ),
            }
        )
    elif not occupancy_expected and motion_state == "active":
        issues.append(
            {
                "type": "motion",
                "severity": "warning",
                "message": (
                    f"Unexpected activity was detected in Room {room.room_number}. "
                    f"Front desk or security should confirm the room condition."
                ),
            }
        )
    elif occupancy_expected and motion_state == "tamper":
        issues.append(
            {
                "type": "motion",
                "severity": "warning",
                "message": (
                    f"Forceful motion signature was detected in occupied Room {room.room_number}. "
                    f"Please verify guest safety."
                ),
            }
        )

    if any(issue["severity"] == "critical" for issue in issues):
        overall_status = "critical"
    elif issues:
        overall_status = "warning"
    else:
        overall_status = "normal"

    return overall_status, issues


@transaction.atomic
def record_sensor_payload(device, payload, *, simulated=True):
    overall_status, issues = evaluate_payload(device, payload)
    reading = SensorReading.objects.create(
        device=device,
        room=device.room,
        temperature_c=payload["temperature_c"],
        gas_level=payload["gas_level"],
        motion_state=payload["motion_state"],
        occupancy_expected=payload["occupancy_expected"],
        overall_status=overall_status,
        issues=issues,
        simulated=simulated,
        recorded_at=payload.get("recorded_at") or timezone.now(),
    )

    device.last_seen_at = reading.recorded_at
    device.is_online = True
    device.save(update_fields=["last_seen_at", "is_online", "updated_at"])

    sync_alerts_for_reading(device, reading)
    return reading


def sync_alerts_for_reading(device, reading):
    active_alerts = _active_alert_map(device)
    active_issue_types = set()

    for issue in reading.issues:
        alert_type = issue["type"]
        active_issue_types.add(alert_type)
        title, _ = ALERT_COPY[alert_type][issue["severity"]]
        alert = active_alerts.get(alert_type)
        if alert:
            previous_severity = alert.severity
            alert.severity = issue["severity"]
            alert.title = title
            alert.message = issue["message"]
            alert.latest_reading = reading
            update_fields = ["severity", "title", "message", "latest_reading", "updated_at"]
            if previous_severity != issue["severity"] and issue["severity"] == "critical":
                alert.acknowledged_at = None
                alert.acknowledged_by = None
                update_fields.extend(["acknowledged_at", "acknowledged_by"])
            alert.save(update_fields=update_fields)
        else:
            RoomConditionAlert.objects.create(
                room=device.room,
                device=device,
                latest_reading=reading,
                alert_type=alert_type,
                severity=issue["severity"],
                title=title,
                message=issue["message"],
            )

    for alert_type, alert in active_alerts.items():
        if alert_type in active_issue_types:
            continue
        alert.is_active = False
        alert.resolved_at = reading.recorded_at
        alert.latest_reading = reading
        alert.save(update_fields=["is_active", "resolved_at", "latest_reading", "updated_at"])


def refresh_simulated_readings(*, force=False, now=None):
    now = now or timezone.now()
    devices = ensure_iot_devices()
    if not devices:
        return []

    latest_by_device = {}
    for reading in SensorReading.objects.filter(device__in=devices).order_by("device_id", "-recorded_at"):
        latest_by_device.setdefault(reading.device_id, reading)

    refreshed = []
    for device in devices:
        latest = latest_by_device.get(device.id)
        is_stale = not latest or (now - latest.recorded_at) >= timedelta(seconds=max(device.sampling_interval_seconds, 15))
        if not device.simulation_enabled or not (force or is_stale):
            continue
        payload = simulate_device_payload(device, now=now, latest_reading=latest)
        refreshed.append(record_sensor_payload(device, payload))
    return refreshed


def _format_issue_types(issues):
    return [issue["type"] for issue in issues]


def build_monitoring_snapshot(*, force_refresh=False):
    devices = ensure_iot_devices()
    if force_refresh:
        refresh_simulated_readings(force=True)
        devices = ensure_iot_devices()
    else:
        refresh_simulated_readings(force=False)

    devices = list(IoTDevice.objects.select_related("room").order_by("room__floor", "room__room_number"))
    if not devices:
        return {
            "generated_at": timezone.now(),
            "summary": {
                "rooms_monitored": 0,
                "normal_rooms": 0,
                "warning_rooms": 0,
                "critical_rooms": 0,
                "active_alerts": 0,
                "acknowledged_alerts": 0,
            },
            "rooms": [],
            "alerts": [],
        }

    room_ids = [device.room_id for device in devices]
    device_ids = [device.id for device in devices]

    readings_by_device = defaultdict(list)
    for reading in SensorReading.objects.filter(device_id__in=device_ids).order_by("device_id", "-recorded_at"):
        if len(readings_by_device[reading.device_id]) < 12:
            readings_by_device[reading.device_id].append(reading)

    alerts = list(
        RoomConditionAlert.objects.select_related("room", "device", "latest_reading", "acknowledged_by")
        .filter(device_id__in=device_ids)
        .order_by("-is_active", "-triggered_at")
    )

    active_alerts_by_room = defaultdict(list)
    for alert in alerts:
        if alert.is_active:
            active_alerts_by_room[alert.room_id].append(alert)

    room_cards = []
    status_counter = defaultdict(int)

    for device in devices:
        history = readings_by_device.get(device.id, [])
        latest = history[0] if history else None
        room_alerts = active_alerts_by_room.get(device.room_id, [])
        status = latest.overall_status if latest else "normal"
        status_counter[status] += 1

        room_cards.append(
            {
                "room_id": device.room_id,
                "room_number": device.room.room_number,
                "floor": device.room.floor,
                "room_type": device.room.get_room_type_display(),
                "room_status": device.room.status,
                "housekeeping_status": device.room.housekeeping_status,
                "device_identifier": device.device_identifier,
                "status": status,
                "temperature_c": latest.temperature_c if latest else None,
                "gas_level": latest.gas_level if latest else None,
                "motion_state": latest.motion_state if latest else "idle",
                "occupancy_expected": latest.occupancy_expected if latest else room_expected_occupancy(device.room),
                "issues": latest.issues if latest else [],
                "issue_types": _format_issue_types(latest.issues) if latest else [],
                "last_seen_at": device.last_seen_at,
                "history_labels": [timezone.localtime(reading.recorded_at).strftime("%H:%M:%S") for reading in reversed(history)],
                "history_temperature": [reading.temperature_c for reading in reversed(history)],
                "history_gas": [reading.gas_level for reading in reversed(history)],
                "history_motion": [reading.motion_state for reading in reversed(history)],
                "active_alerts": [
                    {
                        "id": alert.id,
                        "type": alert.alert_type,
                        "severity": alert.severity,
                        "title": alert.title,
                        "message": alert.message,
                        "acknowledged": bool(alert.acknowledged_at),
                    }
                    for alert in room_alerts
                ],
            }
        )

    active_alerts = [alert for alert in alerts if alert.is_active]
    acknowledged_alerts = [alert for alert in active_alerts if alert.acknowledged_at]

    return {
        "generated_at": timezone.now(),
        "summary": {
            "rooms_monitored": len(room_ids),
            "normal_rooms": status_counter["normal"],
            "warning_rooms": status_counter["warning"],
            "critical_rooms": status_counter["critical"],
            "active_alerts": len(active_alerts),
            "acknowledged_alerts": len(acknowledged_alerts),
        },
        "rooms": room_cards,
        "alerts": [
            {
                "id": alert.id,
                "room_number": alert.room.room_number,
                "severity": alert.severity,
                "alert_type": alert.alert_type,
                "title": alert.title,
                "message": alert.message,
                "is_active": alert.is_active,
                "acknowledged": bool(alert.acknowledged_at),
                "acknowledged_by": alert.acknowledged_by.get_full_name() if alert.acknowledged_by else "",
                "triggered_at": timezone.localtime(alert.triggered_at).strftime("%b %d, %Y %H:%M"),
                "resolved_at": timezone.localtime(alert.resolved_at).strftime("%b %d, %Y %H:%M") if alert.resolved_at else "",
                "last_notified_at": (
                    timezone.localtime(alert.last_notified_at).strftime("%b %d, %Y %H:%M")
                    if alert.last_notified_at
                    else ""
                ),
                "notification_count": alert.notification_count,
            }
            for alert in alerts[:30]
        ],
    }


def acknowledge_alert(alert, user):
    if not alert.acknowledged_at:
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = user
        alert.save(update_fields=["acknowledged_at", "acknowledged_by", "updated_at"])
    return alert


def resolve_alert(alert):
    if alert.is_active:
        alert.is_active = False
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["is_active", "resolved_at", "updated_at"])
    return alert
