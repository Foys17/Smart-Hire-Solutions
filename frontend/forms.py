from django import forms
from jobs.models import Job, Question
from candidates.models import Application
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from reviewer.models import InterviewScore

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
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Full Name'}))
    
    # Role Selection (Candidate or Client)
    role = forms.ChoiceField(
        choices=[('Candidate', 'Candidate'), ('Client', 'Client')],
        widget=forms.Select(attrs={'class': SELECT_STYLE})
    )

    class Meta:
        model = User
        fields = ('email', 'full_name', 'role') 
        widgets = {
            'email': forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'name@company.com'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        # Role is saved from the form data automatically if included in fields, 
        # but we explicitly save user to ensure commit logic holds
        if commit:
            user.save()
        return user

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
    reviewer = forms.ModelChoiceField(
        queryset=User.objects.filter(role='Reviewer'), # Now this will find your user!
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all'}),
        label="Assign Reviewer",
        required=True,
        empty_label="Select a Team Member"
    )
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


# --- CLIENT REQUEST FORM (UPDATED WITH VALIDATION) ---
class ClientJobRequestForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title', 'description_text', 'description_file', 
            'target_candidates_count', 'client_does_final_interview',
            'has_primary_exam', 'exam_passing_score'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT_STYLE}),
            'description_text': forms.Textarea(attrs={'class': INPUT_STYLE, 'rows': 4}),
            'description_file': forms.FileInput(attrs={'class': FILE_INPUT_STYLE}),
            'target_candidates_count': forms.NumberInput(attrs={'class': INPUT_STYLE}),
            'exam_passing_score': forms.NumberInput(attrs={'class': INPUT_STYLE, 'placeholder': '60'}),
        }

    # --- ADDED VALIDATION LOGIC ---
    def clean(self):
        cleaned_data = super().clean()
        desc_text = cleaned_data.get('description_text')
        desc_file = cleaned_data.get('description_file')

        if not desc_text and not desc_file:
            raise forms.ValidationError("You must provide either Job Description Text OR upload a PDF file.")

        if desc_text and desc_file:
            raise forms.ValidationError("Please provide ONLY one source: either paste Text OR upload a File, not both.")

        return cleaned_data


# --- QUESTION ADDITION FORM ---
class QuestionForm(forms.ModelForm):
    # We manually create fields for the 4 options to make it easy for the client
    option_1 = forms.CharField(widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Option A'}))
    option_2 = forms.CharField(widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Option B'}))
    option_3 = forms.CharField(widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Option C'}))
    option_4 = forms.CharField(widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Option D'}))
    
    correct_option = forms.ChoiceField(
        choices=[('0', 'Option A'), ('1', 'Option B'), ('2', 'Option C'), ('3', 'Option D')],
        widget=forms.Select(attrs={'class': SELECT_STYLE})
    )

    class Meta:
        model = Question
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': INPUT_STYLE, 'rows': 2, 'placeholder': 'Enter the Question Text here...'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = InterviewScore
        fields = [
            'technical_score', 
            'communication_score', 
            'problem_solving_score', 
            'cultural_fit_score', 
            'comments'
        ]
        widgets = {
            'technical_score': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': 1, 'max': 10, 'placeholder': '1-10'}),
            'communication_score': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': 1, 'max': 10, 'placeholder': '1-10'}),
            'problem_solving_score': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': 1, 'max': 10, 'placeholder': '1-10'}),
            'cultural_fit_score': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': 1, 'max': 10, 'placeholder': '1-10'}),
            'comments': forms.Textarea(attrs={'class': INPUT_STYLE, 'rows': 4, 'placeholder': 'Write your detailed feedback here...'}),
        }