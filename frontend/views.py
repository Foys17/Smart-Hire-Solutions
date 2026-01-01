from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, logout
from jobs.models import Job
from jobs.utils import run_ai_pipeline  # Import your AI logic
from candidates.models import Application
from candidates.utils import process_application # Import your AI logic
from .forms import JobForm, ApplicationForm, UserLoginForm, UserRegistrationForm
from django.http import HttpResponseForbidden

@login_required
def dashboard(request):
    """Landing page showing buttons based on Role."""
    return render(request, 'dashboard.html')

@login_required
def job_list(request):
    """Show all jobs. Candidates can apply here."""
    jobs = Job.objects.all().order_by('-created_at')
    return render(request, 'job_list.html', {'jobs': jobs})

@login_required
def create_job(request):
    """HR Only: Post a job."""
    if request.user.role != 'HR':
        messages.error(request, "Only HR can post jobs.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            
            # TRIGGER AI PIPELINE
            run_ai_pipeline(job)
            
            messages.success(request, "Job posted and AI processed!")
            return redirect('web_test:job_list')
    else:
        form = JobForm()
    return render(request, 'create_job.html', {'form': form})

@login_required
def apply_for_job(request, job_id):
    """Candidate: Upload CV."""
    job = get_object_or_404(Job, pk=job_id)
    
    # Check if already applied
    if Application.objects.filter(candidate=request.user, job=job).exists():
        messages.warning(request, "You have already applied!")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.candidate = request.user
            app.job = job
            app.save()
            
            # TRIGGER AI PIPELINE
            process_application(app)
            
            messages.success(request, f"Applied to {job.title}. AI Score Calculated!")
            return redirect('web_test:job_list')
    else:
        form = ApplicationForm()
    
    return render(request, 'apply_job.html', {'form': form, 'job': job})

@login_required
def job_ranking(request, job_id):
    """HR Only: See ranked candidates."""
    job = get_object_or_404(Job, pk=job_id)
    
    # Filter by Reference if query param exists (?ref=true)
    apps = Application.objects.filter(job=job)
    if request.GET.get('ref'):
        apps = apps.filter(has_reference=True)
        
    # Order by Match Score
    apps = apps.order_by('-match_score')
    
    return render(request, 'ranking.html', {'job': job, 'applications': apps})


def register_view(request):
    """Handles User Registration"""
    if request.user.is_authenticated:
        return redirect('web_test:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after register
            messages.success(request, f"Welcome, {user.full_name}!")
            return redirect('web_test:dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    """Handles User Login"""
    if request.user.is_authenticated:
        return redirect('web_test:dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('web_test:dashboard')
    else:
        form = UserLoginForm()

    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('web_test:login')


@login_required
def job_detail(request, pk):
    """
    Shows full job info AND the AI 'Brain' (Extracted Entities).
    """
    job = get_object_or_404(Job, pk=pk)
    return render(request, 'job_detail.html', {'job': job})

@login_required
def job_edit(request, pk):
    """
    Allows HR or Reviewer to edit the job.
    """
    job = get_object_or_404(Job, pk=pk)

    # Security Check: Only HR or Reviewer can edit
    if request.user.role not in ['HR', 'Reviewer']:
        messages.error(request, "You are not authorized to edit this job.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES, instance=job)
        if form.is_valid():
            job = form.save(commit=False)
            # Optional: Re-run AI if description changed
            # run_ai_pipeline(job) 
            job.save()
            messages.success(request, "Job updated successfully!")
            return redirect('web_test:job_detail', pk=job.pk)
    else:
        form = JobForm(instance=job)

    return render(request, 'edit_job.html', {'form': form, 'job': job})


@login_required
def application_detail(request, pk):
    """
    HR Only: View deep dive of a candidate's application.
    Shows the exact entities GLiNER extracted from their CV.
    """
    application = get_object_or_404(Application, pk=pk)
    
    # Security: Only HR (or the candidate themselves) should see this
    if request.user.role != 'HR' and request.user != application.candidate:
        messages.error(request, "Access Denied.")
        return redirect('web_test:dashboard')
        
    return render(request, 'application_detail.html', {'app': application})