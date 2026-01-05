from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from jobs.models import Job
from jobs.utils import run_ai_pipeline  # Import your AI logic
from candidates.models import Application
from candidates.utils import process_application # Import your AI logic
from .forms import JobForm, ApplicationForm, UserLoginForm, UserRegistrationForm,HRUploadCVForm,InterviewInviteForm
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


def home(request):
    """Public Landing Page"""
    return render(request, 'home.html')

@login_required
def dashboard(request):
    """Landing page showing buttons based on Role."""
    return render(request, 'dashboard.html')

@login_required
def job_list(request):
    """Show all jobs. Candidates can apply here."""
    jobs = Job.objects.all().order_by('-created_at')
    
    # --- NEW LOGIC: Check User's Application Status ---
    if request.user.is_authenticated and request.user.role == 'Candidate':
        # Fetch all applications by this user
        my_apps = Application.objects.filter(candidate=request.user)
        # Create a dictionary map: { job_id: 'APPLIED' or 'SCREENED' etc. }
        status_map = {app.job_id: app.status for app in my_apps}
        
        # Attach the status to each job object dynamically
        for job in jobs:
            job.current_user_status = status_map.get(job.id)
            
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
    Allows HR to edit the job. 
    Fix: Uses instance=job to pre-fill the form with existing data.
    """
    job = get_object_or_404(Job, pk=pk)

    if request.user.role not in ['HR', 'Reviewer']:
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        # instance=job ensures we are UPDATING, not creating new
        form = JobForm(request.POST, request.FILES, instance=job) 
        if form.is_valid():
            job = form.save(commit=False)
            
            # Optional: Re-run AI if description changed
            # run_ai_pipeline(job) 
            
            job.save()
            messages.success(request, "Job updated successfully!")
            return redirect('web_test:job_detail', pk=job.pk)
    else:
        # This pre-fills the form with the database values
        form = JobForm(instance=job)

    return render(request, 'edit_job.html', {'form': form, 'job': job})

@login_required
def delete_job(request, pk):
    """
    Permanently deletes a job.
    """
    job = get_object_or_404(Job, pk=pk)
    
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')
        
    if request.method == 'POST':
        title = job.title
        job.delete()
        messages.success(request, f"Job '{title}' has been deleted.")
        return redirect('web_test:job_list')
    
    # If accessed via GET, ask for confirmation
    return render(request, 'delete_job_confirm.html', {'job': job})


@login_required
def toggle_job_status(request, pk):
    """
    Switches job between OPEN and CLOSED.
    """
    job = get_object_or_404(Job, pk=pk)
    
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if job.status == 'OPEN':
        job.status = 'CLOSED'
        messages.info(request, "Job marked as CLOSED. No new applicants allowed.")
    else:
        job.status = 'OPEN'
        messages.success(request, "Job Re-Opened!")
    
    job.save()
    return redirect('web_test:job_detail', pk=job.pk)


@login_required
def application_detail(request, pk):
    """
    Shows a deep-dive comparison between the Job Requirements and the Candidate's CV.
    Includes:
    1. Fuzzy Matching for Skills (e.g. 'React' matches 'React.js')
    2. Logic Comparison for Experience (e.g. 4.2 Years >= 4 Years)
    """
    application = get_object_or_404(Application, pk=pk)
    
    if request.user.role != 'HR' and request.user != application.candidate:
        messages.error(request, "Access Denied.")
        return redirect('web_test:dashboard')

    # --- GAP ANALYSIS LOGIC ---
    
    tech_labels = [
        'Skill', 'Technology', 'Framework', 'Programming Language', 
        'Database', 'Tool', 'Platform', 'Cloud', 'Service'
    ]

    # 1. PREPARE SKILL DATA
    job_skills_map = {}
    if application.job.gliner_entities:
        for item in application.job.gliner_entities:
            if item['label'] in tech_labels:
                job_skills_map[item['text'].strip().lower()] = item['text'].strip()

    cv_skills_map = {}
    if application.extracted_data:
        for item in application.extracted_data:
            if item['label'] in tech_labels:
                cv_skills_map[item['text'].strip().lower()] = item['text'].strip()

    matches = []
    misses = []
    extras = []
    
    # 2. EXPERIENCE LOGIC (New Addition)
    req_years = 0
    cand_years = 0.0

    # Get Job Requirement
    if application.job.gliner_entities:
        for item in application.job.gliner_entities:
            if item.get('label') == 'Min_Years_Req':
                try:
                    req_years = int(item['text'])
                except ValueError:
                    req_years = 0
                break

    # Get Candidate Actual
    if application.extracted_data:
        for item in application.extracted_data:
            if item.get('label') == 'Total_Years_Calc':
                try:
                    cand_years = float(item['text'])
                except ValueError:
                    cand_years = 0.0
                break

    # Compare Years
    if req_years > 0:
        if cand_years >= req_years:
            # We insert at 0 to make it the top item in the list
            matches.insert(0, f"✅ {cand_years} Years Experience (Matches {req_years}+ Req)")
        else:
            misses.insert(0, f"❌ Requires {req_years}+ Years (Has {cand_years})")
    elif cand_years > 0:
        # If job didn't specify years, just list it as a feature
        extras.insert(0, f"{cand_years} Years Total Experience")

    # 3. SKILLS MATCHING LOGIC
    synonyms = {
        "drf": "django rest framework",
        "reactjs": "react",
        "js": "javascript",
        "aws": "amazon web services",
        "postgres": "postgresql",
        "k8s": "kubernetes",
    }

    # CHECK JOB SKILLS
    for j_key, j_text in job_skills_map.items():
        matched = False
        
        # Strategy A: Exact Match
        if j_key in cv_skills_map:
            matches.append(j_text) 
            matched = True
            
        # Strategy B: Substring & Synonyms
        else:
            for c_key, c_text in cv_skills_map.items():
                # Substring check (avoiding short noise like "c" or "go" unless exact)
                if len(c_key) > 2 and len(j_key) > 2:
                    if c_key in j_key: 
                        matches.append(f"{c_text} (matches {j_text})")
                        matched = True
                        break
                    if j_key in c_key:
                        matches.append(c_text)
                        matched = True
                        break
                
                # Synonym check
                std_j = synonyms.get(j_key, j_key)
                std_c = synonyms.get(c_key, c_key)
                if std_j == std_c or std_c in std_j:
                    matches.append(f"{c_text} (matches {j_text})")
                    matched = True
                    break

        if not matched:
            misses.append(j_text)

    # CHECK EXTRAS (Skills in CV but not in Job)
    # Convert matches to a single string for easy exclusion check
    match_strings = " ".join(matches).lower()
    
    for c_key, c_text in cv_skills_map.items():
        # Only add if it hasn't been matched yet AND isn't in the job requirements
        if c_key not in match_strings and c_key not in job_skills_map:
            extras.append(c_text)

    context = {
        'app': application,
        'matches': matches,
        'misses': misses,
        'extras': extras,
    }
        
    return render(request, 'application_detail.html', context)


# frontend/views.py
import uuid # Add this import at the top of your file, or inside the function

@login_required
def hr_upload_cv(request, job_id):
    """
    Allows HR to:
    1. Bulk upload raw PDFs (Auto-creates candidate from filename)
    2. detailed upload with references (Manual entry)
    """
    job = get_object_or_404(Job, pk=job_id)

    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        success_count = 0
        errors = []

        # --- PART 1: PROCESS BULK FILES (No References) ---
        bulk_files = request.FILES.getlist('bulk_cvs')
        
        for f in bulk_files:
            try:
                # 1. Derive Name from Filename (e.g., "John_Doe_CV.pdf" -> "John Doe Cv")
                clean_name = f.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                
                # 2. Generate Placeholder Email (Since we don't have one yet)
                # The AI or HR can update this later
                unique_id = str(uuid.uuid4())[:8]
                placeholder_email = f"{clean_name.replace(' ', '.').lower()}.{unique_id}@pending.parsing"

                # 3. Create User
                candidate, created = User.objects.get_or_create(
                    email=placeholder_email,
                    defaults={'full_name': clean_name, 'role': 'Candidate'}
                )
                if created:
                    candidate.set_unusable_password()
                    candidate.save()

                # 4. Create Application
                app = Application.objects.create(
                    job=job,
                    candidate=candidate,
                    cv_file=f,
                    has_reference=False
                )
                
                # 5. Trigger AI
                process_application(app)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Bulk File Error ({f.name}): {str(e)}")


        # --- PART 2: PROCESS DETAILED ROWS (With References) ---
        names = request.POST.getlist('full_name')
        emails = request.POST.getlist('email')
        refs = request.POST.getlist('reference_name')
        files = request.FILES.getlist('cv_file')

        # Only process if there are actually rows added
        if names and files:
            # Iterate through each manual entry
            for i in range(len(names)):
                # Skip empty rows if any
                if not names[i] or not files[i]:
                    continue

                try:
                    name = names[i]
                    email = emails[i]
                    cv_file = files[i]
                    ref_name = refs[i] if i < len(refs) else ''

                    # Create Candidate
                    candidate, created = User.objects.get_or_create(
                        email=email,
                        defaults={'full_name': name, 'role': 'Candidate'}
                    )
                    if created:
                        candidate.set_unusable_password()
                        candidate.save()

                    # Check Duplication
                    if Application.objects.filter(job=job, candidate=candidate).exists():
                        errors.append(f"Skipped {name}: Already applied.")
                        continue

                    # Create Application
                    app = Application.objects.create(
                        job=job,
                        candidate=candidate,
                        cv_file=cv_file,
                        has_reference=bool(ref_name),
                        reference_name=ref_name
                    )
                    
                    # Trigger AI
                    process_application(app)
                    success_count += 1

                except Exception as e:
                    errors.append(f"Row {i+1} Error: {str(e)}")

        # --- FEEDBACK ---
        if success_count > 0:
            messages.success(request, f"Successfully processed {success_count} applications!")
        
        if errors:
            for err in errors:
                messages.error(request, err)
        
        return redirect('web_test:job_ranking', job_id=job.id)

    else:
        form = HRUploadCVForm()

    return render(request, 'hr_upload_cv.html', {'form': form, 'job': job})


@login_required
def send_interview_invite(request, application_id):
    """
    HR submits the Interview Form.
    1. Updates Application Status -> 'INTERVIEW'
    2. Sends Email to Candidate.
    """
    application = get_object_or_404(Application, pk=application_id)
    
    # Security Check
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:dashboard')

    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            # 1. Update Application Status
            application.status = 'INTERVIEW'
            # Assuming you have an 'interview_date' field, or we just save it in notes
            # If your model handles datetime, combine data['date'] and data['time']
            application.save()

            # 2. Send Email
            subject = f"Interview Invitation: {application.job.title}"
            message_body = (
                f"Dear {application.candidate.full_name},\n\n"
                f"We are pleased to invite you for an interview for the position of {application.job.title}.\n\n"
                f"📅 Date: {data['date']}\n"
                f"⏰ Time: {data['time']}\n"
                f"📍 Location: {data['location']}\n\n"
                f"Notes: {data['message']}\n\n"
                f"Best regards,\nSmart Hire Solutions Team"
            )

            try:
                send_mail(
                    subject,
                    message_body,
                    settings.EMAIL_HOST_USER or 'noreply@smarthire.com',
                    [application.candidate.email],
                    fail_silently=False,
                )
                messages.success(request, f"Invite sent to {application.candidate.full_name}!")
            except Exception as e:
                messages.error(request, f"Error sending email: {e}")

            return redirect('web_test:job_ranking', job_id=application.job.id)
    
    # If not POST, just redirect back
    return redirect('web_test:job_ranking', job_id=application.job.id)


# In frontend/views.py

@login_required
def bulk_send_invite(request):
    """
    Process the Bulk Interview Invite Form.
    """
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:dashboard')

    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            ids_str = form.cleaned_data['application_ids']
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            location = form.cleaned_data['location']
            notes = form.cleaned_data['message']

            # Parse IDs
            app_ids = [int(id) for id in ids_str.split(',') if id.isdigit()]
            
            applications = Application.objects.filter(id__in=app_ids)
            success_count = 0
            errors = []
            
            for app in applications:
                # 1. Update Status
                app.status = 'INTERVIEW'
                app.save()

                # 2. Send Email
                subject = f"Interview Invitation: {app.job.title}"
                message_body = (
                    f"Dear {app.candidate.full_name},\n\n"
                    f"We are pleased to invite you for an interview.\n\n"
                    f"📅 Date: {date}\n"
                    f"⏰ Time: {time}\n"
                    f"📍 Location: {location}\n\n"
                    f"Notes: {notes}\n\n"
                    f"Best regards,\nSmart Hire Solutions Team"
                )
                
                try:
                    send_mail(
                        subject, message_body, 
                        settings.EMAIL_HOST_USER or 'noreply@smarthire.com', 
                        [app.candidate.email], fail_silently=False
                    )
                    success_count += 1
                except Exception as e:
                    # Collect error messages to show the user
                    errors.append(f"{app.candidate.email}: {str(e)}")

            # 3. Show Feedback
            if success_count > 0:
                messages.success(request, f"✅ Sent invites to {success_count} candidates!")
            
            if errors:
                messages.error(request, f"❌ Failed to send {len(errors)} emails. Check console for details.")
                # Print exact errors to the terminal so you can debug
                for err in errors:
                    print(f"EMAIL ERROR: {err}")

            if applications.exists():
                return redirect('web_test:job_ranking', job_id=applications.first().job.id)
            
    return redirect('web_test:job_list')


@login_required
def candidate_job_status(request, job_id):
    """
    Displays the status of the candidate's application.
    If status is 'APPLIED', allows them to delete/re-upload.
    """
    job = get_object_or_404(Job, pk=job_id)
    
    # Security Check
    if request.user.role != 'Candidate':
        return redirect('web_test:job_list')
        
    # Get the specific application
    application = get_object_or_404(Application, job=job, candidate=request.user)
    
    return render(request, 'candidate_status.html', {
        'application': application, 
        'job': job
    })

@login_required
def withdraw_application(request, application_id):
    """
    Allows candidate to delete their application (CV) only if status is APPLIED.
    """
    app = get_object_or_404(Application, pk=application_id, candidate=request.user)
    
    if app.status == 'APPLIED':
        app.delete()
        messages.success(request, "Your CV has been removed. You can now upload a new one.")
    else:
        messages.error(request, "You cannot delete your CV at this stage (already processed).")
        
    return redirect('web_test:job_list')