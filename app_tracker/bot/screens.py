"""Экраны: меню, справка, ответ на устаревшую кнопку."""

from __future__ import annotations

from django.utils import timezone

from . import keyboards
from .constants import CHILL_LIMIT
from .helpers import send
from app_tracker.models import BotState, GoalPeriod, Participant
from app_tracker.periods import (
    is_goals_window,
    is_work_period,
    month_key,
    period_label,
    target_goals_month,
    work_month,
)
from .storage import (
    chill_count,
    period_points,
    reset_state,
    sync_period_goals,
    today_report,
)
from .texts import HELP_TEXT, goals_bulletin


def _menu_flags(participant: Participant, report, day) -> tuple[bool, int, int]:
    """Возвращает (можно_отметиться, остаток Chill, использовано Chill)."""
    used = chill_count(participant, day)

    if not is_work_period(day) or not participant.has_goals:
        return False, 0, used

    if report is None:
        can_checkin = True
    else:
        can_checkin = not report.completed and not report.is_chill

    can_chill = report is None and used < CHILL_LIMIT
    chill_left = CHILL_LIMIT - used if can_chill else 0
    return can_checkin, chill_left, used


def show_menu(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    *,
    intro: str | None = None,
) -> None:
    """Показывает карточку и меню по состоянию периода."""
    reset_state(state)
    sync_period_goals(participant)

    day = timezone.localdate()
    report = today_report(participant)
    can_checkin, chill_left, _ = _menu_flags(participant, report, day)

    send(
        vk,
        peer_id,
        _menu_card(participant, report, day, intro),
        keyboards.main_menu(
            can_checkin=can_checkin,
            chill_left=chill_left,
            can_edit=is_goals_window(day),
        ),
    )


def _menu_card(
    participant: Participant,
    report,
    day,
    intro: str | None = None,
) -> str:
    """Собирает карточку-бюллетень для раздела «Мои цели»."""
    lines = ["🌋 ТВОЙ ДНЕВНИК", "──────────────"]

    if intro:
        lines += [f"✨ {intro}", ""]

    working = is_work_period(day)

    if working and participant.has_goals:
        points = period_points(participant, day)
        used = chill_count(participant, day)

        lines += [
            goals_bulletin(participant.goals, participant.goals_month),
            "",
            "📊 Итоги периода",
            f"⭐ Баллы: {points}",
        ]

        if report is None:
            lines.append(f"❄️ Chill: доступно {CHILL_LIMIT - used} из {CHILL_LIMIT}")
        else:
            lines.append(f"❄️ Chill: использовано {used} из {CHILL_LIMIT}")

        lines.append("")

        if report is None:
            lines.append("⏳ Сегодня ещё не отмечено · до 00:00 по Москве")
        elif report.is_chill:
            lines.append("🌀 Сегодня Chill · отметка закрыта до завтра")
        elif report.completed:
            lines.append("✅ Сегодня все три цели выполнены · новая отметка завтра")
        else:
            lines.append(f"🟡 Сегодня отмечено {report.goals_done} из 3 · можно дополнить")

        if is_goals_window(day):
            lines += ["", "🎯 Окно целей открыто: можно поставить цели на следующий период."]

    elif working:
        target = target_goals_month(day)
        lines += [
            f"🎯 Рабочий период {period_label(month_key(day))} уже идёт.",
            "",
            "⚠️ Цели на этот период не поставлены.",
        ]
        if is_goals_window(day):
            lines.append("Сегодня последний день окна — поставь цели кнопкой ниже.")
        else:
            lines.append("Окно целей откроется 28-го числа.")

    else:
        target = target_goals_month(day)
        planned = GoalPeriod.objects.filter(
            participant=participant, month=target, status="active"
        ).first()

        lines += ["💤 Перерыв между периодами.", ""]

        if planned:
            lines += [
                goals_bulletin(planned.goals, target),
                "",
                "✅ Цели сохранены — период начнётся 3-го.",
            ]
        else:
            lines += [
                f"🎯 Цели на период {period_label(target)} ещё не поставлены.",
                "Окно открыто: поставь три цели до 3-го.",
            ]

        if participant.goals_month:
            lines += [
                "",
                f"📊 Прошлый период: ⭐ {period_points(participant, day)} баллов",
            ]

    lines += [
        "",
        "──────────────",
        f"🆔 VK ID: {participant.vk_id} · для регистрации на сайте",
    ]

    return "\n".join(lines)


def menu_keyboard(participant: Participant) -> str:
    """Меню, учитывающее период, отметку за сегодня и остаток Chill."""
    sync_period_goals(participant)
    day = timezone.localdate()
    report = today_report(participant)
    can_checkin, chill_left, _ = _menu_flags(participant, report, day)
    return keyboards.main_menu(
        can_checkin=can_checkin,
        chill_left=chill_left,
        can_edit=is_goals_window(day),
    )


def show_help(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Показывает справку и актуальное меню."""
    reset_state(state)
    send(vk, peer_id, HELP_TEXT, menu_keyboard(participant))


def expired(vk, participant: Participant, peer_id: int) -> None:
    """Отвечает на устаревшую кнопку и показывает актуальное меню."""
    send(vk, peer_id, "Это сообщение устарело.", menu_keyboard(participant))


def no_goals_hint(participant: Participant) -> str:
    """Почему нельзя отметиться: перерыв или окно целей закрыто."""
    day = timezone.localdate()
    if not is_work_period(day):
        target = target_goals_month(day)
        return (
            f"Сейчас перерыв. Цели на период {period_label(target)} можно "
            "поставить в окне с 28 по 3 число."
        )
    if is_goals_window(day):
        return "Цели ещё не поставлены. Сегодня последний день окна — поставь их."
    return "Цели на этот период не поставлены. Окно откроется 28-го числа."
