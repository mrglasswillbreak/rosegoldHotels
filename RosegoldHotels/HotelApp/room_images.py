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


def get_default_room_image_path(room_number="", room_type=""):
    normalized_room_number = str(room_number or "").strip()
    if normalized_room_number in DEFAULT_ROOM_IMAGE_BY_NUMBER:
        return DEFAULT_ROOM_IMAGE_BY_NUMBER[normalized_room_number]

    normalized_room_type = str(room_type or "").strip()
    return DEFAULT_ROOM_IMAGE_BY_TYPE.get(normalized_room_type, "")
