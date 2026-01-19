from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from candidates.models import Application
from jobs.models import ExamAttempt
from candidates.utils import process_application

@login_required
def take_exam(request, application_id):
    app = get_object_or_404(Application, pk=application_id, candidate=request.user)
    job = app.job

    # Security Checks
    if app.status != 'PENDING_EXAM':
        messages.warning(request, "You have already completed this step.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        # --- GRADING LOGIC ---
        questions = job.questions.all()
        total_questions = questions.count()
        correct_answers = 0

        for q in questions:
            # We expect the input name to be "question_123"
            user_answer = request.POST.get(f'question_{q.id}')
            if user_answer and int(user_answer) == q.correct_answer_index:
                correct_answers += 1
        
        # Calculate Score
        score_percent = 0
        if total_questions > 0:
            score_percent = (correct_answers / total_questions) * 100
        
        is_passed = score_percent >= job.exam_passing_score

        # Save Attempt
        ExamAttempt.objects.create(
            job=job,
            candidate=request.user,
            score=score_percent,
            passed=is_passed
        )

        # Update Application Status
        if is_passed:
            app.status = 'APPLIED'
            app.save()
            process_application(app) # <--- NOW we run the AI Scoring
            messages.success(request, f"Congratulations! You passed with {score_percent:.1f}%. Your application is now with HR.")
        else:
            app.status = 'REJECTED'
            app.save()
            messages.error(request, f"Score: {score_percent:.1f}%. Unfortunately, you did not meet the passing requirement ({job.exam_passing_score}%).")

        return redirect('web_test:job_list')

    return render(request, 'candidates/take_exam.html', {'app': app, 'job': job, 'questions': job.questions.all()})