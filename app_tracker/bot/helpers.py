"""Мелкие помощники: отправка, проверки, дата, имя пользователя."""

from __future__ import annotations

import logging
import os
import requests
from datetime import datetime
from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)


def send(vk, peer_id: int, text: str, keyboard: str | None = None) -> None:
    """Отправляет сообщение через VK и пишет его в лог."""
    log.debug("Ответ в %s: %r", peer_id, text)
    vk.send_message(peer_id, text, keyboard=keyboard)


def validate_text(text: str) -> str | None:
    """Проверяет текст цели; возвращает текст ошибки или None, если всё в порядке."""
    if not text:
        return "Мне нужен текст."
    if text.startswith("/"):
        return "Напиши обычным текстом, без команд."
    if len(text) < 3:
        return "Слишком коротко, напиши ещё раз."
    return None


def current_month() -> str:
    """Возвращает текущий месяц в формате YYYY-MM по часовому поясу проекта."""
    return timezone.localdate().strftime("%Y-%m")


def fetch_user(vk, user_id: int) -> dict:
    """Просит у ВК имя, фамилию, фото и пол.

    Возвращает словарь с ключами `last_name`, `first_name`, `photo_id`,
    `photo_url`, `sex`. Если ВК не ответил — пустые значения, а имя
    «пользователь», чтобы сценарий не падал.
    """
    try:
        profile = vk.get_user_info(user_id) or {}
    except Exception:
        log.warning("users.get не сработал", exc_info=True)
        profile = {}

    try:
        sex = int(profile.get("sex") or 0)
    except (TypeError, ValueError):
        sex = 0

    return {
        "last_name": str(profile.get("last_name") or ""),
        "first_name": str(profile.get("first_name") or "пользователь"),
        "photo_id": str(profile.get("photo_id") or ""),
        "photo_url": str(profile.get("photo_200") or ""),
        "sex": sex,
    }


def extract_media_from_vk_attachments(attachments: list) -> list[dict]:
    """Принимает список attachments из ВК, возвращает данные для скачивания."""
    media_list = []
    for att in attachments:
        att_type = att.get('type')

        if att_type == 'photo':
            photo_data = att.get('photo', {})
            sizes = photo_data.get('sizes', [])
            if sizes:
                best_size = max(sizes, key=lambda s: s.get('width', 0))
                media_list.append({
                    'kind': 'photo',
                    'url': best_size.get('url'),
                    'external_id': f"photo{photo_data.get('owner_id')}_{photo_data.get('id')}"
                })

        elif att_type == 'video':
            video_data = att.get('video', {})
            media_list.append({
                'kind': 'video',
                'url': video_data.get('player'),
                'source_url': f"https://vk.com/video{video_data.get('owner_id')}_{video_data.get('id')}",
                'external_id': f"video{video_data.get('owner_id')}_{video_data.get('id')}",
                'duration': video_data.get('duration', 0)
            })
    return media_list


def download_vk_attachment(url: str, report_id: int, filename: str) -> str | None:
    """Скачивает файл из ВК в папку media/reports/YYYY-MM/report_id/."""
    if not url:
        return None

    date_str = datetime.now().strftime("%Y-%m")
    rel_dir = f"reports/{date_str}/{report_id}"
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)

    os.makedirs(abs_dir, exist_ok=True)
    filepath = os.path.join(abs_dir, filename)

    try:
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"{rel_dir}/{filename}"
    except Exception as e:
        log.error(f"Ошибка при скачивании файла {url}: {e}")
        return None
