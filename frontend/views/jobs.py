from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from jobs.models import Job
from candidates.models import Application
from jobs.utils import run_ai_pipeline
from frontend.forms import JobForm, InterviewInviteForm
from django.db.models import Q
from django.contrib.auth import get_user_model
from users.models import Notification 
from django.urls import reverse
from django.core.mail import send_mail  
from django.conf import settings

def job_list(request):
    query = request.GET.get('q', '')
    client_id = request.GET.get('client', '')
    
    jobs = Job.objects.filter(status='OPEN') 

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) | 
            Q(description_text__icontains=query)
        )
    
    if client_id: 
        jobs = jobs.filter(client_contact_id=client_id)
    
    jobs = jobs.order_by('client_contact__full_name', '-created_at')

    User = get_user_model()
    #Fetch clients for filter dropdown
    clients = User.objects.filter(
        role='Client', 
        client_jobs__status='OPEN' 
    ).distinct().values('id', 'full_name')

    if request.user.is_authenticated and request.user.role == 'Candidate':
        user_applications = Application.objects.filter(candidate=request.user).values('job_id', 'status')
        apps_map = {app['job_id']: app['status'] for app in user_applications}
        
        jobs_list = []
        for job in jobs:
            job.current_user_status = apps_map.get(job.id) 
            jobs_list.append(job)
        jobs = jobs_list

    context = {
        'jobs': jobs, 
        'query': query,
        'selected_client': client_id,
        'clients': clients
    }
    return render(request, 'job_list.html', context)

def job_detail(request, pk):  
    job = get_object_or_404(Job, pk=pk)
    
    if job.status == 'REQUESTED':
        is_owner = (request.user.is_authenticated and job.client_contact == request.user)
        is_hr = (request.user.is_authenticated and request.user.role in ['HR', 'Admin'])
        
        if not (is_owner or is_hr):
            messages.error(request, "This job is currently pending approval.")
            return redirect('web_test:job_list')

    if request.user.is_authenticated and request.user.role == 'Candidate':
        application = Application.objects.filter(candidate=request.user, job=job).first()
        if application:
            job.current_user_status = application.status

    return render(request, 'job_detail.html', {'job': job})

@login_required
def create_job(request):
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
def toggle_job_status(request, pk):  #Open / Close job
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
def hr_pending_requests(request):  #HR sees client job requests
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
    job.posted_by = request.user 
    job.save()
    
    run_ai_pipeline(job)
    
    if job.client_contact:
        Notification.objects.create(
            user=job.client_contact,
            message=f"Good news! Your job request '{job.title}' has been APPROVED and is now live.",
            link=reverse('web_test:client_job_view', args=[job.id])
        )
    
    messages.success(request, f"Job '{job.title}' is now LIVE and Candidates can apply!")
    return redirect('web_test:job_list')

@login_required
def hr_reject_request(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.user.role not in ['HR', 'Admin']: return redirect('web_test:home')
    
    job_title = job.title
    client = job.client_contact
    
    job.delete() 

    if client:
        Notification.objects.create(
            user=client,
            message=f"Update regarding '{job_title}': This request was declined by HR. Please contact us for details.",
            link='#' 
        )

    messages.info(request, "Job request rejected and removed.")
    return redirect('web_test:hr_pending_requests')


@login_required
def hr_schedule_interview(request):
    """
    Handles bulk interview scheduling.
    HR selects candidates -> Assigns Reviewer -> System notifies everyone.
    """
    if request.user.role not in ['HR', 'Admin']:
        messages.error(request, "Access Denied")
        return redirect('web_test:home')

    apps = Application.objects.none()
    single_app = None

    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            app_ids = form.cleaned_data['application_ids'].split(',')
            reviewer = form.cleaned_data['reviewer']
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            location = form.cleaned_data['location']
            message = form.cleaned_data['message']

            applications = Application.objects.filter(id__in=app_ids)
            count = applications.count()

            #Bulk Update & Notifications
            for app in applications:
                # Update Status & Reviewer
                app.status = 'INTERVIEW'
                app.assigned_reviewer = reviewer
                
                app.interview_date = f"{date} {time}" 
                app.interview_location = location  
                app.interview_note = message       
                app.save()

                # A. Notify Candidate (Dashboard)
                Notification.objects.create(
                    user=app.candidate,
                    message=f"Interview Scheduled! Date: {date} at {time}. Check details.",
                    link=reverse('web_test:candidate_job_status', args=[app.job.id]) # <--- Changed link
                )

                # B. Notify Candidate (Email)
                try:
                    send_mail(
                        subject=f"Interview Invitation - {app.job.title}",
                        message=f"Hello {app.candidate.full_name},\n\n"
                                f"You have been selected for an interview.\n"
                                f"Date: {date}\nTime: {time}\nLink/Location: {location}\n\n"
                                f"Message: {message}\n\nGood luck!",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[app.candidate.email],
                        fail_silently=True
                    )
                except Exception:
                    pass 

            # 4. Notify Reviewer (One summary notification)
            Notification.objects.create(
                user=reviewer,
                message=f"New Assignment: You have {count} new candidates to interview on {date}.",
                link=reverse('web_test:reviewer_dashboard')
            )

            messages.success(request, f"Successfully scheduled interviews for {count} candidates.")
            return redirect('web_test:kanban_board')
        
        # If form is invalid, restore 'apps' for display
        ids = request.POST.get('application_ids', '')
        if ids:
            id_list = ids.split(',')
            apps = Application.objects.filter(id__in=id_list)
            single_app = apps.first() if apps.count() == 1 else None

    else:
        # GET request
        ids = request.GET.get('ids', '')
        form = InterviewInviteForm(initial={'application_ids': ids})
        
        id_list = ids.split(',') if ids else []
        apps = Application.objects.filter(id__in=id_list)
        single_app = apps.first() if len(apps) == 1 else None

    return render(request, 'hr/schedule_interview.html', {
        'form': form,
        'apps': apps,
        'app': single_app 
    })