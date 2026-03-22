from django.db import migrations

DEFAULT_ROOMS = [
    {
        "room_number": "101",
        "room_type": "single",
        "floor": 1,
        "facility": "WiFi, AC, TV, Single Bed",
        "price": "15000.00",
        "status": "available",
    },
    {
        "room_number": "102",
        "room_type": "single",
        "floor": 1,
        "facility": "WiFi, AC, TV, Single Bed",
        "price": "18000.00",
        "status": "occupied",
    },
    {
        "room_number": "201",
        "room_type": "double",
        "floor": 2,
        "facility": "WiFi, AC, TV, Mini Bar, Two Beds",
        "price": "35000.00",
        "status": "available",
    },
    {
        "room_number": "202",
        "room_type": "double",
        "floor": 2,
        "facility": "WiFi, AC, TV, Mini Bar, Balcony",
        "price": "42000.00",
        "status": "available",
    },
    {
        "room_number": "301",
        "room_type": "suite",
        "floor": 3,
        "facility": "WiFi, AC, TV, Jacuzzi, King Bed, Living Room",
        "price": "85000.00",
        "status": "available",
    },
    {
        "room_number": "302",
        "room_type": "suite",
        "floor": 3,
        "facility": "WiFi, AC, TV, Private Pool, Butler Service",
        "price": "120000.00",
        "status": "maintenance",
    },
    {
        "room_number": "203",
        "room_type": "double",
        "floor": 2,
        "facility": "WiFi, AC, Smart TV, Mini Bar, City View",
        "price": "60000.00",
        "status": "available",
    },
    {
        "room_number": "303",
        "room_type": "suite",
        "floor": 3,
        "facility": "WiFi, AC, Jacuzzi, King Bed, Ocean View",
        "price": "95000.00",
        "status": "available",
    },
    {
        "room_number": "103",
        "room_type": "single",
        "floor": 1,
        "facility": "WiFi, AC, TV, Work Desk",
        "price": "16000.00",
        "status": "occupied",
    },
    {
        "room_number": "104",
        "room_type": "single",
        "floor": 1,
        "facility": "WiFi, AC, TV, Garden View",
        "price": "20000.00",
        "status": "available",
    },
]

def seed_initial_rooms(apps, schema_editor):
    """Backfill the original room inventory without duplicating existing rooms."""
    Room = apps.get_model("HotelApp", "Room")
    existing_room_numbers = set(
        Room.objects.values_list("room_number", flat=True)
    )
    missing_rooms = [
        Room(**room_data)
        for room_data in DEFAULT_ROOMS
        if room_data["room_number"] not in existing_room_numbers
    ]
    if missing_rooms:
        Room.objects.bulk_create(missing_rooms)


class Migration(migrations.Migration):
    dependencies = [
        ("HotelApp", "0006_alter_offlinebooking_check_in_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_initial_rooms, migrations.RunPython.noop),
    ]
