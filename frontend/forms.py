from django import forms
from jobs.models import Job
from candidates.models import Application
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from employees.models import Employee, Payroll, LeaveRequest


User = get_user_model()

# --- TAILWIND STYLES CONFIGURATION ---
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

    def clean(self):
        cleaned_data = super().clean()
        desc_text = cleaned_data.get('description_text')
        desc_file = cleaned_data.get('description_file')

        if not desc_text and not desc_file:
            raise forms.ValidationError("You must provide either Job Description Text OR upload a PDF file.")

        if desc_text and desc_file:
            raise forms.ValidationError("Please provide ONLY one source: either paste Text OR upload a File, not both.")

        return cleaned_data


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cv_file']
        widgets = {
            'cv_file': forms.FileInput(attrs={
                'class': FILE_INPUT_STYLE
            }),
        }

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.TextInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'name@company.com'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': '••••••••'
    }))

class UserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'Mahedy Hasan'
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
    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'Candidate Name'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': INPUT_STYLE, 
        'placeholder': 'candidate@example.com'
    }))
    cv_file = forms.FileField(widget=forms.FileInput(attrs={
        'class': FILE_INPUT_STYLE
    }))
    reference_name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': INPUT_STYLE, 
            'placeholder': 'Referrer Name (Optional)'
        })
    )

class InterviewInviteForm(forms.Form):
    application_ids = forms.CharField(widget=forms.HiddenInput())
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

class CVBuilderForm(forms.Form):
    # Removed Experience, Education, Projects textareas to use dynamic list inputs instead
    full_name = forms.CharField(
        label="Full Name", 
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Jane Doe'})
    )
    email = forms.EmailField(
        label="Email", 
        widget=forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'jane@example.com'})
    )
    phone = forms.CharField(
        label="Phone Number", 
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': '+1 234 567 890'})
    )
    location = forms.CharField(
        label="Location", 
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'City, Country'})
    )
    linkedin = forms.URLField(
        label="LinkedIn URL", 
        required=False, 
        widget=forms.URLInput(attrs={'class': INPUT_STYLE, 'placeholder': 'https://linkedin.com/in/jane'})
    )
    
    summary = forms.CharField(
        label="Professional Summary", 
        widget=forms.Textarea(attrs={'class': INPUT_STYLE, 'rows': 4, 'placeholder': 'Brief overview of your skills and experience...'})
    )
    
    skills = forms.CharField(
        label="Skills (Comma separated)", 
        widget=forms.Textarea(attrs={'class': INPUT_STYLE, 'rows': 3, 'placeholder': 'Python, Django, AWS, React...'})
    )


class EmployeeCreationForm(forms.ModelForm):
    full_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-300'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'w-full rounded-lg border-slate-300'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full rounded-lg border-slate-300'}))
    
    class Meta:
        model = Employee
        fields = ['department', 'designation', 'phone_number']
        widgets = {
            'department': forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'designation': forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full rounded-lg border-slate-300'}),
        }

class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['employee', 'month', 'basic_salary', 'bonuses', 'deductions', 'is_paid']
        widgets = {
            'employee': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'month': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-lg border-slate-300'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'bonuses': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'deductions': forms.NumberInput(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'rounded text-indigo-600 focus:ring-indigo-500'}),
        }

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-300'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-lg border-slate-300'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-lg border-slate-300'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-lg border-slate-300'}),
        }