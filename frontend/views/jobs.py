from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from jobs.models import Job
from candidates.models import Application
from jobs.utils import run_ai_pipeline
from frontend.forms import JobForm
from django.db.models import Q
from django.contrib.auth import get_user_model

def job_list(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    client_id = request.GET.get('client', '') # <--- NEW: Get client filter
    
    # 1. Start with ONLY 'OPEN' jobs
    jobs = Job.objects.filter(status='OPEN') 

    # 2. Apply Search Filters
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) | 
            Q(description_text__icontains=query) |
            Q(skills_required__icontains=query) 
        )
    
    if location:
        jobs = jobs.filter(location__icontains=location) 

    # --- NEW: CLIENT FILTER ---
    if client_id:
        jobs = jobs.filter(client_contact_id=client_id)
    
    # Organize: Sort by Client Name first, then Date
    jobs = jobs.order_by('client_contact__full_name', '-created_at')

    # --- NEW: FETCH CLIENT LIST FOR DROPDOWN ---
    # Only get users who are clients AND have at least one open job
    User = get_user_model()
    clients = User.objects.filter(
        role='Client', 
        posted_jobs__status='OPEN'
    ).distinct().values('id', 'full_name')
    # -------------------------------------------

    # --- CHECK CANDIDATE STATUS (Existing Logic) ---
    if request.user.is_authenticated and request.user.role == 'Candidate':
        user_applications = Application.objects.filter(candidate=request.user).values('job_id', 'status')
        apps_map = {app['job_id']: app['status'] for app in user_applications}
        
        jobs_list = []
        for job in jobs:
            job.current_user_status = apps_map.get(job.id) 
            jobs_list.append(job)
        jobs = jobs_list
    # -----------------------------------------------

    context = {
        'jobs': jobs, 
        'query': query,
        'location': location,
        'selected_client': client_id, # Pass back to keep dropdown selected
        'clients': clients            # Pass list to template
    }
    return render(request, 'job_list.html', context)

def job_detail(request, pk):  
    job = get_object_or_404(Job, pk=pk)
    
    # SECURITY: Prevent direct access to 'Pending' jobs
    if job.status == 'REQUESTED':
        is_owner = (request.user.is_authenticated and job.client_contact == request.user)
        is_hr = (request.user.is_authenticated and request.user.role in ['HR', 'Admin'])
        
        if not (is_owner or is_hr):
            messages.error(request, "This job is currently pending approval.")
            return redirect('web_test:job_list')

    # OPTIONAL: Pass status to detail view too if you want the button there to update as well
    if request.user.is_authenticated and request.user.role == 'Candidate':
        application = Application.objects.filter(candidate=request.user, job=job).first()
        if application:
            job.current_user_status = application.status

    return render(request, 'job_detail.html', {'job': job})

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
            run_ai_pipeline(job)
            messages.success(request, "Job posted and AI processed!")
            return redirect('web_test:job_list')
    else:
        form = JobForm()
    return render(request, 'create_job.html', {'form': form})

@login_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if request.user.role not in ['HR', 'Reviewer']:
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES, instance=job) 
        if form.is_valid():
            job = form.save(commit=False)
            job.save()
            messages.success(request, "Job updated successfully!")
            return redirect('web_test:job_detail', pk=job.pk)
    else:
        form = JobForm(instance=job)

    return render(request, 'edit_job.html', {'form': form, 'job': job})

@login_required
def delete_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    if request.user.role not in ['HR', 'Reviewer']:
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')
        
    if request.method == 'POST':
        title = job.title
        job.delete()
        messages.success(request, f"Job '{title}' has been deleted.")
        return redirect('web_test:job_list')
    
    return render(request, 'delete_job_confirm.html', {'job': job})

@login_required
def toggle_job_status(request, pk):
    """
    Switches job between OPEN and CLOSED.
    Closing a job now REJECTS all non-shortlisted candidates instead of deleting them.
    """
    job = get_object_or_404(Job, pk=pk)
    
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if job.status == 'OPEN':
        job.status = 'CLOSED'
        count = Application.objects.filter(job=job).exclude(status='REJECTED').update(status='REJECTED')
        messages.info(request, f"Job CLOSED. {count} active application(s) marked as Rejected.")
    else:
        job.status = 'OPEN'
        messages.success(request, "Job Re-Opened! Candidates can apply again.")
    
    job.save()
    return redirect('web_test:job_detail', pk=job.pk)


@login_required
def hr_pending_requests(request):
    """Shows all jobs with status='REQUESTED' for HR to review."""
    if request.user.role not in ['HR', 'Admin']:
        return redirect('web_test:home')
        
    pending_jobs = Job.objects.filter(status='REQUESTED').order_by('-created_at')
    return render(request, 'hr/pending_requests.html', {'jobs': pending_jobs})

@login_required
def hr_approve_request(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    
    if request.user.role not in ['HR', 'Admin']:
        return redirect('web_test:home')
        
    job.status = 'OPEN'
    job.posted_by = request.user # Assign the HR who approved it as the owner
    job.save()
    
    # Run AI Pipeline now that it is approved
    run_ai_pipeline(job)
    
    messages.success(request, f"Job '{job.title}' is now LIVE and Candidates can apply!")
    return redirect('web_test:job_list')

@login_required
def hr_reject_request(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.user.role not in ['HR', 'Admin']: return redirect('web_test:home')
    
    job.delete() # Or set status='REJECTED' if you want to keep record
    messages.info(request, "Job request rejected and removed.")
    return redirect('web_test:hr_pending_requests')