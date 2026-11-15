"""Запуск бота из Django: python manage.py runbot.

Django нужен ради базы и админки. Цикл LongPoll остаётся обычным
синхронным циклом, а транспорт лежит в app_tracker/bot/vk.py.
"""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app_tracker.bot import handle_update
from app_tracker.bot.lock import acquire_single_instance_lock
from app_tracker.bot.vk import RETRY_DELAY, VK

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Запускает учебного бота ВКонтакте"

    def handle(self, *args, **options) -> None:
        if not settings.VK_TOKEN or not settings.VK_GROUP_ID:
            raise CommandError("Заполните VK_TOKEN и VK_GROUP_ID в .env")

        lock = acquire_single_instance_lock()
        vk = VK(settings.VK_TOKEN, int(settings.VK_GROUP_ID))

        self.stdout.write(
            self.style.SUCCESS(
                f"Бот запущен для сообщества {settings.VK_GROUP_ID}. Жду сообщения…"
            )
        )

        try:
            self._listen(vk)
        except KeyboardInterrupt:
            self.stdout.write("Остановлено вручную")
        finally:
            lock.close()

    def _listen(self, vk: VK) -> None:
        """Читает события, переживая ошибки сети и сбои в обработчиках."""
        while True:
            try:
                for update in vk.long_poll():
                    try:
                        handle_update(vk, update)
                    except Exception:
                        # Одно кривое событие не должно останавливать бота.
                        log.exception("Ошибка обработки события — пропускаю")
            except Exception:
                log.exception("LongPoll остановился — перезапускаю через %s с", RETRY_DELAY)
                time.sleep(RETRY_DELAY)
