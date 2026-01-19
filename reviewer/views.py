from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from candidates.models import Application
from reviewer.models import InterviewScore
from frontend.forms import ReviewForm

@login_required
def reviewer_dashboard(request):
    # Security: Ensure only Reviewers (or Admins) can see this
    if request.user.role not in ['Reviewer', 'Admin']:
        messages.error(request, "Access Restricted to Reviewers.")
        return redirect('web_test:home')
    
    # 1. Pending Interviews: Assigned to me, currently in 'INTERVIEW' stage, and NO score yet.
    pending_interviews = Application.objects.filter(
        assigned_reviewer=request.user,
        status='INTERVIEW',
        interview_score__isnull=True
    ).select_related('job', 'candidate').order_by('created_at')

    # 2. Completed History: Reviews I have already submitted
    completed_reviews = InterviewScore.objects.filter(
        reviewer=request.user
    ).select_related('application', 'application__candidate').order_by('-created_at')

    return render(request, 'reviewer/dashboard.html', {
        'pending': pending_interviews,
        'completed': completed_reviews
    })

@login_required
def submit_review(request, app_id):
    # Get the specific application
    app = get_object_or_404(Application, pk=app_id)
    
    # Security Check: Am I the assigned reviewer?
    if app.assigned_reviewer != request.user and request.user.role != 'Admin':
        messages.error(request, "You are not assigned to this interview.")
        return redirect('web_test:reviewer_dashboard')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            # Save the Score
            score = form.save(commit=False)
            score.application = app
            score.reviewer = request.user
            score.save()
            
            # --- AUTOMATION LOGIC: PROMOTION ---
            # If the candidate scores > 70% (7.0 average), send to Client.
            if score.average_score >= 7.0:
                app.status = 'CLIENT_REVIEW'
                app.save()
                messages.success(request, f"Score: {score.average_score}/10. Excellent! Candidate promoted to Client Review.")
                
                # (Optional: Trigger 'New Candidate' email to Client here)
                
            else:
                # If score is low, keep them in Interview stage (or move to Screening/Rejected)
                # for HR to make the final call.
                messages.warning(request, f"Score: {score.average_score}/10. Review saved. Candidate remains in queue for HR decision.")
            
            return redirect('web_test:reviewer_dashboard')
    else:
        form = ReviewForm()
        
    return render(request, 'reviewer/submit_review.html', {'form': form, 'app': app})