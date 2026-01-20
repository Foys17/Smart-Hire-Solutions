from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from candidates.models import Application
from reviewer.models import InterviewScore
from frontend.forms import ReviewForm
from jobs.models import Job
from users.models import Notification
from django.urls import reverse

@login_required
def reviewer_dashboard(request):
    """
    Shows a list of Active Jobs assigned to this Reviewer.
    """
    if request.user.role not in ['Reviewer', 'Admin']:
        messages.error(request, "Access Restricted to Reviewers.")
        return redirect('web_test:home')

    # Find jobs where this user has assigned interviews OR is a general reviewer
    # distinct() ensures we don't see the same job twice
    my_jobs = Job.objects.filter(
        applications__assigned_reviewer=request.user, 
        status='OPEN'
    ).distinct()

    return render(request, 'reviewer/dashboard.html', {
        'my_jobs': my_jobs
    })

@login_required
def reviewer_job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if request.user.role not in ['Reviewer', 'Admin']:
        return redirect('web_test:home')

    # --- CHANGED LOGIC: FETCH ALL ASSIGNED CANDIDATES ---
    # We removed status='INTERVIEW' so we can see history (Offers, Rejections, etc.)
    candidates = Application.objects.filter(
        job=job,
        assigned_reviewer=request.user
    ).select_related('candidate').order_by('-match_score')
    # ----------------------------------------------------

    for app in candidates:
        score_obj = InterviewScore.objects.filter(application=app, reviewer=request.user).first()
        if score_obj:
            app.has_score = True
            app.given_score = score_obj.average_score
        else:
            app.has_score = False
            app.given_score = None

    return render(request, 'reviewer/job_detail.html', {
        'job': job,
        'candidates': candidates
    })

@login_required
def submit_review(request, app_id):
    app = get_object_or_404(Application, pk=app_id)
    
    # 1. Security Check: Only assigned reviewer or Admin can score
    if app.assigned_reviewer != request.user and request.user.role != 'Admin':
        messages.error(request, "You are not assigned to this interview.")
        return redirect('web_test:reviewer_dashboard')

    # 2. FIX: Robustly fetch existing score
    # We filter ONLY by application because the database constraint is on application_id
    score_instance = InterviewScore.objects.filter(application=app).first()

    if request.method == 'POST':
        # 3. Pass 'instance=score_instance' to UPDATE existing record
        form = ReviewForm(request.POST, instance=score_instance)
        
        if form.is_valid():
            score = form.save(commit=False)
            score.application = app
            score.reviewer = request.user  # Update reviewer to current user
            score.save()
            
            messages.success(request, f"Review saved successfully! Score: {score.average_score}/10.")
            return redirect('web_test:reviewer_job_detail', job_id=app.job.id)
    else:
        # 4. Pre-fill form if instance exists
        form = ReviewForm(instance=score_instance)
        
    return render(request, 'reviewer/submit_review.html', {'form': form, 'app': app})


@login_required
def finish_interview_process(request, job_id):
    """
    Called when the Reviewer decides they are done interviewing ALL candidates for a Job.
    It ranks candidates and moves the Top N to the next stage.
    """
    job = get_object_or_404(Job, id=job_id)
    
    if request.user.role not in ['Reviewer', 'Admin']:
        messages.error(request, "Access Denied")
        return redirect('web_test:home')

    # 1. Get all candidates in INTERVIEW stage who have been scored
    candidates = Application.objects.filter(job=job, status='INTERVIEW')
    
    scored_candidates = []
    for app in candidates:
        # Assuming One-to-One or One-to-Many, get the latest score
        score_obj = InterviewScore.objects.filter(application=app).first()
        if score_obj:
            scored_candidates.append((app, score_obj.average_score))
    
    if not scored_candidates:
        messages.warning(request, "No scored candidates found to process.")
        return redirect('web_test:reviewer_dashboard')

    # 2. Sort by Score (High to Low)
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    # 3. Select Top N Candidates
    top_n_count = job.target_candidates_count
    selected = scored_candidates[:top_n_count]
    rejected = scored_candidates[top_n_count:] # The rest are rejected or kept in pool

    # 4. Process Logic
    promoted_names = []
    
    for app, score in selected:
        promoted_names.append(app.candidate.full_name)
        
        # LOGIC BRANCH: Does Client want to interview?
        if job.client_does_final_interview:
            # YES: Move to Client Review (So Client can Approve -> Final Interview)
            app.status = 'CLIENT_REVIEW'
            msg_body = f"Candidates shortlisted for {job.title} are ready for your review."
            next_stage_desc = "Client Review"
        else:
            # NO: Move directly to OFFER (Skip Client)
            app.status = 'OFFER'
            msg_body = f"Candidates for {job.title} have been selected and Offers have been generated."
            next_stage_desc = "Offer Sent"
            
            # Notify Candidate immediately
            Notification.objects.create(
                user=app.candidate,
                message=f"Congratulations! You have received an Offer for {job.title}.",
                link=reverse('web_test:view_offer', args=[app.id]) # Assuming you have this view
            )

        app.save()

    # 5. Handle Rejected (Optional: Mark as REJECTED or leave in INTERVIEW?)
    # For now, let's mark them as REJECTED so the pipeline is clean.
    for app, score in rejected:
        app.status = 'REJECTED'
        app.save()

    # 6. Notify Client
    if job.client_contact:
        Notification.objects.create(
            user=job.client_contact,
            message=msg_body,
            link=reverse('web_test:client_dashboard')
        )

    messages.success(request, f"Interview Process Finished! {len(promoted_names)} candidates moved to {next_stage_desc}.")
    return redirect('web_test:reviewer_dashboard')