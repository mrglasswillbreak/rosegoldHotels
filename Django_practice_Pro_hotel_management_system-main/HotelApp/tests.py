from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError

from .models import Room


class HomeViewTests(TestCase):
    def test_home_page_loads_latest_rooms_when_database_is_available(self):
        Room.objects.create(
            room_number="A101",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="available",
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rooms"]), 1)

    def test_home_page_renders_when_room_query_fails(self):
        with patch("HotelApp.views.Room.objects.all", side_effect=OperationalError("db unavailable")):
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rooms"], [])

    def test_home_page_renders_when_room_schema_is_unavailable(self):
        with patch("HotelApp.views.Room.objects.all", side_effect=ProgrammingError("relation does not exist")):
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rooms"], [])
