from unittest.mock import patch
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Room, OnlineBooking
from .room_seed import seed_missing_rooms


class HomeViewTests(TestCase):
    def setUp(self):
        Room.objects.all().delete()

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

    def test_home_redirects_authenticated_user_to_user_home(self):
        user = get_user_model().objects.create_user(
            email="loggedin@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("user_home"))

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

    def test_home_page_contains_explore_and_room_booking_ctas(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "slider-1.jpg")
        self.assertContains(response, 'href="#OUR_ROOMS">explore</a>')
        self.assertContains(response, "?new=1&amp;room_type=", count=6)


class RoomAvailabilityViewTests(TestCase):
    def setUp(self):
        Room.objects.all().delete()

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

    def test_online_booking_room_type_param_preselects_first_available_room(self):
        single_available = Room.objects.create(
            room_number="A105",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="available",
        )
        Room.objects.create(
            room_number="B205",
            room_type="double",
            floor=2,
            facility="TV",
            price="200.00",
            status="available",
        )

        response = self.client.get(
            reverse("online_booking") + "?new=1&room_type=single"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_form"])
        self.assertEqual(response.context["room"], single_available)
        self.assertEqual(response.context["form_data"]["room_id"], str(single_available.id))

    def test_online_booking_room_type_param_ignored_when_no_available_room(self):
        Room.objects.create(
            room_number="A106",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="occupied",
        )

        response = self.client.get(
            reverse("online_booking") + "?new=1&room_type=single"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["room"])

    def test_online_booking_shows_bookings_list_for_authenticated_user(self):
        user = get_user_model().objects.create_user(
            email="booker@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        room = Room.objects.create(
            room_number="D404",
            room_type="suite",
            floor=4,
            facility="WiFi, TV",
            price="500.00",
            status="available",
        )
        from datetime import date
        today = date.today()
        # Active booking (check_out in future)
        OnlineBooking.objects.create(
            user=user,
            room=room,
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            adults=2,
            children=0,
            city="Lagos",
            country="Nigeria",
            address="123 Main St",
        )
        # Past booking (check_out already passed)
        OnlineBooking.objects.create(
            user=user,
            room=room,
            check_in=date(2025, 1, 1),
            check_out=date(2025, 1, 3),
            adults=1,
            children=0,
            city="Lagos",
            country="Nigeria",
            address="123 Main St",
        )

        response = self.client.get(reverse("online_booking"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["show_form"])
        # Only the active booking should appear
        self.assertEqual(len(response.context["bookings"]), 1)
        self.assertEqual(response.context["bookings"][0].nights, 4)


class SeedInitialRoomsTests(TestCase):
    def setUp(self):
        Room.objects.all().delete()
        seed_missing_rooms(Room)

    def test_default_rooms_are_seeded(self):
        room_numbers = list(Room.objects.order_by("room_number").values_list("room_number", flat=True))
        self.assertEqual(
            room_numbers,
            ["101", "102", "103", "104", "201", "202", "203", "301", "302", "303"],
        )

    def test_seed_function_restores_missing_rooms_without_duplicates(self):
        Room.objects.filter(room_number__in=["101", "201", "303"]).delete()
        self.assertEqual(Room.objects.count(), 7)

        seed_missing_rooms(Room)
        self.assertEqual(Room.objects.count(), 10)


class SharedLayoutResponsiveTests(TestCase):
    def test_public_layout_includes_mobile_friendly_navigation(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="navbar navbar-expand-lg modern-navbar"')
        self.assertContains(response, 'class="navbar-toggler"')
        self.assertContains(response, 'data-bs-target="#navbarNav"')

    def test_admin_layout_includes_mobile_friendly_table_wrapper_script(self):
        template_path = Path(settings.BASE_DIR) / "templates" / "admin" / "AdminAllinclude.html"
        template_content = template_path.read_text(encoding="utf-8")

        self.assertIn('class="nav-md admin-modern"', template_content)
        self.assertIn("function wrapTablesForMobile()", template_content)
        self.assertIn("wrapper.className = 'table-responsive';", template_content)
