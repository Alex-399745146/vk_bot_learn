"""Запуск бота из Django: python manage.py runbot.

Django нужен ради базы и админки. Цикл LongPoll остаётся обычным
синхронным циклом, а транспорт лежит в app_tracker/vk.py.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app_tracker.bot import handle_update
from app_tracker.lock import acquire_single_instance_lock
from app_tracker.vk import VK


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
            for update in vk.long_poll():
                handle_update(vk, update)
        except KeyboardInterrupt:
            self.stdout.write("Остановлено вручную")
        finally:
            lock.close()
