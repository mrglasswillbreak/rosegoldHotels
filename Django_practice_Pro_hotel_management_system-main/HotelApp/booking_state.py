from __future__ import annotations

from uuid import uuid4

from django.utils import timezone

from .models import OfflineBooking, OnlineBooking, Room


CONFLICT_BOOKING_STATUSES = ("pending", "confirmed", "checked_in")
RESERVED_BOOKING_STATUSES = ("confirmed",)
OCCUPIED_BOOKING_STATUSES = ("checked_in",)


def generate_payment_reference(prefix: str = "PST") -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}-{uuid4().hex[:8].upper()}"


def sync_room_status(room: Room) -> str:
    has_checked_in_booking = (
        OnlineBooking.objects.filter(room=room, status__in=OCCUPIED_BOOKING_STATUSES).exists()
        or OfflineBooking.objects.filter(room=room, status__in=OCCUPIED_BOOKING_STATUSES).exists()
    )
    if has_checked_in_booking:
        new_status = "occupied"
    elif room.status == "maintenance":
        new_status = "maintenance"
    else:
        has_reserved_booking = (
            OnlineBooking.objects.filter(room=room, status__in=RESERVED_BOOKING_STATUSES).exists()
            or OfflineBooking.objects.filter(room=room, status__in=RESERVED_BOOKING_STATUSES).exists()
        )
        new_status = "reserved" if has_reserved_booking else "available"

    if room.status != new_status:
        room.status = new_status
        room.save(update_fields=["status"])

    return new_status
