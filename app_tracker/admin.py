"""Админка: данные участников, состояний и отметок."""

from __future__ import annotations

from django.contrib import admin

from .models import BotState, Participant, Report


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "vk_id",
        "is_moderator",
    )
    search_fields = (
        "last_name",
        "first_name",
        "=vk_id",
    )
    list_filter = ("created_at", "goals_month", "is_moderator")
    list_editable = ("is_moderator",)
    readonly_fields = ("created_at",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("date", "participant", "goals_done", "is_chill", "created_at")
    list_filter = ("date", "is_chill", "goal_1_done", "goal_2_done", "goal_3_done")
    search_fields = ("participant__last_name", "participant__first_name")
    list_select_related = ("participant",)
    date_hierarchy = "date"


@admin.register(BotState)
class BotStateAdmin(admin.ModelAdmin):
    list_display = ("vk_id", "state", "updated_at")
    list_filter = ("state",)
    readonly_fields = ("vk_id", "state", "data", "updated_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
