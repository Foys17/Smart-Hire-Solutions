from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from jobs.models import Job
from jobs.utils import run_ai_pipeline
from candidates.models import Application
from candidates.utils import process_application
from .forms import JobForm, ApplicationForm, UserLoginForm, UserRegistrationForm, HRUploadCVForm, InterviewInviteForm, CVBuilderForm,EmployeeCreationForm, PayrollForm, LeaveRequestForm
from .utils import generate_ats_cv
from django.http import HttpResponseForbidden, FileResponse
from django.core.mail import send_mail
from django.conf import settings
import uuid 
from employees.models import Employee, Payroll, LeaveRequest


User = get_user_model()


def home(request):
    """Public Landing Page"""
    return render(request, 'home.html')


def job_list(request):
    """Show all jobs. Publicly accessible."""
    jobs = Job.objects.all().order_by('-created_at')
    
    if request.user.is_authenticated and getattr(request.user, 'role', '') == 'Candidate':
        my_apps = Application.objects.filter(candidate=request.user)
        status_map = {app.job_id: app.status for app in my_apps}
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
            run_ai_pipeline(job)
            messages.success(request, "Job posted and AI processed!")
            return redirect('web_test:job_list')
    else:
        form = JobForm()
    return render(request, 'create_job.html', {'form': form})

def apply_for_job(request, job_id):
    """Candidate: Upload CV. Redirects to Register if not logged in."""
    if not request.user.is_authenticated:
        messages.info(request, "Please register or login to apply for this job.")
        return redirect('web_test:register')

    job = get_object_or_404(Job, pk=job_id)
    
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
    
    apps = Application.objects.filter(job=job)
    if request.GET.get('ref'):
        apps = apps.filter(has_reference=True)
        
    apps = apps.order_by('-match_score')
    
    return render(request, 'ranking.html', {'job': job, 'applications': apps})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.full_name}!")
            return redirect('web_test:job_list')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            remember_me = request.POST.get('remember-me')
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600) 

            return redirect('web_test:job_list')
    else:
        form = UserLoginForm()

    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('web_test:login')


# REMOVED @login_required to allow public access
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # Check application status for logged-in candidates
    if request.user.is_authenticated and getattr(request.user, 'role', '') == 'Candidate':
        has_applied = Application.objects.filter(candidate=request.user, job=job).exists()
        job.has_applied = has_applied
        
    return render(request, 'job_detail.html', {'job': job})

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
    
    if request.user.role != 'HR':
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
        # Update all candidates who are not already rejected to REJECTED
        count = Application.objects.filter(job=job).exclude(status='REJECTED').update(status='REJECTED')
        messages.info(request, f"Job CLOSED. {count} active application(s) marked as Rejected.")
    else:
        job.status = 'OPEN'
        messages.success(request, "Job Re-Opened! Candidates can apply again.")
    
    job.save()
    return redirect('web_test:job_detail', pk=job.pk)

@login_required
def delete_application(request, pk):
    app = get_object_or_404(Application, pk=pk)
    job_id = app.job.id 

    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    candidate_name = app.candidate.full_name
    app.delete()
    messages.success(request, f"Candidate {candidate_name} removed successfully.")
    
    return redirect('web_test:job_ranking', job_id=job_id)


@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    
    if request.user.role != 'HR' and request.user != application.candidate:
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    tech_labels = ['Skill', 'Technology', 'Framework', 'Programming Language', 'Database', 'Tool', 'Platform', 'Cloud', 'Service']

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
    
    req_years = 0
    cand_years = 0.0

    if application.job.gliner_entities:
        for item in application.job.gliner_entities:
            if item.get('label') == 'Min_Years_Req':
                try: req_years = int(item['text'])
                except ValueError: req_years = 0
                break

    if application.extracted_data:
        for item in application.extracted_data:
            if item.get('label') == 'Total_Years_Calc':
                try: cand_years = float(item['text'])
                except ValueError: cand_years = 0.0
                break

    if req_years > 0:
        if cand_years >= req_years:
            matches.insert(0, f"✅ {cand_years} Years Experience (Matches {req_years}+ Req)")
        else:
            misses.insert(0, f"❌ Requires {req_years}+ Years (Has {cand_years})")
    elif cand_years > 0:
        extras.insert(0, f"{cand_years} Years Total Experience")

    synonyms = {
        "drf": "django rest framework", "reactjs": "react", "js": "javascript",
        "aws": "amazon web services", "postgres": "postgresql", "k8s": "kubernetes",
    }

    for j_key, j_text in job_skills_map.items():
        matched = False
        if j_key in cv_skills_map:
            matches.append(j_text) 
            matched = True
        else:
            for c_key, c_text in cv_skills_map.items():
                if len(c_key) > 2 and len(j_key) > 2:
                    if c_key in j_key: 
                        matches.append(f"{c_text} (matches {j_text})")
                        matched = True
                        break
                    if j_key in c_key:
                        matches.append(c_text)
                        matched = True
                        break
                
                std_j = synonyms.get(j_key, j_key)
                std_c = synonyms.get(c_key, c_key)
                if std_j == std_c or std_c in std_j:
                    matches.append(f"{c_text} (matches {j_text})")
                    matched = True
                    break
        if not matched:
            misses.append(j_text)

    match_strings = " ".join(matches).lower()
    for c_key, c_text in cv_skills_map.items():
        if c_key not in match_strings and c_key not in job_skills_map:
            extras.append(c_text)

    context = {'app': application, 'matches': matches, 'misses': misses, 'extras': extras}
    return render(request, 'application_detail.html', context)


@login_required
def hr_upload_cv(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        success_count = 0
        errors = []

        bulk_files = request.FILES.getlist('bulk_cvs')
        for f in bulk_files:
            try:
                clean_name = f.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                unique_id = str(uuid.uuid4())[:8]
                placeholder_email = f"{clean_name.replace(' ', '.').lower()}.{unique_id}@pending.parsing"
                candidate, created = User.objects.get_or_create(
                    email=placeholder_email, defaults={'full_name': clean_name, 'role': 'Candidate'}
                )
                if created:
                    candidate.set_unusable_password()
                    candidate.save()
                app = Application.objects.create(job=job, candidate=candidate, cv_file=f, has_reference=False)
                process_application(app)
                success_count += 1
            except Exception as e:
                errors.append(f"Bulk File Error ({f.name}): {str(e)}")

        names = request.POST.getlist('full_name')
        emails = request.POST.getlist('email')
        refs = request.POST.getlist('reference_name')
        files = request.FILES.getlist('cv_file')

        if names and files:
            for i in range(len(names)):
                if not names[i] or not files[i]: continue
                try:
                    name = names[i]; email = emails[i]; cv_file = files[i]
                    ref_name = refs[i] if i < len(refs) else ''
                    candidate, created = User.objects.get_or_create(
                        email=email, defaults={'full_name': name, 'role': 'Candidate'}
                    )
                    if created:
                        candidate.set_unusable_password()
                        candidate.save()
                    if Application.objects.filter(job=job, candidate=candidate).exists():
                        errors.append(f"Skipped {name}: Already applied.")
                        continue
                    app = Application.objects.create(
                        job=job, candidate=candidate, cv_file=cv_file,
                        has_reference=bool(ref_name), reference_name=ref_name
                    )
                    process_application(app)
                    success_count += 1
                except Exception as e:
                    errors.append(f"Row {i+1} Error: {str(e)}")

        if success_count > 0: messages.success(request, f"Successfully processed {success_count} applications!")
        if errors:
            for err in errors: messages.error(request, err)
        return redirect('web_test:job_ranking', job_id=job.id)
    else:
        form = HRUploadCVForm()
    return render(request, 'hr_upload_cv.html', {'form': form, 'job': job})


@login_required
def send_interview_invite(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    
    if request.user.role != 'HR':
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            # UPDATE STATUS TO SHORTLISTED
            application.status = 'SHORTLISTED'
            application.save()

            subject = f"Interview Invitation: {application.job.title}"
            message_body = (
                f"Dear {application.candidate.full_name},\n\n"
                f"You have been Shortlisted for an Interview!\n\n"
                f"📅 Date: {data['date']}\n"
                f"⏰ Time: {data['time']}\n"
                f"📍 Location: {data['location']}\n\n"
                f"Notes: {data['message']}\n\n"
                f"Best regards,\nSmart Hire Solutions Team"
            )

            try:
                send_mail(
                    subject, message_body,
                    settings.EMAIL_HOST_USER or 'noreply@smarthire.com',
                    [application.candidate.email], fail_silently=False,
                )
                messages.success(request, f"Invite sent & Candidate Shortlisted!")
            except Exception as e:
                messages.error(request, f"Error sending email: {e}")

            return redirect('web_test:job_ranking', job_id=application.job.id)
    
    return redirect('web_test:job_ranking', job_id=application.job.id)

@login_required
def bulk_send_invite(request):
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            ids_str = form.cleaned_data['application_ids']
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            location = form.cleaned_data['location']
            notes = form.cleaned_data['message']

            app_ids = [int(id) for id in ids_str.split(',') if id.isdigit()]
            applications = Application.objects.filter(id__in=app_ids)
            success_count = 0
            errors = []
            
            for app in applications:
                # UPDATED: Set status to SHORTLISTED (Shortlisted for Interview)
                app.status = 'SHORTLISTED'
                app.save()
                
                subject = f"Interview Invitation: {app.job.title}"
                message_body = (
                    f"Dear {app.candidate.full_name},\n\n"
                    f"You have been Shortlisted for an Interview!\n\n"
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
                    errors.append(f"{app.candidate.email}: {str(e)}")

            if success_count > 0:
                messages.success(request, f"✅ Sent invites to {success_count} candidates!")
            
            if errors:
                messages.error(request, f"❌ Failed to send {len(errors)} emails. Check console for details.")
                for err in errors: print(f"EMAIL ERROR: {err}")

            if applications.exists():
                return redirect('web_test:job_ranking', job_id=applications.first().job.id)
            
    return redirect('web_test:job_list')


@login_required
def candidate_job_status(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.user.role != 'Candidate':
        return redirect('web_test:job_list')
    application = get_object_or_404(Application, job=job, candidate=request.user)
    return render(request, 'candidate_status.html', {'application': application, 'job': job})

@login_required
def withdraw_application(request, application_id):
    app = get_object_or_404(Application, pk=application_id, candidate=request.user)
    if app.status == 'APPLIED':
        app.delete()
        messages.success(request, "Your CV has been removed. You can now upload a new one.")
    else:
        messages.error(request, "You cannot delete your CV at this stage (already processed).")
    return redirect('web_test:job_list')


@login_required
def cv_builder(request):
    """
    Candidate Tool: Generate an ATS-friendly CV PDF.
    Updated to handle dynamic fields for Experience, Education, and Projects.
    """
    if request.user.role != 'Candidate':
        messages.error(request, "This tool is for candidates only.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = CVBuilderForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # --- PROCESS DYNAMIC EXPERIENCE FIELDS ---
            exp_titles = request.POST.getlist('exp_title')
            exp_companies = request.POST.getlist('exp_company')
            exp_dates = request.POST.getlist('exp_date')
            exp_positions = request.POST.getlist('exp_position')
            
            data['experience_list'] = []
            for i in range(len(exp_titles)):
                if exp_titles[i]: # Only add if title exists
                    data['experience_list'].append({
                        'title': exp_titles[i],
                        'company': exp_companies[i],
                        'dates': exp_dates[i],
                        'position': exp_positions[i]
                    })

            # --- PROCESS DYNAMIC EDUCATION FIELDS ---
            edu_degrees = request.POST.getlist('edu_degree')
            edu_colleges = request.POST.getlist('edu_college')
            edu_dates = request.POST.getlist('edu_date')
            
            data['education_list'] = []
            for i in range(len(edu_degrees)):
                if edu_degrees[i]:
                    data['education_list'].append({
                        'degree': edu_degrees[i],
                        'college': edu_colleges[i],
                        'dates': edu_dates[i]
                    })

            # --- PROCESS DYNAMIC PROJECT FIELDS ---
            proj_names = request.POST.getlist('proj_name')
            proj_techs = request.POST.getlist('proj_tech')
            proj_descs = request.POST.getlist('proj_desc')
            proj_links = request.POST.getlist('proj_link')
            
            data['projects_list'] = []
            for i in range(len(proj_names)):
                if proj_names[i]:
                    data['projects_list'].append({
                        'name': proj_names[i],
                        'tech': proj_techs[i],
                        'desc': proj_descs[i],
                        'link': proj_links[i]
                    })

            # Generate PDF with structured data
            pdf_buffer = generate_ats_cv(data)
            
            # Return as Downloadable File
            filename = f"{data['full_name'].replace(' ', '_')}_CV.pdf"
            return FileResponse(
                pdf_buffer, 
                as_attachment=True, 
                filename=filename,
                content_type='application/pdf'
            )
    else:
        # Pre-fill some data from User profile if available
        initial_data = {
            'full_name': request.user.full_name,
            'email': request.user.email,
        }
        form = CVBuilderForm(initial=initial_data)

    return render(request, 'cv_builder.html', {'form': form})


@login_required
def delete_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # UPDATED: Allow HR and Reviewer to delete
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
def reject_application(request, pk):
    """
    Mark a candidate as Rejected.
    """
    app = get_object_or_404(Application, pk=pk)
    
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    app.status = 'REJECTED'
    app.save()
    messages.info(request, f"Candidate {app.candidate.full_name} has been rejected.")
    
    return redirect('web_test:job_ranking', job_id=app.job.id)




# --- EMPLOYEE MANAGEMENT (HR) ---
@login_required
def employee_list(request):
    if request.user.role not in ['HR', 'Admin']:
        messages.error(request, "Access Denied")
        return redirect('web_test:home')
    
    employees = Employee.objects.all().select_related('user')
    return render(request, 'employees/employee_list.html', {'employees': employees})

@login_required
def add_employee(request):
    if request.user.role not in ['HR', 'Admin']:
        return redirect('web_test:home')

    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST)
        if form.is_valid():
            # Create User
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            name = form.cleaned_data['full_name']
            
            try:
                user = User.objects.create_user(email=email, password=password, full_name=name, role='Employee')
                
                # Create Employee Profile
                employee = form.save(commit=False)
                employee.user = user
                employee.save()
                
                # Send Email
                send_mail(
                    'Your Employee Account',
                    f'Login with Email: {email}\nPassword: {password}',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=True
                )
                messages.success(request, "Employee created and email sent!")
                return redirect('web_test:employee_list')
            except Exception as e:
                messages.error(request, f"Error: {e}")
    else:
        form = EmployeeCreationForm()
    
    return render(request, 'employees/add_employee.html', {'form': form})

# --- PAYROLL (HR & EMPLOYEE) ---
@login_required
def payroll_dashboard(request):
    # HR sees all, Employee sees their own
    if request.user.role in ['HR', 'Admin']:
        payrolls = Payroll.objects.all().order_by('-month')
        form = PayrollForm() # For the modal/add section
        
        if request.method == 'POST':
            form = PayrollForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Payroll record created.")
                return redirect('web_test:payroll_dashboard')
                
    elif request.user.role == 'Employee':
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, "Employee profile not found.")
            return redirect('web_test:home')
        payrolls = Payroll.objects.filter(employee=request.user.employee_profile).order_by('-month')
        form = None
    else:
        return redirect('web_test:home')

    return render(request, 'employees/payroll.html', {'payrolls': payrolls, 'form': form})

# --- LEAVES ---
@login_required
def leave_dashboard(request):
    user = request.user
    form = LeaveRequestForm()

    # Handle Leave Application (Employee)
    if request.method == 'POST' and 'apply_leave' in request.POST:
        if user.role != 'Employee':
            messages.error(request, "Only employees can apply for leave.")
        else:
            form = LeaveRequestForm(request.POST)
            if form.is_valid():
                leave = form.save(commit=False)
                leave.employee = user.employee_profile
                leave.save()
                messages.success(request, "Leave request sent!")
                return redirect('web_test:leave_dashboard')

    # Handle Status Update (HR)
    if request.method == 'POST' and 'update_status' in request.POST:
        if user.role in ['HR', 'Admin']:
            leave_id = request.POST.get('leave_id')
            status = request.POST.get('status')
            leave = get_object_or_404(LeaveRequest, id=leave_id)
            leave.status = status
            leave.reviewed_by = user
            leave.save()
            messages.success(request, f"Leave marked as {status}")
            return redirect('web_test:leave_dashboard')

    # Data Fetching
    if user.role in ['HR', 'Admin']:
        leaves = LeaveRequest.objects.all().order_by('-start_date')# Assuming you add created_at or sort by start_date
    elif user.role == 'Employee':
        leaves = LeaveRequest.objects.filter(employee=user.employee_profile).order_by('-start_date')
    else:
        leaves = []

    return render(request, 'employees/leaves.html', {'leaves': leaves, 'form': form})