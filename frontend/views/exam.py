from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse  # Needed for links
from candidates.models import Application
from jobs.models import ExamAttempt
from users.models import Notification 


@login_required
def take_exam(request, application_id):
    app = get_object_or_404(Application, pk=application_id, candidate=request.user)
    job = app.job

    # Security Checks
    if app.status not in ['SCREENING', 'PENDING_EXAM']:
        messages.warning(request, "You have already completed this step or cannot access it now.")
        return redirect('web_test:home')

    if request.method == 'POST':
        # --- GRADING LOGIC ---
        questions = job.questions.all()
        total_questions = questions.count()
        correct_answers = 0

        for q in questions:
            user_answer = request.POST.get(f'question_{q.id}')
            
            # Logic assuming your Question model uses 'correct_answer' string or index
            # Adjust 'q.correct_answer' to match your actual model field name
            if user_answer and user_answer == q.correct_answer:
                correct_answers += 1
        
        # Calculate Score
        score_percent = 0
        if total_questions > 0:
            score_percent = (correct_answers / total_questions) * 100
        
        is_passed = score_percent >= job.exam_passing_score

        # 1. Save Attempt (Keep your existing model)
        ExamAttempt.objects.create(
            job=job,
            candidate=request.user,
            score=score_percent,
            passed=is_passed
        )

        # 2. Update Application Status & Score
        app.exam_score = score_percent  # Save to app for HR to see easily
        
        if is_passed:
            app.status = 'INTERVIEW'  # <--- MOVE FORWARD to Interview
            app.save()
            
            # --- NOTIFY CANDIDATE ---
            Notification.objects.create(
                user=request.user,
                message=f"🎉 You passed the screening exam with {score_percent:.0f}%! HR will contact you shortly.",
                link=reverse('web_test:home')
            )
            
            # Optional: Notify HR
            # Notification.objects.create(
            #     user=job.posted_by,
            #     message=f"{app.candidate.full_name} passed the exam ({score_percent:.0f}%). Ready for Interview.",
            #     link=reverse('web_test:kanban_board')
            # )

            messages.success(request, f"Congratulations! You passed with {score_percent:.0f}%.")
        
        else:
            app.status = 'REJECTED'   
            app.save()
            
            messages.error(request, f"Score: {score_percent:.0f}%. Unfortunately, you did not meet the passing requirement.")

        # Redirect to Dashboard so they see the change immediately
        return redirect('web_test:home')

    return render(request, 'candidates/take_exam.html', {
        'app': app, 
        'job': job, 
        'questions': job.questions.all()
    })