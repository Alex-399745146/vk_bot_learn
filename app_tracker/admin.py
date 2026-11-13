"""Админка: то, что Влад видит в браузере."""

from __future__ import annotations

from django.contrib import admin

from .models import Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("name", "vk_id", "created_at")
    search_fields = ("name", "vk_id")
    readonly_fields = ("created_at",)
