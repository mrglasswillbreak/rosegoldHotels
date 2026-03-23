from django.contrib import admin

from .models import AlertNotification, IoTDevice, RoomConditionAlert, SensorReading


@admin.register(IoTDevice)
class IoTDeviceAdmin(admin.ModelAdmin):
    list_display = ("device_identifier", "room", "is_online", "simulation_enabled", "last_seen_at")
    list_filter = ("is_online", "simulation_enabled", "room__status")
    search_fields = ("device_identifier", "room__room_number")


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ("room", "overall_status", "temperature_c", "gas_level", "motion_state", "recorded_at")
    list_filter = ("overall_status", "motion_state", "simulated")
    search_fields = ("room__room_number", "device__device_identifier")
    ordering = ("-recorded_at",)


@admin.register(RoomConditionAlert)
class RoomConditionAlertAdmin(admin.ModelAdmin):
    list_display = (
        "room",
        "alert_type",
        "severity",
        "is_active",
        "acknowledged_at",
        "last_notified_at",
        "notification_count",
        "triggered_at",
    )
    list_filter = ("alert_type", "severity", "is_active")
    search_fields = ("room__room_number", "title", "message")
    ordering = ("-is_active", "-triggered_at")


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ("alert", "channel", "event_type", "recipient", "status", "created_at")
    list_filter = ("channel", "event_type", "status", "severity")
    search_fields = ("recipient", "subject", "message", "alert__room__room_number")
    ordering = ("-created_at",)
