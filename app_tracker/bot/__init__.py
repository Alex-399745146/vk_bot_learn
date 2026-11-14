"""Пакет бота: транспорт, сценарии и вспомогательные модули.

Публичная точка входа для runbot.py — handle_update.
"""

from __future__ import annotations

from app_tracker.bot.router import handle_update

__all__ = ["handle_update"]
