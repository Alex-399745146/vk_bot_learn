"""Экран «Модераторы»: список участников и выдача прав.

В ВК нет переключателей, поэтому «ползунок как у айфонов» эмулируем
inline-кнопкой: 🟢 и зелёный цвет — права есть, ⚪ и серый — нет.
Нажатие не создаёт сообщение в чате, а приходит событием message_event,
поэтому список обновляется на месте через messages.edit.
"""

from __future__ import annotations

import logging
import math

from django.conf import settings

from app_tracker.models import Participant

from . import keyboards, states
from .helpers import send
from .permissions import is_superuser
from .screens import menu_keyboard
from .storage import reset_state, set_state

log = logging.getLogger(__name__)

PAGE_SIZE = keyboards.MODERATORS_PAGE_SIZE


def show_moderators(
    vk,
    participant: Participant,
    state,
    peer_id: int,
    *,
    page: int = 1,
    message_id: int | None = None,
) -> None:
    """Показывает список всех участников; при обновлении правит старое сообщение."""
    if not is_superuser(participant):
        _deny(vk, peer_id, participant)
        return

    people = Participant.objects.order_by("last_name", "first_name", "vk_id")
    total = people.count()
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(1, page), pages)
    start = (page - 1) * PAGE_SIZE
    chunk = list(people[start : start + PAGE_SIZE])

    text = _list_text(total, page, pages)
    keyboard = keyboards.moderators_list(
        chunk,
        page=page,
        pages=pages,
        owner_vk_id=settings.SUPERUSER_VK_ID,
    )

    if message_id:
        try:
            vk.edit_message(peer_id, message_id, text, keyboard=keyboard)
            set_state(state, states.MODERATORS, {"page": page, "message_id": message_id})
            return
        except Exception:
            # Сообщение могли удалить — тогда просто пришлём новое.
            log.warning("Не удалось обновить список модераторов", exc_info=True)

    new_message_id = send(vk, peer_id, text, keyboard)
    set_state(state, states.MODERATORS, {"page": page, "message_id": new_message_id})


def toggle_moderator(
    vk, participant: Participant, state, peer_id: int, target_pk: int
) -> None:
    """Переключает права модератора у выбранного участника."""
    if not is_superuser(participant):
        _deny(vk, peer_id, participant)
        return

    target = Participant.objects.filter(pk=target_pk).first()
    if target is None:
        send(vk, peer_id, "Участник не найден — обнови список.", menu_keyboard(participant))
        return

    target.is_moderator = not target.is_moderator
    target.save(update_fields=["is_moderator"])
    log.info(
        "Права модератора %s у %s",
        "выданы" if target.is_moderator else "сняты",
        target,
    )

    data = dict(state.data or {})
    show_moderators(
        vk,
        participant,
        state,
        peer_id,
        page=int(data.get("page", 1)),
        message_id=data.get("message_id"),
    )


def close_moderators(vk, participant: Participant, state, peer_id: int) -> None:
    """Убирает кнопки из сообщения со списком."""
    if not is_superuser(participant):
        _deny(vk, peer_id, participant)
        return

    data = dict(state.data or {})
    message_id = data.get("message_id")
    reset_state(state)

    text = "Список модераторов закрыт. Открыть снова — кнопка «🛡 Модераторы»."
    if message_id:
        try:
            # Пустая клавиатура убирает inline-кнопки у сообщения.
            vk.edit_message(peer_id, message_id, text, keyboard="")
            return
        except Exception:
            log.warning("Не удалось закрыть список модераторов", exc_info=True)

    send(vk, peer_id, text, menu_keyboard(participant))


def _list_text(total: int, page: int, pages: int) -> str:
    if total == 0:
        return (
            "🛡 МОДЕРАТОРЫ\n"
            "──────────────\n"
            "Пока никого нет: участники появятся, когда напишут боту."
        )
    return "\n".join(
        [
            "🛡 МОДЕРАТОРЫ",
            "──────────────",
            "Нажми на участника, чтобы выдать или снять права.",
            "",
            "🟢 модератор · ⚪ обычный участник",
            f"Страница {page} из {pages} · всего {total}",
        ]
    )


def _deny(vk, peer_id: int, participant: Participant) -> None:
    send(
        vk,
        peer_id,
        "Список модераторов доступен только суперпользователю бота.",
        menu_keyboard(participant),
    )
