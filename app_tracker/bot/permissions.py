"""Права в боте.

В ВК нет входа в аккаунт, поэтому «суперпользователь» — это VK ID из
`SUPERUSER_VK_ID` в `.env`. Django-флаг `is_superuser` тут не работает:
он относится к веб-админке, а не к боту.

Модератор — обычный участник с `Participant.is_moderator = True`; права
выдаёт суперпользователь в списке «Модераторы».
"""

from __future__ import annotations

from django.conf import settings

from app_tracker.models import Participant


def is_superuser(participant: Participant) -> bool:
    """Owner бота: VK ID совпадает с SUPERUSER_VK_ID."""
    return bool(settings.SUPERUSER_VK_ID) and participant.vk_id == settings.SUPERUSER_VK_ID


def can_moderate(participant: Participant) -> bool:
    """Может ли участник модерировать: суперпользователь или назначенный модератор."""
    return is_superuser(participant) or participant.is_moderator
