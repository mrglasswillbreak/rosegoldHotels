from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from HotelApp.bootstrap import ensure_env_receptionist_account


@override_settings(
    DEFAULT_RECEPTIONIST_EMAIL="receptionist-env@example.com",
    DEFAULT_RECEPTIONIST_PASSWORD="FrontDeskEnv123!",
    DEFAULT_RECEPTIONIST_FIRST_NAME="Front",
    DEFAULT_RECEPTIONIST_LAST_NAME="Desk",
    DEFAULT_RECEPTIONIST_PHONE="+2348012345678",
    DEFAULT_RECEPTIONIST_THEME="light",
    DEFAULT_RECEPTIONIST_IS_ACTIVE=True,
    DEFAULT_RECEPTIONIST_SYNC_PASSWORD=True,
)
class ReceptionistEnvBootstrapTests(TestCase):
    def test_env_bootstrap_creates_receptionist_account_and_login_works(self):
        created_user = ensure_env_receptionist_account(force=True)

        self.assertIsNotNone(created_user)
        self.assertTrue(created_user.is_receptionist)
        self.assertFalse(created_user.is_staff)
        self.assertEqual(created_user.first_name, "Front")
        self.assertEqual(created_user.last_name, "Desk")
        self.assertEqual(created_user.phone_number, "+2348012345678")
        self.assertTrue(created_user.check_password("FrontDeskEnv123!"))

        response = self.client.post(
            reverse("author_login"),
            data={
                "username": "receptionist-env@example.com",
                "password": "FrontDeskEnv123!",
            },
        )

        self.assertRedirects(response, reverse("receptionist_dashboard"))

    def test_env_bootstrap_updates_existing_receptionist_password(self):
        user_model = get_user_model()
        existing_user = user_model.objects.create_user(
            email="receptionist-env@example.com",
            password="OldPassword123!",
            first_name="Old",
            last_name="Name",
            is_receptionist=True,
        )

        synced_user = ensure_env_receptionist_account(force=True)
        existing_user.refresh_from_db()

        self.assertEqual(existing_user.pk, synced_user.pk)
        self.assertEqual(existing_user.first_name, "Front")
        self.assertEqual(existing_user.last_name, "Desk")
        self.assertTrue(existing_user.check_password("FrontDeskEnv123!"))
