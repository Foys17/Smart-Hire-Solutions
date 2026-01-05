from django import forms
from jobs.models import Job
from candidates.models import Application
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

# --- TAILWIND STYLES CONFIGURATION ---
# We define them here to keep the code clean and consistent
INPUT_STYLE = (
    "w-full px-4 py-2 border border-slate-300 rounded-lg "
    "focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 "
    "outline-none transition duration-200 placeholder-slate-400 "
    "bg-white text-slate-700"
)

FILE_INPUT_STYLE = (
    "w-full text-sm text-slate-500 "
    "file:mr-4 file:py-2 file:px-4 "
    "file:rounded-lg file:border-0 "
    "file:text-sm file:font-semibold "
    "file:bg-indigo-50 file:text-indigo-700 "
    "hover:file:bg-indigo-100 cursor-pointer"
)

SELECT_STYLE = (
    "w-full px-4 py-2 border border-slate-300 rounded-lg "
    "focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 "
    "outline-none transition duration-200 bg-white"
)

# -------------------------------------

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'description_text', 'description_file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_STYLE, 
                'placeholder': 'e.g. Senior Backend Engineer'
            }),
            'description_text': forms.Textarea(attrs={
                'class': INPUT_STYLE, 
                'rows': 5, 
                'placeholder': 'Paste the full job description here...'
            }),
            'description_file': forms.FileInput(attrs={
                'class': FILE_INPUT_STYLE
            }),
        }

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cv_file']
        widgets = {
            'cv_file': forms.FileInput(attrs={
                'class': FILE_INPUT_STYLE
            }),
        }

# 1. Login Form (Standard)
class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.TextInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'name@company.com'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': '••••••••'
    }))

# 2. Registration Form (Custom)
class UserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'John Doe'
    }))
    
    role = forms.ChoiceField(
        choices=User.Roles.choices, 
        widget=forms.Select(attrs={'class': SELECT_STYLE})
    )

    class Meta:
        model = User
        fields = ('email', 'full_name', 'role')
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': INPUT_STYLE, 
                'placeholder': 'name@company.com'
            }),
        }

class HRUploadCVForm(forms.Form):
    # Candidate Details
    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'Candidate Name'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'candidate@example.com'
    }))
    
    # File
    cv_file = forms.FileField(widget=forms.FileInput(attrs={
        'class': FILE_INPUT_STYLE
    }))
    
    # Reference Info
    reference_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': INPUT_STYLE, 
            'placeholder': 'Referrer Name (Optional)'
        })
    )


class InterviewInviteForm(forms.Form):
    application_ids = forms.CharField(widget=forms.HiddenInput()) # Stores "1,2,5"
    
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_STYLE}),
        label="Interview Date"
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': INPUT_STYLE}),
        label="Interview Time"
    )
    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': INPUT_STYLE, 
            'placeholder': 'e.g. Google Meet Link or Office Address'
        }),
        label="Location / Link"
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': INPUT_STYLE, 
            'rows': 3, 
            'placeholder': 'Any specific instructions for the candidate...'
        }),
        required=False,
        label="Additional Message"
    )