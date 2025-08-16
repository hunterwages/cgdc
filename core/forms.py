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
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    venmo_handle = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'venmo_handle', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user