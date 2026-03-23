from django.conf import settings
from django.db import models
from django.utils import timezone

from HotelApp.models import Room


class IoTDevice(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name="iot_device")
    device_identifier = models.CharField(max_length=50, unique=True)
    is_online = models.BooleanField(default=True)
    simulation_enabled = models.BooleanField(default=True)
    temperature_min_normal = models.FloatField(default=20.0)
    temperature_max_normal = models.FloatField(default=27.5)
    gas_warning_threshold = models.PositiveIntegerField(default=70)
    gas_critical_threshold = models.PositiveIntegerField(default=120)
    sampling_interval_seconds = models.PositiveIntegerField(default=45)
    installed_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["room__floor", "room__room_number"]

    def __str__(self):
        return f"{self.device_identifier} - Room {self.room.room_number}"


class SensorReading(models.Model):
    STATUS_CHOICES = [
        ("normal", "Normal"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    MOTION_STATE_CHOICES = [
        ("idle", "Idle"),
        ("brief", "Brief Movement"),
        ("active", "Active Movement"),
        ("tamper", "Tamper / Forced Entry"),
    ]

    device = models.ForeignKey(IoTDevice, on_delete=models.CASCADE, related_name="readings")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="sensor_readings")
    temperature_c = models.FloatField()
    gas_level = models.PositiveIntegerField(help_text="Simulated gas concentration in ppm.")
    motion_state = models.CharField(max_length=20, choices=MOTION_STATE_CHOICES, default="idle")
    occupancy_expected = models.BooleanField(default=False)
    overall_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="normal", db_index=True)
    issues = models.JSONField(default=list, blank=True)
    simulated = models.BooleanField(default=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"Room {self.room.room_number} {self.overall_status} at {self.recorded_at:%Y-%m-%d %H:%M:%S}"


class RoomConditionAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ("temperature", "Temperature"),
        ("gas", "Gas Leakage"),
        ("motion", "Unexpected Motion"),
        ("device", "Device Health"),
    ]

    SEVERITY_CHOICES = [
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="condition_alerts")
    device = models.ForeignKey(IoTDevice, on_delete=models.CASCADE, related_name="alerts")
    latest_reading = models.ForeignKey(
        SensorReading,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_alerts",
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, db_index=True)
    title = models.CharField(max_length=140)
    message = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    triggered_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_room_alerts",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    last_notified_at = models.DateTimeField(blank=True, null=True, db_index=True)
    resolution_notified_at = models.DateTimeField(blank=True, null=True)
    last_notified_severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, blank=True)
    notification_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-triggered_at"]

    def __str__(self):
        state = "Active" if self.is_active else "Resolved"
        return f"{self.get_alert_type_display()} {self.get_severity_display()} - Room {self.room.room_number} ({state})"


class AlertNotification(models.Model):
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    EVENT_TYPE_CHOICES = [
        ("triggered", "Triggered"),
        ("escalated", "Escalated"),
        ("reminder", "Reminder"),
        ("resolved", "Resolved"),
    ]

    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("simulated", "Simulated"),
        ("failed", "Failed"),
    ]

    alert = models.ForeignKey(RoomConditionAlert, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, db_index=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, db_index=True)
    recipient = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=RoomConditionAlert.SEVERITY_CHOICES)
    subject = models.CharField(max_length=180)
    message = models.TextField()
    provider = models.CharField(max_length=40, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="simulated", db_index=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_channel_display()} {self.get_event_type_display()} to {self.recipient}"
