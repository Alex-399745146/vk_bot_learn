"""Админка: данные участников, состояний и отметок."""

from __future__ import annotations

from django.contrib import admin

from .models import BotState, Participant, Report


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "goal_1",
        "goal_2",
        "goal_3",
        "vk_id",
    )
    search_fields = ("last_name", "first_name", "goal_1", "goal_2", "goal_3", "vk_id")
    list_filter = ("created_at", "last_name")
    readonly_fields = ("created_at",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("date", "participant", "goals_done", "created_at")
    list_filter = ("date", "goal_1_done", "goal_2_done", "goal_3_done")
    search_fields = ("participant__last_name", "participant__first_name")
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
