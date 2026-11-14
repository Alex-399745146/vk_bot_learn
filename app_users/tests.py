"""Тесты веб-регистрации и страницы результатов."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app_tracker.models import Participant, Report

from .models import Profile

PASSWORD = "Sup3rSecretPass!"


class RegistrationTests(TestCase):
    def setUp(self) -> None:
        self.participant = Participant.objects.create(
            vk_id=777,
            last_name="Иванов",
            first_name="Иван",
            goal_1="зарядка",
            goal_2="спорт",
            goal_3="без сахара",
            goals_month=timezone.localdate().strftime("%Y-%m"),
        )

    def test_register_links_existing_participant(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "username": "ivan",
                "vk_id": 777,
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="ivan")
        self.assertEqual(user.profile.participant, self.participant)

    def test_unknown_vk_id_is_rejected(self) -> None:
        response = self.client.post(
            reverse("register"),
            {
                "username": "ivan",
                "vk_id": 999,
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "не найден")
        self.assertFalse(User.objects.filter(username="ivan").exists())

    def test_vk_id_cannot_be_linked_twice(self) -> None:
        user = User.objects.create_user("first", password=PASSWORD)
        Profile.objects.create(user=user, participant=self.participant)

        response = self.client.post(
            reverse("register"),
            {
                "username": "second",
                "vk_id": 777,
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "уже привязан")
        self.assertFalse(User.objects.filter(username="second").exists())


class DashboardTests(TestCase):
    def setUp(self) -> None:
        self.participant = Participant.objects.create(
            vk_id=777,
            last_name="Иванов",
            first_name="Иван",
            goal_1="зарядка",
            goal_2="спорт",
            goal_3="без сахара",
            goals_month=timezone.localdate().strftime("%Y-%m"),
        )
        self.user = User.objects.create_user("ivan", password=PASSWORD)
        Profile.objects.create(user=self.user, participant=self.participant)

    def test_dashboard_requires_login(self) -> None:
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_shows_goals_and_report(self) -> None:
        Report.objects.create(
            participant=self.participant,
            date=timezone.localdate(),
            goal_1_done=True,
            goal_2_done=True,
            goal_3_done=True,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "зарядка")
        self.assertContains(response, "3/3")
        self.assertContains(response, "День выполнен")


class PageTests(TestCase):
    def test_login_and_register_pages_render(self) -> None:
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)
