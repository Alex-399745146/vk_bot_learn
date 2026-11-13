"""Модели — описание таблиц базы данных обычным Python-кодом.

Django сам создаёт таблицы по этим классам (команда `migrate`).
"""

from __future__ import annotations

from django.db import models


class Participant(models.Model):
    """Участник бота. Одна запись — один человек ВКонтакте."""

    vk_id = models.BigIntegerField("VK ID", unique=True)
    name = models.CharField("Имя", max_length=100)
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)

    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"
        ordering = ["name"]

    def __str__(self) -> str:
        # Так запись выглядит в админке и в консоли.
        return f"{self.name} ({self.vk_id})"
