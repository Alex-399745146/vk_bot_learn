"""Связь веб-аккаунта с участником бота."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Профиль веб-пользователя и его участник из бота."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    participant = models.OneToOneField(
        "app_tracker.Participant",
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Участник",
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self) -> str:
        return f"{self.user.username} → {self.participant}"
