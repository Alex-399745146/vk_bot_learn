"""Ежедневная отметка: три вопроса и запись Report."""

from __future__ import annotations

from django.utils import timezone

from . import keyboards, states
from .constants import GOAL_COUNT
from .helpers import send
from app_tracker.models import BotState, Participant, Report
from .screens import expired
from .storage import reset_state, set_state, today_report
from .texts import report_text, report_title


def handle_checkin(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Запускает отметку или сообщает, что день уже закрыт."""
    if not participant.has_goals:
        # Ленивый импорт: onboarding использует экраны, а экраны — его.
        from .onboarding import begin_onboarding

        begin_onboarding(vk, participant, state, peer_id)
        return

    report = today_report(participant)
    if report is not None and report.completed:
        send(
            vk,
            peer_id,
            report_text(participant, report, title=report_title(report, exists=True)),
            keyboards.report_exists(),
        )
        return

    start_report(vk, participant, state, peer_id)


def start_report(vk, participant: Participant, state: BotState, peer_id: int) -> None:
    """Начинает отметку дня: обнуляет индекс и результаты, задаёт первый вопрос."""
    set_state(state, states.REPORTING, {"index": 0, "results": []})
    ask_goal(vk, participant, state, peer_id, 0)


def ask_goal(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    index: int,
) -> None:
    """Отправляет вопрос по цели с номером index и кнопки «Да»/«Нет»."""
    goal = participant.goals[index]
    send(
        vk,
        peer_id,
        f"Цель {index + 1} из {GOAL_COUNT}. {goal}\n\nВыполнено?",
        keyboards.yes_no(),
    )


def answer_report(
    vk,
    participant: Participant,
    state: BotState,
    peer_id: int,
    done: bool,
) -> None:
    """Принимает ответ по цели; после третьего сохраняет Report и показывает итог."""
    if state.state != states.REPORTING:
        expired(vk, participant, peer_id)
        return

    data = dict(state.data or {})
    index = int(data.get("index", 0))
    results = list(data.get("results") or [])
    results.append(done)
    index += 1

    if index < GOAL_COUNT:
        set_state(state, states.REPORTING, {"index": index, "results": results})
        ask_goal(vk, participant, state, peer_id, index)
        return

    report, _ = Report.objects.update_or_create(
        participant=participant,
        date=timezone.localdate(),
        defaults={
            "goal_1_done": results[0],
            "goal_2_done": results[1],
            "goal_3_done": results[2],
        },
    )
    reset_state(state)
    send(
        vk,
        peer_id,
        report_text(participant, report, title=report_title(report, exists=False)),
        keyboards.main_menu(can_checkin=not report.completed),
    )
