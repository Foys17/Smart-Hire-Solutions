from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from candidates.models import Application
from jobs.models import ExamAttempt
from users.models import Notification 
from candidates.utils import process_application  


@login_required
def take_exam(request, application_id):
    app = get_object_or_404(Application, pk=application_id, candidate=request.user)
    job = app.job

    if app.status not in ['SCREENING', 'PENDING_EXAM']:
        messages.warning(request, "You have already completed this step or cannot access it now.")
        return redirect('web_test:home')

    if request.method == 'POST':
        #GRADING LOGIC
        questions = job.questions.all()
        total_questions = questions.count()
        correct_answers = 0

        for q in questions:
            user_answer = request.POST.get(f'question_{q.id}')
            
            # Compare user_answer (string) with correct_answer_index (int)
            # We convert the model's index to a string to match the POST data safely
            if user_answer and user_answer == str(q.correct_answer_index):
                correct_answers += 1
        
        # Calculate Score
        score_percent = 0
        if total_questions > 0:
            score_percent = (correct_answers / total_questions) * 100
        
        is_passed = score_percent >= job.exam_passing_score

        ExamAttempt.objects.create(
            job=job,
            candidate=request.user,
            score=score_percent,
            passed=is_passed
        )

        # Update Application Status & Score
        app.exam_score = score_percent
        
        if is_passed:
            app.status = 'INTERVIEW'
            app.save()
            
            # TRIGGER AI SCORING
            # Now that the candidate has passed the gatekeeper exam, 
            # we run the AI pipeline to extract skills and calculate the CV match score.
            process_application(app) 
            
            # NOTIFY CANDIDATE 
            Notification.objects.create(
                user=request.user,
                message=f"🎉 You passed the screening exam with {score_percent:.0f}%! HR will contact you shortly.",
                link=reverse('web_test:home')
            )
            messages.success(request, f"Congratulations! You passed with {score_percent:.0f}%.")
        
        else:
            app.status = 'REJECTED'   
            app.save()
            messages.error(request, f"Score: {score_percent:.0f}%. Unfortunately, you did not meet the passing requirement.")

        return redirect('web_test:home')

    return render(request, 'candidates/take_exam.html', {
        'app': app, 
        'job': job, 
        'questions': job.questions.all()
    })