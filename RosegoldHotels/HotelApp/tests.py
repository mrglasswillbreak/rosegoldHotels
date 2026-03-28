from unittest.mock import patch
from pathlib import Path
from datetime import date
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Room, OnlineBooking, OfflineBooking
from .paystack import initialize_transaction
from .room_seed import seed_missing_rooms
from .tokens import account_activation_token


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


class LoginRoutingTests(TestCase):
    def test_login_redirects_staff_users_to_custom_admin_dashboard(self):
        admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123!",
        )

        response = self.client.post(reverse("author_login"), data={
            "username": admin_user.email,
            "password": "AdminPass123!",
        })

        self.assertRedirects(response, reverse("dashboard"))

    def test_login_redirects_regular_users_to_user_home(self):
        user = get_user_model().objects.create_user(
            email="guest@example.com",
            password="GuestPass123!",
        )

        response = self.client.post(reverse("author_login"), data={
            "username": user.email,
            "password": "GuestPass123!",
        })

        self.assertRedirects(response, reverse("user_home"))

    def test_login_preserves_next_url_for_staff_users(self):
        admin_user = get_user_model().objects.create_superuser(
            email="manager@example.com",
            password="AdminPass123!",
        )

        response = self.client.post(
            f"{reverse('author_login')}?next={reverse('add_room')}",
            data={
                "username": admin_user.email,
                "password": "AdminPass123!",
                "next": reverse("add_room"),
            },
        )

        self.assertRedirects(response, reverse("add_room"))

    def test_login_page_renders_200_with_next_query_param(self):
        """Regression test: GET /login/?next=... must not raise VariableDoesNotExist."""
        response = self.client.get(
            f"{reverse('author_login')}?next={reverse('user_home')}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<input type="hidden" name="next" value="{reverse("user_home")}">',
        )

    def test_login_page_renders_200_without_next_query_param(self):
        """Regression test: GET /login/ (no next) must also render cleanly."""
        response = self.client.get(reverse("author_login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="next"')

    def test_login_page_strips_unsafe_next_url(self):
        """An external ?next= value must not appear in the rendered form."""
        response = self.client.get(
            f"{reverse('author_login')}?next=https://evil.com"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "evil.com")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class MediaServingTests(TestCase):
    def test_room_images_are_served_when_debug_is_disabled(self):
        self.assertFalse(settings.DEBUG)

        response = self.client.get("/media/rooms/single1.jpg", secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistrationConfirmationTests(TestCase):
    def test_registration_creates_inactive_user_and_sends_confirmation_email(self):
        response = self.client.post(
            reverse("author_register"),
            data={
                "first_name": "Ada",
                "last_name": "Guest",
                "email": "ada@example.com",
                "phone_number": "08001234567",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
                "accept_terms": "on",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("registration_pending"))
        user = get_user_model().objects.get(email="ada@example.com")
        self.assertFalse(user.is_active)
        self.assertContains(response, "We sent a confirmation email to your inbox.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])
        self.assertIn("Confirm your RoseGold Hotel account", mail.outbox[0].subject)
        self.assertIn("/register/confirm/", mail.outbox[0].body)

    def test_registration_rejects_invalid_email_addresses(self):
        response = self.client.post(
            reverse("author_register"),
            data={
                "first_name": "Ada",
                "last_name": "Guest",
                "email": "not-an-email",
                "phone_number": "08001234567",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
                "accept_terms": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address.")
        self.assertFalse(get_user_model().objects.filter(email="not-an-email").exists())

    def test_activation_link_marks_user_active(self):
        user = get_user_model().objects.create_user(
            email="pending@example.com",
            password="GuestPass123!",
            is_active=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)

        response = self.client.get(reverse("activate_account", args=[uid, token]), follow=True)

        self.assertRedirects(response, reverse("author_login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertContains(response, "Your email has been confirmed. You can now sign in.")

    def test_login_shows_confirmation_message_for_inactive_users(self):
        inactive_user = get_user_model().objects.create_user(
            email="inactive@example.com",
            password="GuestPass123!",
            is_active=False,
        )

        response = self.client.post(
            reverse("author_login"),
            data={
                "username": inactive_user.email,
                "password": "GuestPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please confirm your email before signing in.")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
class RegistrationPendingFallbackTests(TestCase):
    def test_registration_shows_activation_link_when_email_delivery_is_not_configured(self):
        response = self.client.post(
            reverse("author_register"),
            data={
                "first_name": "Local",
                "last_name": "Tester",
                "email": "localtester@example.com",
                "phone_number": "08001234567",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
                "accept_terms": "on",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("registration_pending"))
        self.assertContains(response, "This environment is not configured to deliver real emails yet")
        self.assertContains(response, "/register/confirm/")
        self.assertFalse(get_user_model().objects.get(email="localtester@example.com").is_active)


class AdminAccessControlTests(TestCase):
    def test_home_redirects_staff_users_to_custom_admin_dashboard(self):
        admin_user = get_user_model().objects.create_superuser(
            email="adminhome@example.com",
            password="AdminPass123!",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("home"))

        self.assertRedirects(response, reverse("dashboard"))

    def test_non_staff_users_cannot_access_custom_admin_routes(self):
        user = get_user_model().objects.create_user(
            email="member@example.com",
            password="GuestPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("add_room"))

        self.assertRedirects(response, reverse("user_home"))


@override_settings(SECURE_SSL_REDIRECT=False)
class CustomAdminDashboardTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email="adminpanel@example.com",
            password="AdminPass123!",
        )
        self.client.force_login(self.admin_user)

    def test_dashboard_uses_live_database_metrics(self):
        guest_user = get_user_model().objects.create_user(
            email="dashboard-guest@example.com",
            password="GuestPass123!",
        )
        available_room = Room.objects.create(
            room_number="A500",
            room_type="single",
            floor=5,
            facility="WiFi",
            price="120.00",
            status="available",
        )
        occupied_room = Room.objects.create(
            room_number="B600",
            room_type="suite",
            floor=6,
            facility="Spa",
            price="320.00",
            status="occupied",
        )
        OnlineBooking.objects.create(
            user=guest_user,
            room=occupied_room,
            check_in=date(2026, 4, 1),
            check_out=date(2026, 4, 4),
            adults=2,
            children=1,
            city="Lagos",
            country="Nigeria",
            address="12 Admin Road",
        )
        OfflineBooking.objects.create(
            room=available_room,
            first_name="Desk",
            last_name="Guest",
            email="desk@example.com",
            mobile_number="08001234567",
            check_in=date(2026, 4, 10),
            check_out=date(2026, 4, 12),
            adults=2,
            children=0,
            country="Nigeria",
            address="Front Desk",
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total_bookings"], 2)
        self.assertEqual(response.context["stats"]["online_bookings"], 1)
        self.assertEqual(response.context["stats"]["offline_bookings"], 1)
        self.assertEqual(response.context["stats"]["rooms_available"], 1)
        self.assertEqual(response.context["stats"]["users"], 2)

    def test_admin_can_create_room_from_custom_admin(self):
        response = self.client.post(reverse("add_room"), data={
            "room_number": "C700",
            "room_type": "double",
            "floor": 7,
            "facility": "WiFi, TV",
            "price": "180.00",
            "status": "available",
        })

        self.assertRedirects(response, reverse("add_room"))
        self.assertTrue(Room.objects.filter(room_number="C700").exists())

    def test_admin_can_create_user_from_custom_admin(self):
        response = self.client.post(reverse("manage_users"), data={
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "08000000000",
            "theme": "light",
            "is_active": "on",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        self.assertRedirects(response, reverse("manage_users"))
        created_user = get_user_model().objects.get(email="newuser@example.com")
        self.assertTrue(created_user.check_password("StrongPass123!"))
        self.assertFalse(created_user.is_staff)

    def test_admin_can_create_online_booking_from_custom_admin(self):
        guest_user = get_user_model().objects.create_user(
            email="booking-admin@example.com",
            password="GuestPass123!",
        )
        room = Room.objects.create(
            room_number="D800",
            room_type="suite",
            floor=8,
            facility="WiFi, Pool",
            price="400.00",
            status="available",
        )

        response = self.client.post(reverse("online_booking_list"), data={
            "user": guest_user.pk,
            "room": room.pk,
            "check_in": "2026-05-01",
            "check_out": "2026-05-04",
            "adults": 2,
            "children": 1,
            "city": "Abuja",
            "country": "Nigeria",
            "address": "Airport Road",
        })

        self.assertRedirects(response, reverse("online_booking_list"))
        self.assertTrue(
            OnlineBooking.objects.filter(user=guest_user, room=room, city="Abuja", country="Nigeria").exists()
        )


@override_settings(SECURE_SSL_REDIRECT=False)
class AdminDashboardRegressionTests(TestCase):
    def test_superuser_can_open_dashboard_without_server_error(self):
        admin_user = get_user_model().objects.create_superuser(
            email="dashboard-admin@example.com",
            password="AdminPass123!",
        )

        self.client.force_login(admin_user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Custom Admin Dashboard")

    def test_admin_dashboard_uses_text_user_card_without_images(self):
        admin_user = get_user_model().objects.create_superuser(
            email="avatar-admin@example.com",
            password="AdminPass123!",
        )

        self.client.force_login(admin_user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="admin-user-card"')
        self.assertContains(response, 'class="fa fa-user-circle"')
        self.assertNotContains(response, "<img")
        self.assertNotContains(response, "eniadmin.jpg")

    def test_receptionist_dashboard_uses_text_user_card_without_images(self):
        receptionist_user = get_user_model().objects.create_user(
            email="avatar-reception@example.com",
            password="ReceptionPass123!",
            is_receptionist=True,
        )

        self.client.force_login(receptionist_user)
        response = self.client.get(reverse("receptionist_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="admin-user-card"')
        self.assertContains(response, 'class="fa fa-user-circle"')
        self.assertNotContains(response, "<img")
        self.assertNotContains(response, "eniadmin.jpg")


@override_settings(SECURE_SSL_REDIRECT=False)
class RoomAvailabilityViewTests(TestCase):
    def setUp(self):
        Room.objects.all().delete()
        self.user = get_user_model().objects.create_user(
            email="roomviewer@example.com",
            password="StrongPass123!",
        )

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

    def test_room_list_uses_fallback_image_when_room_has_no_uploaded_image(self):
        Room.objects.create(
            room_number="101",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="100.00",
            status="available",
        )

        response = self.client.get(reverse("room_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/media/rooms/single1.jpg"')

    def test_online_booking_page_lists_rooms_regardless_of_status(self):
        self.client.force_login(self.user)
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

        response = self.client.get(f"{reverse('online_booking')}?new=1")

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context["rooms"], [available_room, maintenance_room])

    def test_online_booking_form_uses_fallback_image_for_selected_room(self):
        self.client.force_login(self.user)
        room = Room.objects.create(
            room_number="202",
            room_type="double",
            floor=2,
            facility="Balcony",
            price="250.00",
            status="available",
        )

        response = self.client.get(f"{reverse('online_booking')}?new=1&room={room.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/media/rooms/double2.jpg"')
        self.assertContains(response, 'image: "/media/rooms/double2.jpg"')

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

    def test_book_room_page_uses_fallback_image_when_room_has_no_uploaded_image(self):
        self.client.force_login(self.user)
        room = Room.objects.create(
            room_number="301",
            room_type="suite",
            floor=3,
            facility="Jacuzzi",
            price="500.00",
            status="available",
        )

        response = self.client.get(reverse("book_room", args=[room.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/media/rooms/suite1.jpg"')

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

    def test_seed_function_assigns_default_room_images(self):
        image_names = list(Room.objects.order_by("room_number").values_list("image", flat=True))

        self.assertTrue(all(image_names))


@override_settings(SECURE_SSL_REDIRECT=False)
class PaystackPaymentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="payer@example.com",
            password="PayTest123!",
        )
        self.client.force_login(self.user)
        self.room = Room.objects.create(
            room_number="P101",
            room_type="single",
            floor=1,
            facility="WiFi",
            price="200.00",
            status="available",
        )

    def _pending_booking_session(self):
        return {
            "room_id": self.room.id,
            "check_in": "2026-06-01",
            "check_out": "2026-06-03",
            "adults": 2,
            "children": 0,
            "city": "Lagos",
            "country": "Nigeria",
            "address": "5 Hotel Lane",
        }

    def _make_init_response(self, status=True, access_code="acc_test", authorization_url="https://checkout.paystack.com/test"):
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.status = status
        resp.data.access_code = access_code
        resp.data.authorization_url = authorization_url
        return resp

    def _make_verify_response(self, status=True, tx_status="success", raw=None):
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.status = status
        resp.data.status = tx_status
        resp.raw = raw or {"status": True, "data": {"status": tx_status}}
        return resp

    # --- initiate_payment ---

    def test_initiate_payment_redirects_to_paystack_checkout_on_success(self):
        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        init_resp = self._make_init_response()
        with patch("HotelApp.views.PaystackClient") as MockClient:
            MockClient.return_value.transactions.initialize.return_value = init_resp
            response = self.client.post(reverse("initiate_payment"))

        self.assertRedirects(
            response, "https://checkout.paystack.com/test", fetch_redirect_response=False
        )

    def test_initiate_payment_creates_pending_payment_record(self):
        from HotelApp.models import Payment
        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        init_resp = self._make_init_response(access_code="acc_xyz")
        with patch("HotelApp.views.PaystackClient") as MockClient:
            MockClient.return_value.transactions.initialize.return_value = init_resp
            self.client.post(reverse("initiate_payment"))

        payment = Payment.objects.filter(payment_status="pending", payment_method="paystack").first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.paystack_access_code, "acc_xyz")

    def test_initiate_payment_redirects_to_online_booking_when_paystack_returns_failure(self):
        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        init_resp = self._make_init_response(status=False)
        with patch("HotelApp.views.PaystackClient") as MockClient:
            MockClient.return_value.transactions.initialize.return_value = init_resp
            response = self.client.post(reverse("initiate_payment"))

        self.assertRedirects(response, reverse("booking_payment_page"))

    def test_initiate_payment_redirects_to_online_booking_when_no_pending_booking_in_session(self):
        response = self.client.post(reverse("initiate_payment"))
        self.assertRedirects(response, reverse("online_booking"))

    def test_initiate_payment_get_request_redirects_to_online_booking(self):
        response = self.client.get(reverse("initiate_payment"))
        self.assertRedirects(response, reverse("online_booking"))

    @override_settings(PAYSTACK_MOCK_MODE=True, PAYSTACK_SECRET_KEY="")
    def test_initiate_payment_completes_booking_in_mock_mode(self):
        from HotelApp.models import Payment, OnlineBooking

        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        response = self.client.post(reverse("initiate_payment"))

        booking = OnlineBooking.objects.get(user=self.user, room=self.room)
        payment = Payment.objects.get(booking_id=booking.id)

        self.assertEqual(payment.payment_status, "paid")
        self.assertEqual(payment.payment_method, "paystack")
        self.assertIn("local demo payment mode", payment.notes)
        self.assertRedirects(
            response,
            reverse("payment_success", kwargs={"booking_id": booking.id}),
            fetch_redirect_response=False,
        )

    @override_settings(PAYSTACK_MOCK_MODE=False, PAYSTACK_SECRET_KEY="", PAYSTACK_PUBLIC_KEY="")
    def test_initiate_payment_shows_configuration_error_when_secret_key_is_missing(self):
        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        response = self.client.post(reverse("initiate_payment"), follow=True)

        self.assertRedirects(response, reverse("booking_payment_page"))
        self.assertContains(response, "Payment gateway is not configured on this deployment.")

    @override_settings(PAYSTACK_MOCK_MODE=False, PAYSTACK_SECRET_KEY="sk_test_demo", PAYSTACK_PUBLIC_KEY="pk_test_demo")
    def test_initiate_payment_shows_cloudflare_specific_message(self):
        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        init_resp = self._make_init_response(status=False)
        init_resp.raw = {
            "status": False,
            "message": (
                '{"status":403,"error_code":1010,"error_name":"browser_signature_banned",'
                '"cloudflare_error":true,"ray_id":"9e3a1ccbaab15ec6"}'
            ),
        }

        with patch("HotelApp.views.PaystackClient") as MockClient:
            MockClient.return_value.transactions.initialize.return_value = init_resp
            response = self.client.post(reverse("initiate_payment"), follow=True)

        self.assertRedirects(response, reverse("booking_payment_page"))
        self.assertContains(response, "Cloudflare (Error 1010)")
        self.assertContains(response, "9e3a1ccbaab15ec6")

    # --- payment_callback ---

    def test_payment_callback_creates_booking_and_marks_payment_paid_on_success(self):
        from HotelApp.models import Payment
        reference = "HMS-TESTREF123"
        Payment.objects.create(
            booking_type="online",
            booking_id=0,
            amount="400.00",
            payment_method="paystack",
            payment_status="pending",
            receipt_number=reference,
            paystack_reference=reference,
            created_by=self.user,
        )
        session = self.client.session
        session["pending_booking"] = self._pending_booking_session()
        session.save()

        verify_resp = self._make_verify_response()
        with patch("HotelApp.views.PaystackClient") as MockClient:
            MockClient.return_value.transactions.verify.return_value = verify_resp
            response = self.client.get(
                reverse("payment_callback"), {"reference": reference}
            )

        payment = Payment.objects.get(paystack_reference=reference)
        self.assertEqual(payment.payment_status, "paid")
        self.assertIsNotNone(payment.paid_at)
        from HotelApp.models import OnlineBooking
        self.assertTrue(OnlineBooking.objects.filter(user=self.user, room=self.room).exists())
        self.assertRedirects(
            response, reverse("payment_success", kwargs={"booking_id": payment.booking_id}),
            fetch_redirect_response=False,
        )

    def test_payment_callback_marks_payment_failed_when_verification_not_success(self):
        from HotelApp.models import Payment
        reference = "HMS-FAILREF456"
        Payment.objects.create(
            booking_type="online",
            booking_id=0,
            amount="400.00",
            payment_method="paystack",
            payment_status="pending",
            receipt_number=reference,
            paystack_reference=reference,
            created_by=self.user,
        )

        verify_resp = self._make_verify_response(tx_status="failed")
        with patch("HotelApp.views.PaystackClient") as MockClient:
            MockClient.return_value.transactions.verify.return_value = verify_resp
            response = self.client.get(
                reverse("payment_callback"), {"reference": reference}
            )

        payment = Payment.objects.get(paystack_reference=reference)
        self.assertEqual(payment.payment_status, "failed")
        self.assertRedirects(response, reverse("payment_failed"))

    def test_payment_callback_redirects_to_user_home_when_no_reference(self):
        response = self.client.get(reverse("payment_callback"))
        self.assertRedirects(response, reverse("user_home"))


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


class PaystackTransportTests(TestCase):
    @override_settings(PAYSTACK_SECRET_KEY="sk_test_demo", PAYSTACK_USER_AGENT="RoseGoldHotels/1.0")
    def test_initialize_transaction_sends_custom_user_agent(self):
        captured = {}

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"status": true, "data": {"authorization_url": "https://checkout.paystack.com/test"}}'

        def fake_urlopen(request, timeout=20):
            captured["user_agent"] = request.get_header("User-agent")
            return DummyResponse()

        with patch("HotelApp.paystack.urlopen", side_effect=fake_urlopen):
            initialize_transaction(
                email="guest@example.com",
                amount=Decimal("100.00"),
                reference="HMS-USERAGENT1",
                callback_url="https://example.com/callback",
                secret_key="sk_test_demo",
            )

        self.assertEqual(captured["user_agent"], "RoseGoldHotels/1.0")
