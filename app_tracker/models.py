"""Модели — описание таблиц базы данных обычным Python-кодом.

Django сам создаёт таблицы по этим классам (команда `migrate`).
"""

from __future__ import annotations

from django.db import models


class Participant(models.Model):
    """Участник бота. Одна запись — один человек ВКонтакте."""

    vk_id = models.BigIntegerField("VK ID", unique=True)
    last_name = models.CharField("Фамилия", max_length=80, blank=True, default="")
    first_name = models.CharField("Имя", max_length=60, blank=True, default="")
    habit = models.CharField("Привычка", max_length=200, blank=True, default="")
    refusal = models.CharField("Отказ", max_length=200, blank=True, default="")
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)

    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        # Так запись выглядит в админке и в консоли.
        return f"{self.last_name} {self.first_name} ({self.vk_id})"


class BotState(models.Model):
    """Где сейчас находится человек в диалоге.

    Живёт в базе, поэтому перезапуск бота не сбрасывает онбординг.
    """

    vk_id = models.BigIntegerField("VK ID", unique=True)
    state = models.CharField("Состояние", max_length=32, default="IDLE")
    data = models.JSONField("Данные шага", default=dict, blank=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Состояние диалога"
        verbose_name_plural = "Состояния диалогов"

    def __str__(self) -> str:
        return f"{self.vk_id}: {self.state}"
