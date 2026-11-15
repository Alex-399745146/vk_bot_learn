"""Регистрация, вход и страница результатов."""

from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format

from app_tracker.models import Participant

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
    """Публичная инструкция: как работает бот и веб-кабинет."""
    return render(request, "app_users/help.html")


@login_required
def dashboard(request):
    """Показывает цели, сегодняшнюю отметку и последние результаты."""
    profile = getattr(request.user, "profile", None)
    participant = profile.participant if profile else None

    context: dict = {"participant": participant}
    if participant is None:
        return render(request, "app_users/dashboard.html", context)

    today = timezone.localdate()
    month_reports = participant.reports.filter(
        date__year=today.year, date__month=today.month
    )
    chill_total = month_reports.filter(is_chill=True).count()
    goal_reports = month_reports.filter(is_chill=False)
    total = goal_reports.count()
    completed = goal_reports.filter(
        goal_1_done=True, goal_2_done=True, goal_3_done=True
    ).count()

    context.update(
        {
            "goals": participant.goals if participant.has_goals else [],
            "goals_month_label": _month_label(participant.goals_month or _month_key(today)),
            "today_report": participant.reports.filter(date=today).first(),
            "reports": participant.reports.order_by("-date")[:14],
            "month_total": total,
            "month_completed": completed,
            "month_partial": total - completed,
            "month_chill": chill_total,
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


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def _month_label(month_key: str) -> str:
    try:
        year, month = (int(part) for part in month_key.split("-"))
        day = date(year, month, 1)
    except (ValueError, TypeError):
        return month_key
    return date_format(day, "F Y").capitalize()
