from django import forms
from jobs.models import Job
from candidates.models import Application
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'description_text', 'description_file']
        widgets = {
            'description_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cv_file']
        widgets = {
            'cv_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

# 1. Login Form (Standard)
class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

# 2. Registration Form (Custom)
class UserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    role = forms.ChoiceField(choices=User.Roles.choices, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ('email', 'full_name', 'role')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }