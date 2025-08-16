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
    venmo_handle = forms.CharField(
        max_length=30,
        required=False,
        help_text="Your Venmo (no @). Letters, numbers, . _ - only."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "venmo_handle")

    def clean_venmo_handle(self):
        val = (self.cleaned_data.get("venmo_handle") or "").strip()
        if val.startswith("@"):
            val = val[1:]
        if val and not VENMO_RE.match(val):
            raise forms.ValidationError("Use letters, numbers, dots, underscores, or dashes (3–30 chars).")
        return val