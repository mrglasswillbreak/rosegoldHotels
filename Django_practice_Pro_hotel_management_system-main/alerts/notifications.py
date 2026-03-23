import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import AlertNotification, RoomConditionAlert


logger = logging.getLogger(__name__)

SEVERITY_RANK = {"warning": 1, "critical": 2}


def _normalize_phone_number(value):
    if not value:
        return ""
    cleaned = "".join(char for char in str(value).strip() if char.isdigit() or char == "+")
    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"
    return cleaned


def get_notification_recipients():
    user_model = get_user_model()
    staff_users = user_model.objects.filter(is_staff=True, is_active=True).only("email", "phone_number")

    emails = {
        user.email.strip().lower()
        for user in staff_users
        if user.email and user.email.strip()
    }
    phones = {
        _normalize_phone_number(user.phone_number)
        for user in staff_users
        if _normalize_phone_number(user.phone_number)
    }

    emails.update(
        email.strip().lower()
        for email in getattr(settings, "IOT_ALERT_EXTRA_EMAIL_RECIPIENTS", [])
        if str(email).strip()
    )
    phones.update(
        _normalize_phone_number(phone)
        for phone in getattr(settings, "IOT_ALERT_EXTRA_SMS_RECIPIENTS", [])
        if _normalize_phone_number(phone)
    )

    return {
        "emails": sorted(emails),
        "phones": sorted(phones),
    }


def _build_notification_copy(alert, event_type):
    reading = alert.latest_reading
    status_phrase = {
        "triggered": "A new room condition alert has been triggered.",
        "escalated": "An existing room condition alert has escalated and needs urgent attention.",
        "reminder": "This alert is still active and has not been fully resolved.",
        "resolved": "The room condition has returned to normal and the alert has been resolved.",
    }[event_type]

    subject_prefix = "RESOLVED" if event_type == "resolved" else alert.severity.upper()
    subject = f"[HSE {subject_prefix}] Room {alert.room.room_number} - {alert.title}"

    lines = [
        f"Room: {alert.room.room_number}",
        f"Severity: {alert.get_severity_display()}",
        f"Alert Type: {alert.get_alert_type_display()}",
        f"Status: {status_phrase}",
        "",
        alert.message,
    ]

    if reading:
        lines.extend(
            [
                "",
                "Latest sensor snapshot:",
                f"- Temperature: {reading.temperature_c}C",
                f"- Gas concentration: {reading.gas_level} ppm",
                f"- Motion state: {reading.get_motion_state_display()}",
                f"- Expected occupancy: {'Yes' if reading.occupancy_expected else 'No'}",
                f"- Recorded at: {timezone.localtime(reading.recorded_at).strftime('%b %d, %Y %H:%M:%S')}",
            ]
        )

    lines.extend(
        [
            "",
            "Monitoring center: /monitoring/iot/",
            "Alert center: /monitoring/alerts/",
        ]
    )
    return subject, "\n".join(lines)


def _send_email_notification(recipient, subject, message):
    try:
        sent_count = send_mail(
            subject,
            message,
            getattr(settings, "DEFAULT_FROM_EMAIL", "alerts@rosegoldhotel.local"),
            [recipient],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Email notification failed for %s", recipient)
        return {
            "status": "failed",
            "provider": "django-email",
            "provider_reference": "",
            "error_message": str(exc),
        }

    if sent_count:
        return {
            "status": "sent",
            "provider": "django-email",
            "provider_reference": "",
            "error_message": "",
        }

    return {
        "status": "failed",
        "provider": "django-email",
        "provider_reference": "",
        "error_message": "Email backend reported zero delivered messages.",
    }


def _send_sms_notification(recipient, message):
    backend = getattr(settings, "IOT_ALERT_SMS_BACKEND", "console").strip().lower()
    if backend == "twilio":
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        from_number = getattr(settings, "TWILIO_FROM_NUMBER", "")
        if not all([account_sid, auth_token, from_number]):
            return {
                "status": "failed",
                "provider": "twilio",
                "provider_reference": "",
                "error_message": "Twilio credentials are not configured.",
            }
        try:
            from twilio.rest import Client
        except ImportError:
            return {
                "status": "failed",
                "provider": "twilio",
                "provider_reference": "",
                "error_message": "Twilio package is not installed.",
            }

        try:
            client = Client(account_sid, auth_token)
            sms = client.messages.create(body=message, from_=from_number, to=recipient)
        except Exception as exc:
            logger.exception("SMS notification failed for %s", recipient)
            return {
                "status": "failed",
                "provider": "twilio",
                "provider_reference": "",
                "error_message": str(exc),
            }

        return {
            "status": "sent",
            "provider": "twilio",
            "provider_reference": getattr(sms, "sid", ""),
            "error_message": "",
        }

    logger.info("Simulated SMS alert to %s: %s", recipient, message)
    return {
        "status": "simulated",
        "provider": backend or "console",
        "provider_reference": "",
        "error_message": "",
    }


def _create_notification_log(alert, channel, event_type, recipient, severity, subject, message, result):
    return AlertNotification.objects.create(
        alert=alert,
        channel=channel,
        event_type=event_type,
        recipient=recipient,
        severity=severity,
        subject=subject,
        message=message,
        provider=result["provider"],
        provider_reference=result["provider_reference"],
        status=result["status"],
        error_message=result["error_message"],
        sent_at=timezone.now() if result["status"] in {"sent", "simulated"} else None,
    )


def _determine_event_type(alert, now):
    if alert.is_active:
        if not alert.last_notified_at:
            return "triggered"
        previous_rank = SEVERITY_RANK.get(alert.last_notified_severity or "", 0)
        current_rank = SEVERITY_RANK.get(alert.severity, 0)
        if current_rank > previous_rank:
            return "escalated"
        reminder_after = timedelta(minutes=getattr(settings, "IOT_ALERT_REMINDER_MINUTES", 10))
        if not alert.acknowledged_at and alert.last_notified_at <= now - reminder_after:
            return "reminder"
        return ""

    if alert.resolved_at and not alert.resolution_notified_at and alert.notification_count:
        return "resolved"
    return ""


def dispatch_pending_alert_notifications():
    now = timezone.now()
    recipients = get_notification_recipients()
    summary = {
        "processed_alerts": 0,
        "notifications_sent": 0,
        "notifications_failed": 0,
        "channels_used": set(),
    }

    alerts = RoomConditionAlert.objects.select_related("room", "device", "latest_reading").order_by("-is_active", "-triggered_at")

    for alert in alerts:
        event_type = _determine_event_type(alert, now)
        if not event_type:
            continue

        summary["processed_alerts"] += 1
        subject, message = _build_notification_copy(alert, event_type)
        successful_deliveries = 0

        if getattr(settings, "IOT_ALERT_EMAIL_ENABLED", True):
            for email in recipients["emails"]:
                result = _send_email_notification(email, subject, message)
                _create_notification_log(alert, "email", event_type, email, alert.severity, subject, message, result)
                if result["status"] in {"sent", "simulated"}:
                    successful_deliveries += 1
                    summary["notifications_sent"] += 1
                    summary["channels_used"].add("email")
                else:
                    summary["notifications_failed"] += 1

        if getattr(settings, "IOT_ALERT_SMS_ENABLED", True):
            sms_message = f"{subject}\n{alert.message}"
            for phone in recipients["phones"]:
                result = _send_sms_notification(phone, sms_message)
                _create_notification_log(alert, "sms", event_type, phone, alert.severity, subject, sms_message, result)
                if result["status"] in {"sent", "simulated"}:
                    successful_deliveries += 1
                    summary["notifications_sent"] += 1
                    summary["channels_used"].add("sms")
                else:
                    summary["notifications_failed"] += 1

        if not successful_deliveries:
            continue

        if event_type == "resolved":
            alert.resolution_notified_at = now
            alert.save(update_fields=["resolution_notified_at", "updated_at"])
        else:
            alert.last_notified_at = now
            alert.last_notified_severity = alert.severity
            alert.notification_count += 1
            alert.save(update_fields=["last_notified_at", "last_notified_severity", "notification_count", "updated_at"])

    summary["channels_used"] = sorted(summary["channels_used"])
    return summary
