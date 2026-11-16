"""Модели(структуры данных в БД) — описание таблиц
базы данных обычным Python-кодом.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class Participant(models.Model):
    """Участник и его цели на текущий месяц."""

    vk_id = models.BigIntegerField("VK ID", unique=True)
    last_name = models.CharField("Фамилия", max_length=80, blank=True, default="")
    first_name = models.CharField("Имя", max_length=60, blank=True, default="")
    goal_1 = models.CharField("Цель 1", max_length=200, blank=True, default="")
    goal_2 = models.CharField("Цель 2", max_length=200, blank=True, default="")
    goal_3 = models.CharField("Цель 3", max_length=200, blank=True, default="")
    goals_month = models.CharField(
        "Месяц целей", max_length=7, blank=True, default="", help_text="Например: 2026-11"
    )
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)

    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name} ({self.vk_id})"

    @property
    def goals(self) -> list[str]:
        """Три цели в виде списка — удобно перебирать."""
        return [self.goal_1, self.goal_2, self.goal_3]

    @property
    def has_goals(self) -> bool:
        """Цели заполнены и поставлены на текущий месяц."""
        current = timezone.localdate().strftime("%Y-%m")
        return self.goals_month == current and all(self.goals)


class BotState(models.Model):
    """Где сейчас находится человек в диалоге."""

    vk_id = models.BigIntegerField("VK ID", unique=True)
    state = models.CharField("Состояние", max_length=32, default="IDLE")
    data = models.JSONField("Данные шага", default=dict, blank=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Состояние диалога"
        verbose_name_plural = "Состояния диалогов"

    def __str__(self) -> str:
        return f"{self.vk_id}: {self.state}"


class Report(models.Model):
    """Отметка за день: какие из трёх целей выполнены."""

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="reports", verbose_name="Участник"
    )
    date = models.DateField("Дата")
    goal_1_done = models.BooleanField("Цель 1 выполнена", default=False)
    goal_2_done = models.BooleanField("Цель 2 выполнена", default=False)
    goal_3_done = models.BooleanField("Цель 3 выполнена", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    is_chill = models.BooleanField("Chill", default=False)
    goal_1_note = models.TextField("Пояснение к цели 1", blank=True, default="")
    goal_2_note = models.TextField("Пояснение к цели 2", blank=True, default="")
    goal_3_note = models.TextField("Пояснение к цели 3", blank=True, default="")

    class Meta:
        verbose_name = "Отметка"
        verbose_name_plural = "Отметки"
        ordering = ["-date", "participant__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "date"], name="unique_participant_date"
            )
        ]

    def __str__(self) -> str:
        return f"{self.participant} — {self.date}: {self.goals_done}/3"

    @property
    def goals_done(self) -> int:
        return sum([self.goal_1_done, self.goal_2_done, self.goal_3_done])

    @property
    def completed(self) -> bool:
        return self.goals_done == 3

class GoalPeriod(models.Model):
    """Период целей участника на конкретный месяц."""
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='goal_periods')
    month = models.CharField("Месяц", max_length=7)  # Формат "2026-11"
    goal_1 = models.CharField("Цель 1", max_length=200, blank=True, default="")
    goal_2 = models.CharField("Цель 2", max_length=200, blank=True, default="")
    goal_3 = models.CharField("Цель 3", max_length=200, blank=True, default="")
    status = models.CharField(
        "Статус",
        max_length=10,
        choices=[("active", "Активен"), ("paused", "Пауза")],
        default="active"
    )

    class Meta:
        unique_together = ("participant", "month")
        verbose_name = "Период целей"
        verbose_name_plural = "Периоды целей"

    def __str__(self):
        return f"{self.participant} — {self.month} ({self.status})"


class Activity(models.Model):
    """Дополнительная активность участника (Мой день, Буст, Встреча)."""
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='activities')
    kind = models.CharField(
        "Тип",
        max_length=20,
        choices=[("self_day", "Мой день"), ("boost", "Буст"), ("meeting", "Встреча")]
    )
    note = models.TextField("Примечание", blank=True, default="")
    points = models.IntegerField("Баллы", default=2)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Активность"
        verbose_name_plural = "Активности"


class Media(models.Model):
    """Медиафайлы, прикрепленные к отчетам или активностям."""
    report = models.ForeignKey('Report', on_delete=models.CASCADE, null=True, blank=True, related_name='media_files')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True, related_name='media_files')
    goal_index = models.SmallIntegerField("Номер цели", null=True, blank=True)  # 1, 2 или 3
    kind = models.CharField("Тип", max_length=10, choices=[("photo", "Фото"), ("video", "Видео")])
    file = models.FileField("Файл", upload_to='reports/%Y-%m/', blank=True, null=True)
    external_id = models.CharField("ID во ВК", max_length=100, blank=True, default="")
    source_url = models.URLField("Ссылка", max_length=500, blank=True, default="")
    duration = models.IntegerField("Длительность (сек)", null=True, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Медиафайл"
        verbose_name_plural = "Медиафайлы"
