from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_page_renders_without_room_query(self):
        with patch("HotelApp.views.Room.objects.all", side_effect=AssertionError("Room query should not run")):
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
