import os
from datetime import timedelta
from django.utils import timezone  # <-- Импортируем timezone
from django.core.management.base import BaseCommand
from app_tracker.bot.constants import MEDIA_RETENTION_MONTHS
from app_tracker.models import Media


class Command(BaseCommand):
    help = 'Удаляет старые медиафайлы (старше MEDIA_RETENTION_MONTHS месяцев)'

    def handle(self, *args, **options):
        # Вычисляем дату отсечения (например, если сейчас ноябрь, удаляем всё до сентября)
        cutoff_date = timezone.now() - timedelta(days=MEDIA_RETENTION_MONTHS * 30)

        # Ищем медиа, которые были созданы раньше этой даты
        old_media = Media.objects.filter(created_at__lt=cutoff_date)

        count = 0
        for media in old_media:
            # 1. Удаляем физический файл с диска
            if media.file and os.path.isfile(media.file.path):
                try:
                    os.remove(media.file.path)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Ошибка удаления файла {media.file.path}: {e}"))
                    continue

            # 2. Удаляем запись из базы данных
            media.delete()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Успешно удалено старых медиафайлов: {count}"))
