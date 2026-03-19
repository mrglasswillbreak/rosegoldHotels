from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError
from django.contrib.auth import get_user_model

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
        with patch("HotelApp.views.Room.objects") as mocked_manager:
            mocked_queryset = mocked_manager.all.return_value.order_by.return_value
            mocked_queryset.__getitem__.side_effect = OperationalError("db unavailable")
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rooms"], [])
        mocked_manager.all.assert_called_once()
        mocked_manager.all.return_value.order_by.assert_called_once_with("-id")
        mocked_queryset.__getitem__.assert_called_once_with(slice(None, 6, None))

    def test_home_page_renders_when_room_schema_is_unavailable(self):
        with patch("HotelApp.views.Room.objects") as mocked_manager:
            mocked_queryset = mocked_manager.all.return_value.order_by.return_value
            mocked_queryset.__getitem__.side_effect = ProgrammingError("relation does not exist")
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rooms"], [])
        mocked_manager.all.assert_called_once()
        mocked_manager.all.return_value.order_by.assert_called_once_with("-id")
        mocked_queryset.__getitem__.assert_called_once_with(slice(None, 6, None))


class RoomAvailabilityViewTests(TestCase):
    def test_room_list_shows_rooms_regardless_of_status(self):
        available_room = Room.objects.create(
            room_number="A101",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="available",
        )
        occupied_room = Room.objects.create(
            room_number="B202",
            room_type="double",
            floor=2,
            facility="TV",
            price="200.00",
            status="occupied",
        )

        response = self.client.get(reverse("room_list"))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context["rooms"], [available_room, occupied_room])

    def test_online_booking_page_lists_rooms_regardless_of_status(self):
        available_room = Room.objects.create(
            room_number="A103",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="available",
        )
        maintenance_room = Room.objects.create(
            room_number="C303",
            room_type="suite",
            floor=3,
            facility="Pool",
            price="300.00",
            status="maintenance",
        )

        response = self.client.get(reverse("online_booking"))

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context["rooms"], [available_room, maintenance_room])

    def test_online_booking_post_error_keeps_rooms_across_statuses(self):
        user = get_user_model().objects.create_user(
            email="guest@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        available_room = Room.objects.create(
            room_number="A104",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="available",
        )
        occupied_room = Room.objects.create(
            room_number="B203",
            room_type="double",
            floor=2,
            facility="TV",
            price="200.00",
            status="occupied",
        )

        response = self.client.post(reverse("online_booking"), data={})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context["rooms"], [available_room, occupied_room])
