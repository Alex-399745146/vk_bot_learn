"""Админка: то, что Влад видит в браузере."""

from __future__ import annotations

from django.contrib import admin

from .models import Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "vk_id", "created_at")
    search_fields = ("last_name", "first_name", "vk_id")
    list_filter = ("created_at", "last_name")
    readonly_fields = ("created_at",)
