"""Админка: то, что видит человек в браузере."""

from __future__ import annotations

from django.contrib import admin

from .models import BotState, Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "habit", "refusal", "vk_id", "created_at")
    search_fields = ("last_name", "first_name", "habit", "refusal", "vk_id")
    list_filter = ("created_at", "last_name")
    readonly_fields = ("created_at",)


@admin.register(BotState)
class BotStateAdmin(admin.ModelAdmin):
    list_display = ("vk_id", "state", "updated_at")
    list_filter = ("state",)
    readonly_fields = ("vk_id", "state", "data", "updated_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
