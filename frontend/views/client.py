from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from jobs.models import Job,Question
from candidates.models import Application
from django.db.models import Count, Q
from frontend.forms import ClientJobRequestForm,QuestionForm,ClientScheduleForm, OfferCreationForm
from django.contrib.auth import get_user_model
from django.urls import reverse
from users.models import Notification
from django.utils import timezone
from django.utils.dateparse import parse_datetime

@login_required
def client_dashboard(request):
    if request.user.role != 'Client':
        return redirect('web_test:home')

    # Fetch Jobs with "Ready to Review" counts
    my_jobs = Job.objects.filter(client_contact=request.user).annotate(
        ready_to_review_count=Count('applications', filter=Q(applications__status='CLIENT_REVIEW'))
    ).order_by('-created_at')

    active_count = my_jobs.filter(status='OPEN').count()
    candidates_to_review = Application.objects.filter(job__in=my_jobs, status='CLIENT_REVIEW').count()

    # Fetch Upcoming Final Interviews
    upcoming_interviews = Application.objects.filter(
        job__client_contact=request.user,
        status='FINAL_INTERVIEW',
        interview_date__gte=timezone.now()
    ).select_related('job', 'candidate').order_by('interview_date')

    context = {
        'jobs': my_jobs,
        'active_count': active_count,
        'review_count': candidates_to_review,
        'upcoming_interviews': upcoming_interviews 
    }
    return render(request, 'client/dashboard.html', context)

@login_required
def client_job_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if request.user != job.client_contact: #Client can only view their own job
        return redirect('web_test:client_dashboard')

    # Fetch candidates 
    candidates = Application.objects.filter(
        job=job,
        status__in=[
            'CLIENT_REVIEW', 'FINAL_INTERVIEW', 
            'NEGOTIATION', 'NEGOTIATION_SUBMITTED', 
            'OFFER', 'HIRED', 'REJECTED'
        ]
    ).select_related('candidate').order_by('-match_score')

    return render(request, 'client/review_candidates.html', {
        'job': job, 
        'candidates': candidates
    })

@login_required
def client_decision(request, application_id, decision):
    app = get_object_or_404(Application, id=application_id)
    
    if app.job.client_contact != request.user:
        messages.error(request, "Unauthorized access.")
        return redirect('web_test:client_dashboard')

    if decision == 'approve':
        # Condition A: Job requires Final Interview -> Schedule it
        if app.job.client_does_final_interview and app.status == 'CLIENT_REVIEW':
            return redirect('web_test:client_schedule_interview', application_id=app.id)

        # Condition B: Ready for Offer/Negotiation (Final Interview Done OR Not Required)
        # Start Negotiation instead of sending blank Offer
        app.status = 'NEGOTIATION'
        app.save()

        # Notify Candidate
        Notification.objects.create(
            user=app.candidate,
            message=f"Action Required: {app.job.client_contact.full_name} is interested! Please review salary & joining details.",
            link=reverse('web_test:candidate_negotiation', args=[app.id]) 
        )
        
        messages.success(request, f"Request sent to {app.candidate.full_name} to confirm Salary & Joining Date.")
        return redirect('web_test:client_job_view', job_id=app.job.id)

    elif decision == 'reject':
        app.status = 'REJECTED'
        messages.info(request, f"Marked {app.candidate.full_name} as not a fit.")
        app.save()
    
    return redirect('web_test:client_job_view', job_id=app.job.id)

@login_required
def client_create_offer(request, application_id):
    app = get_object_or_404(Application, id=application_id)
    
    if app.job.client_contact != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:client_dashboard')

    if request.method == 'POST':
        form = OfferCreationForm(request.POST)
        if form.is_valid():
            app.offer_salary = form.cleaned_data['salary']
            app.offer_start_date = form.cleaned_data['start_date']
            app.offer_message = form.cleaned_data['message']
            app.status = 'OFFER'
            app.save()

            Notification.objects.create(
                user=app.candidate,
                message=f"🎉 OFFICIAL OFFER: You have received a Job Offer for {app.job.title}!",
                link=reverse('web_test:view_offer', args=[app.id])
            )

            messages.success(request, f"Offer sent to {app.candidate.full_name} successfully!")
            return redirect('web_test:client_job_view', job_id=app.job.id)
    else:
        salary_val = app.candidate_expected_salary if app.candidate_expected_salary else app.job.monthly_salary
        date_val = app.candidate_joining_date if app.candidate_joining_date else timezone.now().date()
        
        initial_data = {
            'salary': salary_val,
            'start_date': date_val,
            'message': f"Dear {app.candidate.full_name},\n\nWe are pleased to offer you the position of {app.job.title} based on our recent discussions."
        }
        form = OfferCreationForm(initial=initial_data)

    return render(request, 'client/create_offer.html', {'form': form, 'app': app})

@login_required
def client_schedule_interview(request, application_id): #Client schedules final interview
    app = get_object_or_404(Application, id=application_id)
    
    if app.job.client_contact != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:client_dashboard')

    if request.method == 'POST':
        form = ClientScheduleForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            location = form.cleaned_data['location']
            notes = form.cleaned_data['notes']
            
            dt_string = f"{date} {time}"
            
            # 1. Update Application & SAVE ALL FIELDS
            app.status = 'FINAL_INTERVIEW'
            app.interview_date = dt_string
            app.interview_location = location 
            app.interview_note = notes         
            app.save()

            # 2. Notify Candidate -> Redirect to Status Page
            Notification.objects.create(
                user=app.candidate,
                message=f"📅 Final Interview Scheduled: {date} at {time}. Click to view details.",
                link=reverse('web_test:candidate_job_status', args=[app.job.id]) 
            )
            
            messages.success(request, f"Final Interview scheduled! Notification sent to {app.candidate.full_name}.")
            return redirect('web_test:client_job_view', job_id=app.job.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.warning(request, f"⚠️ {field.title()}: {error}")
    else:
        form = ClientScheduleForm()

    return render(request, 'client/schedule_interview.html', {
        'form': form, 
        'app': app
    })

@login_required
def client_create_request(request): #Client creates a new job request
    if request.user.role != 'Client':
        messages.error(request, "Access Denied")
        return redirect('web_test:home')

    if request.method == 'POST':
        form = ClientJobRequestForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.client_contact = request.user 
            job.posted_by = request.user 
            job.status = 'REQUESTED' 
            job.save()
            
            User = get_user_model()
            
            hr_users = User.objects.filter(role='HR')
            
            #Create a notification for each HR user
            for hr in hr_users:
                Notification.objects.create(
                    user=hr,
                    message=f"New Job Request from {request.user.full_name}: {job.title}",
                    link=reverse('web_test:hr_pending_requests')  # Directs HR to the pending requests page
                )

            messages.success(request, "Request submitted!")
            
            if job.has_primary_exam:
                return redirect('web_test:client_add_questions', job_id=job.id)
            
            return redirect('web_test:client_dashboard')
        else:
            # Error handling logic 
            for error in form.non_field_errors():
                messages.warning(request, f"⚠️ {error}") 
            for field_name, errors in form.errors.items():
                if field_name != '__all__':
                    for error in errors:
                        messages.warning(request, f"⚠️ {field_name.replace('_', ' ').title()}: {error}")

    else:
        form = ClientJobRequestForm()
        
    return render(request, 'client/create_request.html', {'form': form})

@login_required
def client_edit_request(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if job.client_contact != request.user:
        messages.error(request, "Access Denied.")
        return redirect('web_test:client_dashboard')
        
        # Allow editing if status is REQUESTED OR OPEN
    if job.status not in ['REQUESTED', 'OPEN']:
        messages.error(request, "This job is closed and cannot be edited.")
        return redirect('web_test:client_dashboard')

    if request.method == 'POST':
        form = ClientJobRequestForm(request.POST, request.FILES, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Request updated successfully.")
            
            # If user clicked "Save & Manage Questions", redirect there
            if 'manage_questions' in request.POST or job.has_primary_exam:
                return redirect('web_test:client_add_questions', job_id=job.id)
            return redirect('web_test:client_dashboard')
    else:
        form = ClientJobRequestForm(instance=job)
        
    return render(request, 'client/edit_request.html', {'form': form, 'job': job})

@login_required
def client_delete_request(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if job.client_contact != request.user or job.status != 'REQUESTED':
        messages.error(request, "Cannot delete this job.")
        return redirect('web_test:client_dashboard')
    
    if request.method == 'POST':
        job.delete()
        messages.success(request, "Request deleted.")
        return redirect('web_test:client_dashboard')
        
    return render(request, 'client/delete_request_confirm.html', {'job': job})

@login_required
def add_questions_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if job.client_contact != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:client_dashboard')

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            # Creating Question instance but not saving yet
            question = form.save(commit=False)
            question.job = job
            
            data = form.cleaned_data
            question.choices = [
                data['option_1'],
                data['option_2'],
                data['option_3'],
                data['option_4']
            ]
            
            question.correct_answer_index = int(data['correct_option'])
            question.save()
            
            messages.success(request, "Question added!")
            return redirect('web_test:client_add_questions', job_id=job.id)
    else:
        form = QuestionForm()

    existing_questions = job.questions.all().order_by('created_at')

    return render(request, 'client/add_questions.html', {
        'job': job,
        'form': form,
        'questions': existing_questions
    })

@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    job_id = question.job.id
    
    if question.job.client_contact != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:client_dashboard')
        
    question.delete()
    messages.success(request, "Question removed.")
    return redirect('web_test:client_add_questions', job_id=job_id)


@login_required
def client_edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    job = question.job
    
    if job.client_contact != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:client_dashboard')

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            # Update the existing question instance manually
            question.text = data['text']
            question.choices = [
                data['option_1'],
                data['option_2'],
                data['option_3'],
                data['option_4']
            ]
            question.correct_answer_index = int(data['correct_option'])
            question.save()
            
            messages.success(request, "Question updated!")
            return redirect('web_test:client_add_questions', job_id=job.id)
    else:
        # Pre-fill form with existing data
        initial_data = {
            'text': question.text,
            'option_1': question.choices[0],
            'option_2': question.choices[1],
            'option_3': question.choices[2],
            'option_4': question.choices[3],
            'correct_option': str(question.correct_answer_index)
        }
        form = QuestionForm(initial=initial_data)

    return render(request, 'client/add_questions.html', {
        'job': job,
        'form': form,
        'questions': job.questions.all(),
        'editing': True 
    })