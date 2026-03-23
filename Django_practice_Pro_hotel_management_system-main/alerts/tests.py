from datetime import timedelta
import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from HotelApp.models import Room

from .models import AlertNotification, IoTDevice, RoomConditionAlert, SensorReading
from .notifications import dispatch_pending_alert_notifications
from .services import build_monitoring_snapshot, ensure_iot_devices, evaluate_payload, record_sensor_payload, simulate_device_payload


@override_settings(
    STATIC_ROOT=tempfile.mkdtemp(prefix="alerts-static-root-"),
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    IOT_ALERT_SMS_BACKEND="console",
    IOT_MONITOR_AUTOSTART=False,
)
class IoTMonitoringTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email="hse-admin@example.com",
            password="AdminPass123!",
            phone_number="+2348011111111",
        )
        self.guest_user = get_user_model().objects.create_user(
            email="guest-monitor@example.com",
            password="GuestPass123!",
        )
        self.room = Room.objects.create(
            room_number="H401",
            room_type="double",
            floor=4,
            facility="WiFi, Smart Lock",
            price="35000.00",
            status="available",
        )

    def test_staff_can_view_iot_monitoring_dashboard(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("iot_monitoring_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IoT Room Monitoring")
        self.assertContains(response, self.room.room_number)

    def test_non_staff_users_cannot_access_iot_monitoring_dashboard(self):
        self.client.force_login(self.guest_user)

        response = self.client.get(reverse("iot_monitoring_dashboard"))

        self.assertRedirects(response, reverse("user_home"))

    def test_snapshot_generation_creates_devices_and_readings(self):
        snapshot = build_monitoring_snapshot(force_refresh=True)

        self.assertEqual(snapshot["summary"]["rooms_monitored"], Room.objects.count())
        self.assertTrue(IoTDevice.objects.filter(room=self.room).exists())
        self.assertTrue(SensorReading.objects.filter(room=self.room).exists())

    def test_abnormal_reading_creates_and_resolves_alert(self):
        ensure_iot_devices()
        device = IoTDevice.objects.get(room=self.room)
        abnormal_payload = {
            "temperature_c": 23.4,
            "gas_level": 140,
            "motion_state": "idle",
            "occupancy_expected": False,
            "recorded_at": timezone.now(),
        }

        record_sensor_payload(device, abnormal_payload)

        alert = RoomConditionAlert.objects.get(room=self.room, alert_type="gas")
        self.assertTrue(alert.is_active)
        self.assertEqual(alert.severity, "critical")

        normal_payload = {
            "temperature_c": 22.0,
            "gas_level": 18,
            "motion_state": "idle",
            "occupancy_expected": False,
            "recorded_at": timezone.now() + timedelta(minutes=1),
        }
        record_sensor_payload(device, normal_payload)

        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
        self.assertIsNotNone(alert.resolved_at)

    def test_admin_can_acknowledge_alert(self):
        ensure_iot_devices()
        device = IoTDevice.objects.get(room=self.room)
        record_sensor_payload(
            device,
            {
                "temperature_c": 32.5,
                "gas_level": 10,
                "motion_state": "idle",
                "occupancy_expected": False,
                "recorded_at": timezone.now(),
            },
        )
        alert = RoomConditionAlert.objects.get(room=self.room, alert_type="temperature")
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse("acknowledge_iot_alert", args=[alert.id]))

        self.assertRedirects(response, reverse("iot_alert_center"))
        alert.refresh_from_db()
        self.assertIsNotNone(alert.acknowledged_at)
        self.assertEqual(alert.acknowledged_by, self.admin_user)

    def test_alert_notifications_are_logged_for_email_and_sms(self):
        ensure_iot_devices()
        device = IoTDevice.objects.get(room=self.room)
        record_sensor_payload(
            device,
            {
                "temperature_c": 33.1,
                "gas_level": 12,
                "motion_state": "idle",
                "occupancy_expected": False,
                "recorded_at": timezone.now(),
            },
        )

        summary = dispatch_pending_alert_notifications()

        alert = RoomConditionAlert.objects.get(room=self.room, alert_type="temperature")
        alert.refresh_from_db()
        self.assertEqual(summary["notifications_sent"], 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AlertNotification.objects.filter(alert=alert, channel="email").count(), 1)
        self.assertEqual(AlertNotification.objects.filter(alert=alert, channel="sms").count(), 1)
        self.assertEqual(alert.notification_count, 1)
        self.assertIsNotNone(alert.last_notified_at)

    def test_resolved_alert_sends_resolution_notification(self):
        ensure_iot_devices()
        device = IoTDevice.objects.get(room=self.room)
        record_sensor_payload(
            device,
            {
                "temperature_c": 33.2,
                "gas_level": 10,
                "motion_state": "idle",
                "occupancy_expected": False,
                "recorded_at": timezone.now(),
            },
        )
        dispatch_pending_alert_notifications()
        alert = RoomConditionAlert.objects.get(room=self.room, alert_type="temperature")

        record_sensor_payload(
            device,
            {
                "temperature_c": 22.4,
                "gas_level": 10,
                "motion_state": "idle",
                "occupancy_expected": False,
                "recorded_at": timezone.now() + timedelta(minutes=1),
            },
        )
        dispatch_pending_alert_notifications()

        alert.refresh_from_db()
        self.assertIsNotNone(alert.resolution_notified_at)
        self.assertTrue(
            AlertNotification.objects.filter(alert=alert, event_type="resolved", channel="email").exists()
        )

    def test_run_iot_monitor_command_executes_single_cycle(self):
        call_command("run_iot_monitor", once=True, verbosity=0)

        self.assertTrue(SensorReading.objects.filter(room=self.room).exists())

    @override_settings(IOT_SIM_ABNORMAL_ROOM_RATE=0.20)
    def test_default_simulation_rate_stays_near_twenty_percent(self):
        ensure_iot_devices()
        device = IoTDevice.objects.get(room=self.room)
        abnormal_count = 0
        total_samples = 120

        for offset in range(total_samples):
            sample_time = timezone.now() + timedelta(minutes=offset * 2)
            payload = simulate_device_payload(device, now=sample_time, latest_reading=None)
            overall_status, _ = evaluate_payload(device, payload)
            if overall_status != "normal":
                abnormal_count += 1

        abnormal_rate = abnormal_count / total_samples
        self.assertGreaterEqual(abnormal_rate, 0.12)
        self.assertLessEqual(abnormal_rate, 0.30)
