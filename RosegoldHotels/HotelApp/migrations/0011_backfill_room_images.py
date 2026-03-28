from django.db import migrations


DEFAULT_ROOM_IMAGE_BY_NUMBER = {
    "101": "rooms/single1.jpg",
    "102": "rooms/single2.jpg",
    "103": "rooms/single1.jpg",
    "104": "rooms/single2.jpg",
    "201": "rooms/double1.jpg",
    "202": "rooms/double2.jpg",
    "203": "rooms/double1.jpg",
    "301": "rooms/suite1.jpg",
    "302": "rooms/suite2.jpg",
    "303": "rooms/suite1.jpg",
}

DEFAULT_ROOM_IMAGE_BY_TYPE = {
    "single": "rooms/single1.jpg",
    "double": "rooms/double1.jpg",
    "suite": "rooms/suite1.jpg",
}


def get_default_room_image_path(room):
    room_number = str(room.room_number or "").strip()
    if room_number in DEFAULT_ROOM_IMAGE_BY_NUMBER:
        return DEFAULT_ROOM_IMAGE_BY_NUMBER[room_number]

    room_type = str(room.room_type or "").strip()
    return DEFAULT_ROOM_IMAGE_BY_TYPE.get(room_type, "")


def backfill_room_images(apps, schema_editor):
    Room = apps.get_model("HotelApp", "Room")

    for room in Room.objects.all().only("id", "room_number", "room_type", "image"):
        if room.image:
            continue

        image_path = get_default_room_image_path(room)
        if not image_path:
            continue

        room.image = image_path
        room.save(update_fields=["image"])


class Migration(migrations.Migration):
    dependencies = [
        ("HotelApp", "0010_alter_activitylog_booking_id_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_room_images, migrations.RunPython.noop),
    ]
