import json
from datetime import timedelta
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from HotelApp.models import Room

from .models import AlertNotification, RoomConditionAlert, SensorReading
from .runtime import run_monitoring_cycle
from .services import (
    acknowledge_alert,
    build_monitoring_snapshot,
    ensure_iot_devices,
    record_sensor_payload,
    resolve_alert,
)


def monitoring_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("author_login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        if not request.user.is_staff:
            messages.error(request, "You do not have permission to access the HSE monitoring center.")
            return redirect("user_home")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def build_monitoring_context(active_admin_section, **context):
    context["active_admin_section"] = active_admin_section
    return context


def serialize_snapshot(snapshot):
    serialized_rooms = []
    for room in snapshot["rooms"]:
        serialized_rooms.append(
            {
                **room,
                "last_seen_at": timezone.localtime(room["last_seen_at"]).strftime("%b %d, %H:%M:%S")
                if room["last_seen_at"]
                else "No reading yet",
            }
        )

    return {
        "generated_at": timezone.localtime(snapshot["generated_at"]).strftime("%b %d, %Y %H:%M:%S"),
        "summary": snapshot["summary"],
        "rooms": serialized_rooms,
        "alerts": snapshot["alerts"],
    }


def _resolve_room_from_reference(room_reference):
    if not room_reference:
        return None
    raw_value = str(room_reference).strip()
    normalized = raw_value.lower().replace("room", "").strip()
    return Room.objects.filter(room_number=normalized).first()


def _normalize_motion_state(value):
    normalized = str(value or "idle").strip().lower()
    mapping = {
        "idle": "idle",
        "normal": "brief",
        "brief": "brief",
        "busy": "active",
        "active": "active",
        "critical": "tamper",
        "tamper": "tamper",
    }
    return mapping.get(normalized, "idle")


def _normalize_gas_level(raw_value, device):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return 0

    if value <= 2:
        mapping = {
            0: 12,
            1: device.gas_warning_threshold + 5,
            2: device.gas_critical_threshold + 10,
        }
        return mapping[value]
    return max(value, 0)


def _compat_gas_signal(reading):
    if reading.gas_level >= reading.device.gas_critical_threshold:
        return 2
    if reading.gas_level >= reading.device.gas_warning_threshold:
        return 1
    return 0


def _compat_motion_state(reading):
    mapping = {
        "idle": "Idle",
        "brief": "Normal",
        "active": "Busy",
        "tamper": "Critical",
    }
    return mapping.get(reading.motion_state, "Idle")


@monitoring_admin_required
def iot_monitoring_dashboard(request):
    run_monitoring_cycle(force_refresh=request.GET.get("refresh") == "1")
    snapshot = build_monitoring_snapshot(force_refresh=False)
    serialized_snapshot = serialize_snapshot(snapshot)

    context = build_monitoring_context(
        "iot_monitoring",
        monitoring_snapshot=serialized_snapshot,
        monitoring_snapshot_json=json.dumps(serialized_snapshot),
        summary=serialized_snapshot["summary"],
        rooms=serialized_snapshot["rooms"],
        recent_alerts=serialized_snapshot["alerts"][:8],
        generated_at=serialized_snapshot["generated_at"],
    )
    return render(request, "admin/IoTMonitoring.html", context)


@require_GET
@monitoring_admin_required
def iot_monitoring_feed(request):
    run_monitoring_cycle(force_refresh=request.GET.get("refresh") == "1")
    snapshot = build_monitoring_snapshot(force_refresh=False)
    return JsonResponse(serialize_snapshot(snapshot))


@require_POST
@monitoring_admin_required
def force_simulation_cycle(request):
    run_monitoring_cycle(force_refresh=True)
    snapshot = serialize_snapshot(build_monitoring_snapshot(force_refresh=False))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": "Simulation refreshed.", "snapshot": snapshot})

    messages.success(request, "Fresh IoT sensor readings generated successfully.")
    return redirect("iot_monitoring_dashboard")


@monitoring_admin_required
def iot_alert_center(request):
    run_monitoring_cycle(force_refresh=False)

    status_filter = request.GET.get("status", "active").strip()
    severity_filter = request.GET.get("severity", "").strip()
    room_filter = request.GET.get("room", "").strip()

    alerts = RoomConditionAlert.objects.select_related(
        "room", "device", "latest_reading", "acknowledged_by"
    ).order_by("-is_active", "-triggered_at")

    if status_filter == "active":
        alerts = alerts.filter(is_active=True)
    elif status_filter == "resolved":
        alerts = alerts.filter(is_active=False)

    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)
    if room_filter:
        alerts = alerts.filter(room__room_number__icontains=room_filter)

    snapshot = serialize_snapshot(build_monitoring_snapshot(force_refresh=False))
    notification_window_start = timezone.now() - timedelta(hours=24)
    recent_notifications = AlertNotification.objects.select_related("alert", "alert__room").order_by("-created_at")[:30]
    notification_summary = {
        "total": AlertNotification.objects.filter(created_at__gte=notification_window_start).count(),
        "email": AlertNotification.objects.filter(created_at__gte=notification_window_start, channel="email").count(),
        "sms": AlertNotification.objects.filter(created_at__gte=notification_window_start, channel="sms").count(),
        "failed": AlertNotification.objects.filter(created_at__gte=notification_window_start, status="failed").count(),
    }
    context = build_monitoring_context(
        "iot_alert_center",
        alerts=alerts[:100],
        summary=snapshot["summary"],
        status_filter=status_filter,
        severity_filter=severity_filter,
        room_filter=room_filter,
        recent_notifications=recent_notifications,
        notification_summary=notification_summary,
    )
    return render(request, "admin/IoTAlertCenter.html", context)


@require_POST
@monitoring_admin_required
def acknowledge_iot_alert(request, alert_id):
    alert = get_object_or_404(RoomConditionAlert, pk=alert_id)
    acknowledge_alert(alert, request.user)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": f"Alert for Room {alert.room.room_number} acknowledged."})

    messages.success(request, f"Alert for Room {alert.room.room_number} acknowledged.")
    return redirect(request.POST.get("next") or "iot_alert_center")


@require_POST
@monitoring_admin_required
def resolve_iot_alert(request, alert_id):
    alert = get_object_or_404(RoomConditionAlert, pk=alert_id)
    resolve_alert(alert)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"message": f"Alert for Room {alert.room.room_number} marked as resolved."})

    messages.success(request, f"Alert for Room {alert.room.room_number} marked as resolved.")
    return redirect(request.POST.get("next") or "iot_alert_center")


@csrf_exempt
@require_POST
def receive_iot_data(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    room = _resolve_room_from_reference(data.get("room"))
    if not room:
        return JsonResponse({"error": "Room not found."}, status=404)

    device = next((item for item in ensure_iot_devices(Room.objects.filter(pk=room.pk)) if item.room_id == room.id), None)
    if device is None:
        return JsonResponse({"error": "Unable to provision room device."}, status=500)

    try:
        temperature_value = float(data.get("temperature", data.get("temperature_c", 0)) or 0)
    except (TypeError, ValueError):
        temperature_value = 0

    payload = {
        "temperature_c": temperature_value,
        "gas_level": _normalize_gas_level(data.get("gas", data.get("gas_level", 0)), device),
        "motion_state": _normalize_motion_state(data.get("motion", data.get("motion_state", "idle"))),
        "occupancy_expected": data.get("occupancy_expected", room.status == "occupied"),
        "recorded_at": timezone.now(),
    }
    reading = record_sensor_payload(device, payload, simulated=True)

    return JsonResponse(
        {
            "message": "stored",
            "room": f"Room {room.room_number}",
            "status": reading.overall_status,
            "issues": reading.issues,
        }
    )


@require_GET
def get_iot_data(request):
    readings = SensorReading.objects.select_related("room").order_by("-recorded_at")[:100]

    result = [
        {
            "room": f"Room {reading.room.room_number}",
            "temperature": reading.temperature_c,
            "gas": _compat_gas_signal(reading),
            "gas_ppm": reading.gas_level,
            "motion": _compat_motion_state(reading),
            "status": reading.overall_status.upper(),
            "timestamp": timezone.localtime(reading.recorded_at).strftime("%H:%M:%S"),
        }
        for reading in readings
    ]

    return JsonResponse(result, safe=False)
