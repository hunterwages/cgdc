# core/forms.py
from django import forms
from .models import Pick

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
import re

class PickForm(forms.ModelForm):
    class Meta:
        model = Pick
        fields = ['selection']
        widgets = {
            'selection': forms.RadioSelect(choices=Pick.SELECTION)
        }

VENMO_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")

class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label="First name")
    last_name  = forms.CharField(max_length=30, required=True, label="Last name")
    venmo_handle = forms.CharField(max_length=50, required=False, label="Venmo handle")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "venmo_handle", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={
                "autofocus": True,
                "placeholder": "e.g. hunterwages97",
                "autocomplete": "username",
            }),
            "first_name": forms.TextInput(attrs={"placeholder": "Hunter", "autocomplete": "given-name"}),
            "last_name":  forms.TextInput(attrs={"placeholder": "Wages",  "autocomplete": "family-name"}),
            "venmo_handle": forms.TextInput(attrs={"placeholder": "no @ (e.g. hunterwages)"}),
            "password1": forms.PasswordInput(attrs={"autocomplete": "new-password"}),
            "password2": forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        }

    def clean_venmo_handle(self):
        v = self.cleaned_data.get("venmo_handle", "")
        return v.lstrip("@").strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name  = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
        return user