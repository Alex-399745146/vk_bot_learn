"""Регистрация, вход и страница результатов."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from app_tracker.bot.constants import (
    CHILL_LIMIT,
    LIMIT_PAUSE,
    ON_PERIOD_GOALS_END,
    ON_PERIOD_GOALS_START,
    ON_PERIOD_WORK_END,
    ON_PERIOD_WORK_START,
)
from app_tracker.bot.storage import sync_period_goals
from app_tracker.models import GoalPeriod, Participant
from app_tracker.periods import (
    is_goals_window,
    period_label,
    target_goals_month,
    work_bounds,
    work_month,
)

from .forms import LoginForm, RegisterForm


class UserLoginView(LoginView):
    template_name = "app_users/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("login")


def register(request):
    """Создаёт пользователя и привязывает его к существующему участнику бота."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
            login(request, user)
            messages.success(request, "Готово! Аккаунт создан.")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "app_users/register.html", {"form": form})


def help_page(request):
    """Публичная инструкция: периоды, цели, отметки и Chill."""
    profile = getattr(request.user, "profile", None)
    participant = profile.participant if profile else None

    return render(
        request,
        "app_users/help.html",
        {
            "participant": participant,
            "work_start": ON_PERIOD_WORK_START,
            "work_end": ON_PERIOD_WORK_END,
            "goals_start": ON_PERIOD_GOALS_START,
            "goals_end": ON_PERIOD_GOALS_END,
            "chill_limit": CHILL_LIMIT,
            "pause_limit": LIMIT_PAUSE,
        },
    )


@login_required
def dashboard(request):
    """Показывает цели периода, сегодняшнюю отметку и последние результаты."""
    profile = getattr(request.user, "profile", None)
    participant = profile.participant if profile else None

    context: dict = {"participant": participant}
    if participant is None:
        return render(request, "app_users/dashboard.html", context)

    today = timezone.localdate()
    sync_period_goals(participant, today)

    work = work_month(today)
    target = target_goals_month(today)
    window = is_goals_window(today)

    planned = None
    if work is None:
        planned = GoalPeriod.objects.filter(
            participant=participant, month=target, status="active"
        ).first()

    paused = GoalPeriod.objects.filter(
        participant=participant, month=work or target, status="paused"
    ).exists()

    if paused:
        goals = []
        label = period_label(work or target)
    elif work and participant.has_goals:
        goals = participant.goals
        label = period_label(work)
    elif work is None and planned:
        goals = planned.goals
        label = period_label(target)
    else:
        goals = []
        label = period_label(work or participant.goals_month or target)

    stats_month = work or participant.goals_month
    if paused:
        period_reports = participant.reports.none()
    elif stats_month:
        start, end = work_bounds(stats_month)
        period_reports = participant.reports.filter(date__range=(start, end))
    else:
        period_reports = participant.reports.none()

    chill_total = period_reports.filter(is_chill=True).count()
    goal_reports = period_reports.filter(is_chill=False)
    total = goal_reports.count()
    completed = goal_reports.filter(
        goal_1_done=True, goal_2_done=True, goal_3_done=True
    ).count()

    context.update(
        {
            "goals": goals,
            "period_label": label,
            "work_active": work is not None,
            "paused": paused,
            "goals_window": window,
            "target_period_label": period_label(target),
            "today_report": participant.reports.filter(date=today).first() if work else None,
            "reports": participant.reports.order_by("-date")[:14],
            "period_total": total,
            "period_completed": completed,
            "period_partial": total - completed,
            "period_chill": chill_total,
            "streak": _streak(participant),
        }
    )
    return render(request, "app_users/dashboard.html", context)


def _streak(participant: Participant) -> int:
    """Сколько последних отметок подряд были полными (3 из 3)."""
    streak = 0
    for report in participant.reports.order_by("-date"):
        if not report.completed:
            break
        streak += 1
    return streak
