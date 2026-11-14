"""Форма регистрации: стандартный пользователь + привязка к участнику бота."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from app_tracker.models import Participant

from .models import Profile


class BootstrapFormMixin:
    """Добавляет Bootstrap-классы всем полям формы."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            else:
                css = "form-control"
            field.widget.attrs["class"] = f"{field.widget.attrs.get('class', '')} {css}".strip()


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    vk_id = forms.IntegerField(
        label="VK ID",
        help_text="Числовой ID твоей страницы ВКонтакте. Должен совпадать с тем, "
        "с которого ты уже писал боту.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)
        labels = {"username": "Логин"}

    def clean_vk_id(self) -> int:
        vk_id = int(self.cleaned_data["vk_id"])
        participant = Participant.objects.filter(vk_id=vk_id).first()

        if participant is None:
            raise forms.ValidationError(
                "Участник с таким VK ID не найден. Сначала напиши боту /start."
            )
        if Profile.objects.filter(participant=participant).exists():
            raise forms.ValidationError(
                "Этот VK ID уже привязан к другому веб-аккаунту."
            )

        self.participant = participant
        return vk_id

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        if commit:
            user.save()
            Profile.objects.create(user=user, participant=self.participant)
        return user
