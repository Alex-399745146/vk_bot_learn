"""Админка профилей."""

from __future__ import annotations

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "participant", "created_at")
    search_fields = ("user__username", "participant__last_name", "participant__first_name")
    list_select_related = ("user", "participant")
    autocomplete_fields = ("participant",)
