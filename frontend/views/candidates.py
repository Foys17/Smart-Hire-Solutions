from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import FileResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_POST
import uuid
import json

from jobs.models import Job,Question
from candidates.models import Application,Offer
from candidates.utils import process_application, search_global_talent, extract_text_from_pdf
from frontend.forms import ApplicationForm, HRUploadCVForm, InterviewInviteForm, CVBuilderForm,OfferForm,CandidateNegotiationForm
from frontend.utils import generate_ats_cv
from users.models import Notification

User = get_user_model()

# --- CANDIDATE ACTIONS ---

def apply_for_job(request, job_id):
    if not request.user.is_authenticated:
        messages.info(request, "Please register or login to apply for this job.")
        return redirect('web_test:register')

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
            
            #EXAM CHECK
            if job.has_primary_exam:
                app.status = 'PENDING_EXAM' # Don't show in HR dashboard yet
                app.save()
                messages.info(request, "Step 1 Complete. Now please take the primary skill assessment.")
                return redirect('web_test:take_exam', application_id=app.id)
            else:
                app.status = 'APPLIED'
                app.save()
                process_application(app) # Run AI Scoring immediately
                messages.success(request, f"Applied to {job.title}. AI Score Calculated!")
                return redirect('web_test:job_list')
    else:
        form = ApplicationForm()
    
    return render(request, 'apply_job.html', {'form': form, 'job': job})

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
    if request.user.role != 'Candidate':
        messages.error(request, "This tool is for candidates only.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        form = CVBuilderForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # Process Dynamic Fields (Experience, Education, Projects)
            exp_titles = request.POST.getlist('exp_title')
            exp_companies = request.POST.getlist('exp_company')
            exp_dates = request.POST.getlist('exp_date')
            exp_positions = request.POST.getlist('exp_position')
            
            data['experience_list'] = []
            for i in range(len(exp_titles)):
                if exp_titles[i]:
                    data['experience_list'].append({
                        'title': exp_titles[i], 'company': exp_companies[i],
                        'dates': exp_dates[i], 'position': exp_positions[i]
                    })

            edu_degrees = request.POST.getlist('edu_degree')
            edu_colleges = request.POST.getlist('edu_college')
            edu_dates = request.POST.getlist('edu_date')
            
            data['education_list'] = []
            for i in range(len(edu_degrees)):
                if edu_degrees[i]:
                    data['education_list'].append({
                        'degree': edu_degrees[i], 'college': edu_colleges[i], 'dates': edu_dates[i]
                    })

            proj_names = request.POST.getlist('proj_name')
            proj_techs = request.POST.getlist('proj_tech')
            proj_descs = request.POST.getlist('proj_desc')
            proj_links = request.POST.getlist('proj_link')
            
            data['projects_list'] = []
            for i in range(len(proj_names)):
                if proj_names[i]:
                    data['projects_list'].append({
                        'name': proj_names[i], 'tech': proj_techs[i],
                        'desc': proj_descs[i], 'link': proj_links[i]
                    })

            pdf_buffer = generate_ats_cv(data)
            filename = f"{data['full_name'].replace(' ', '_')}_CV.pdf"
            return FileResponse(pdf_buffer, as_attachment=True, filename=filename, content_type='application/pdf')
    else:
        initial_data = {'full_name': request.user.full_name, 'email': request.user.email}
        form = CVBuilderForm(initial=initial_data)

    return render(request, 'cv_builder.html', {'form': form})

# --- HR ACTIONS ---

@login_required
def job_ranking(request, job_id): # function for ranking candidates based on a job
    job = get_object_or_404(Job, pk=job_id)
    apps = Application.objects.filter(job=job)
    if request.GET.get('ref'):
        apps = apps.filter(has_reference=True)
    apps = apps.order_by('-match_score') #(-) Highest to lowest
    return render(request, 'ranking.html', {'job': job, 'applications': apps})

@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    
    if request.user.role != 'HR' and request.user != application.candidate:
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    # Skill matching logic
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
    
    # Simple year matching logic
    req_years = 0
    cand_years = 0.0
    if application.job.gliner_entities:
        for item in application.job.gliner_entities:
            if item.get('label') == 'Min_Years_Req':
                try: req_years = int(item['text']); break
                except: pass
    if application.extracted_data:
        for item in application.extracted_data:
            if item.get('label') == 'Total_Years_Calc':
                try: cand_years = float(item['text']); break
                except: pass

    if req_years > 0:
        if cand_years >= req_years: matches.insert(0, f"✅ {cand_years} Years Experience (Matches {req_years}+ Req)")
        else: misses.insert(0, f"❌ Requires {req_years}+ Years (Has {cand_years})")
    elif cand_years > 0: extras.insert(0, f"{cand_years} Years Total Experience")

    synonyms = {"drf": "django rest framework", "reactjs": "react", "js": "javascript", "aws": "amazon web services"}

    #This loop checks for the exact match between the job and CV
    for j_key, j_text in job_skills_map.items():
        matched = False
        if j_key in cv_skills_map:
            matches.append(j_text); matched = True
        else: #exact word match na korle eita substring match korar kaj kore
            for c_key, c_text in cv_skills_map.items():
                if len(c_key) > 2 and len(j_key) > 2 and (c_key in j_key or j_key in c_key):
                    matches.append(f"{c_text} (matches {j_text})"); matched = True; break
                std_j = synonyms.get(j_key, j_key)
                std_c = synonyms.get(c_key, c_key)
                if std_j == std_c or std_c in std_j:
                    matches.append(f"{c_text} (matches {j_text})"); matched = True; break
        if not matched: misses.append(j_text)

    match_strings = " ".join(matches).lower()
    for c_key, c_text in cv_skills_map.items():
        if c_key not in match_strings and c_key not in job_skills_map:
            extras.append(c_text)

    context = {'app': application, 'matches': matches, 'misses': misses, 'extras': extras}
    return render(request, 'application_detail.html', context)

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
def reject_application(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')
    app.status = 'REJECTED'
    app.save()
    messages.info(request, f"Candidate {app.candidate.full_name} has been rejected.")
    return redirect('web_test:job_ranking', job_id=app.job.id)

@login_required
def hr_upload_cv(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.user.role != 'HR':
        messages.error(request, "Access Denied.")
        return redirect('web_test:job_list')

    if request.method == 'POST':
        success_count = 0
        errors = []
        
        # 1. Bulk Files
        bulk_files = request.FILES.getlist('bulk_cvs')
        for f in bulk_files:
            try:
                clean_name = f.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                unique_id = str(uuid.uuid4())[:8]
                placeholder_email = f"{clean_name.replace(' ', '.').lower()}.{unique_id}@pending.parsing"
                candidate, created = User.objects.get_or_create(email=placeholder_email, defaults={'full_name': clean_name, 'role': 'Candidate'})
                if created: candidate.set_unusable_password(); candidate.save()
                app = Application.objects.create(job=job, candidate=candidate, cv_file=f, has_reference=False)
                process_application(app)
                success_count += 1
            except Exception as e: errors.append(f"Bulk File Error ({f.name}): {str(e)}")

        # 2. Manual Entry
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
                    candidate, created = User.objects.get_or_create(email=email, defaults={'full_name': name, 'role': 'Candidate'})
                    if created: candidate.set_unusable_password(); candidate.save()
                    if Application.objects.filter(job=job, candidate=candidate).exists(): errors.append(f"Skipped {name}: Already applied."); continue
                    app = Application.objects.create(job=job, candidate=candidate, cv_file=cv_file, has_reference=bool(ref_name), reference_name=ref_name)
                    process_application(app)
                    success_count += 1
                except Exception as e: errors.append(f"Row {i+1} Error: {str(e)}")

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
    if request.user.role != 'HR': return redirect('web_test:job_list')

    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            application.status = 'SHORTLISTED'
            application.save()
            subject = f"Interview Invitation: {application.job.title}"
            message_body = f"Dear {application.candidate.full_name},\n\nShortlisted for Interview!\nDate: {data['date']}\nTime: {data['time']}\nLocation: {data['location']}\nNotes: {data['message']}"
            try:
                send_mail(subject, message_body, settings.EMAIL_HOST_USER, [application.candidate.email], fail_silently=False)
                messages.success(request, f"Invite sent & Candidate Shortlisted!")
            except Exception as e: messages.error(request, f"Error sending email: {e}")
            return redirect('web_test:job_ranking', job_id=application.job.id)
    return redirect('web_test:job_ranking', job_id=application.job.id)

@login_required
def bulk_send_invite(request):
    if request.user.role != 'HR': return redirect('web_test:job_list')
    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            ids_str = form.cleaned_data['application_ids']
            app_ids = [int(id) for id in ids_str.split(',') if id.isdigit()]
            applications = Application.objects.filter(id__in=app_ids)
            success_count = 0
            for app in applications:
                app.status = 'SHORTLISTED'; app.save()
                try:
                    send_mail(f"Interview: {app.job.title}", f"Hi {app.candidate.full_name}, Interview details: {form.cleaned_data['date']}", settings.EMAIL_HOST_USER, [app.candidate.email], fail_silently=False)
                    success_count += 1
                except: pass
            messages.success(request, f"Sent {success_count} invites.")
            if applications.exists(): return redirect('web_test:job_ranking', job_id=applications.first().job.id)
    return redirect('web_test:job_list')

@login_required
def talent_pool(request):
    if request.user.role not in ['HR', 'Admin']:
        messages.error(request, "Access Denied")
        return redirect('web_test:home')
    query = request.GET.get('q', '')
    results = []
    if request.method == 'POST' and request.FILES.get('jd_file'):
        uploaded_file = request.FILES['jd_file']
        if uploaded_file.name.endswith('.pdf'):
            try:
                extracted_text = extract_text_from_pdf(uploaded_file)
                query = extracted_text[:1000]
                messages.success(request, f"Searching from file: {uploaded_file.name}")
            except Exception as e: messages.error(request, f"Error: {e}")
    if query:
        try:
            results = search_global_talent(query)
            if not results: messages.info(request, "No matching talent found.")
        except Exception as e: messages.error(request, f"Search Error: {str(e)}")
    return render(request, 'talent_pool.html', {'query': query, 'results': results})

@login_required
def invite_candidate(request, application_id):
    if request.user.role not in ['HR', 'Admin']: return redirect('web_test:home')
    app = get_object_or_404(Application, id=application_id)
    job_board_url = request.build_absolute_uri(reverse('web_test:job_list'))
    try:
        send_mail("Invitation to Apply", f"Hi {app.candidate.full_name},\nApply here: {job_board_url}", settings.EMAIL_HOST_USER, [app.candidate.email], fail_silently=False)
        messages.success(request, f"Invitation sent to {app.candidate.full_name}!")
    except Exception as e: messages.error(request, f"Failed: {e}")
    return redirect(request.META.get('HTTP_REFERER', 'web_test:talent_pool'))

@login_required
def kanban_board(request):
    if request.user.role not in ['HR', 'Admin']: return redirect('web_test:home')
    selected_job_id = request.GET.get('job_id')
    applications = Application.objects.select_related('candidate', 'job').all()
    if selected_job_id: applications = applications.filter(job_id=selected_job_id)
    
    columns = {
        'APPLIED': [],
        'INTERVIEW': [],       
        'CLIENT_REVIEW': [],
        'FINAL_INTERVIEW': [],
        'OFFER': [],
        'HIRED': [],
        'REJECTED': []
    }
    
    for app in applications:
        if app.status in columns: 
            columns[app.status].append(app)
        else: 
            columns['APPLIED'].append(app)
            
    jobs = Job.objects.filter(status='OPEN')
    context = {'columns': columns, 'jobs': jobs, 'selected_job_id': int(selected_job_id) if selected_job_id else None}
    return render(request, 'kanban_board.html', context)


@login_required
def quick_move_candidate(request, app_id, target_stage):
    app = get_object_or_404(Application, pk=app_id)
    
    # Security: Ensure HR/Admin
    if request.user.role not in ['HR', 'Admin']:
        messages.error(request, "Access Denied.")
        return redirect('web_test:kanban_board')

    # Update Status
    app.status = target_stage
    app.save()

    # NOTIFICATION LOGIC 
    if target_stage == 'CLIENT_REVIEW' and app.job.client_contact:
        Notification.objects.create(
            user=app.job.client_contact,
            message=f"Candidate Ready for Review: {app.candidate.full_name}",
            link=reverse('web_test:client_dashboard')
        )
        messages.success(request, f"Moved to Client & Notification sent to {app.job.client_contact.full_name}")
    else:
        messages.success(request, f"Moved {app.candidate.full_name} to {app.get_status_display()}")

    return redirect('web_test:kanban_board')

@login_required
@require_POST
def update_application_status(request):
    try:
        data = json.loads(request.body)
        app = Application.objects.get(id=data.get('app_id'))
        app.status = data.get('new_status')
        app.save()
        return JsonResponse({'success': True})
    except Exception as e: return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def schedule_interview_view(request, app_id):
    app = get_object_or_404(Application, pk=app_id)
    
    if request.method == 'POST':
        form = InterviewInviteForm(request.POST)
        if form.is_valid():
            # Extract data
            reviewer = form.cleaned_data['reviewer']
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            location = form.cleaned_data['location']
            message = form.cleaned_data['message']

            # 1. Update Application & SAVE ALL FIELDS
            app.status = 'INTERVIEW'
            app.assigned_reviewer = reviewer
            app.interview_date = f"{date} {time}" 
            app.interview_location = location     
            app.interview_note = message         
            app.save()
            
            # 2. Notify Reviewer
            Notification.objects.create(
                user=app.assigned_reviewer,
                message=f"New Interview Assignment: {app.candidate.full_name}",
                link=reverse('web_test:reviewer_dashboard')
            )

            # 3. Notify Candidate -> Redirect to Status Page
            Notification.objects.create(
                user=app.candidate,
                message=f"📅 Interview Scheduled: {date} at {time}. Click to view details.",
                link=reverse('web_test:candidate_job_status', args=[app.job.id])
            )
            
            messages.success(request, f"Interview scheduled! Notification sent to {app.candidate.full_name}")
            return redirect('web_test:kanban_board')
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.warning(request, f"⚠️ {field.title()}: {error}")
    else:
        form = InterviewInviteForm(initial={'application_ids': app.id})

    return render(request, 'hr/schedule_interview.html', {'form': form, 'app': app})



@login_required
def create_offer(request, application_id):
    if request.user.role not in ['HR', 'Admin']:
        return redirect('web_test:home')
        
    app = get_object_or_404(Application, pk=application_id)
    
    # Check if offer exists to allow editing
    try:
        existing_offer = app.offer_letter
    except Offer.DoesNotExist:
        existing_offer = None

    if request.method == 'POST':
        form = OfferForm(request.POST, instance=existing_offer) #offer exist korle edit korbe na exist korle new banabe
        if form.is_valid():
            offer = form.save(commit=False)
            offer.application = app
            offer.save()
            
            # Update Status
            app.status = 'OFFER'
            app.save()
            
            # --- NOTIFY CANDIDATE ---
            Notification.objects.create(
                user=app.candidate,
                message=f"🎉 Congratulations! You have received a job offer for {app.job.title}.",
                link=reverse('web_test:view_offer', args=[app.id])
            )
            
            action = "updated" if existing_offer else "created"
            messages.success(request, f"Offer {action} and sent to {app.candidate.full_name}!")
            return redirect('web_test:kanban_board')
    else:
        form = OfferForm(instance=existing_offer)
        
    return render(request, 'hr/create_offer.html', {'form': form, 'app': app})

@login_required
def view_offer(request, application_id): #candidate nijer offer dekhte parar function
    app = get_object_or_404(Application, id=application_id)
    
    if app.candidate != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:home')
        
    return render(request, 'candidates/view_offer.html', {'application': app})

@login_required
def respond_offer(request, application_id, response): #candidate offer accept or reject korar function
    app = get_object_or_404(Application, id=application_id)

    if app.candidate != request.user:
        messages.error(request, "Unauthorized access.")
        return redirect('web_test:home')

    if app.status != 'OFFER':
        messages.error(request, "This application does not have a pending offer.")
        return redirect('web_test:home')

    if response == 'ACCEPT':
        app.status = 'HIRED'
        app.save()

        if app.job.client_contact:
            Notification.objects.create(
                user=app.job.client_contact,
                message=f"🎉 Offer ACCEPTED! {app.candidate.full_name} has joined the team for {app.job.title}.",
                link=reverse('web_test:client_job_view', args=[app.job.id])
            )
        
        messages.success(request, f"Congratulations! You have successfully accepted the offer for {app.job.title}.")

    elif response == 'DECLINE':
        app.status = 'REJECTED' 
        app.save()
        
        # Notify Client
        if app.job.client_contact:
            Notification.objects.create(
                user=app.job.client_contact,
                message=f"Offer Declined. {app.candidate.full_name} has declined the offer for {app.job.title}.",
                link=reverse('web_test:client_job_view', args=[app.job.id])
            )

        messages.info(request, "You have declined the job offer.")

    return redirect('web_test:home')



@login_required
def candidate_negotiation(request, application_id):
    app = get_object_or_404(Application, pk=application_id)
    
    if app.candidate != request.user:
        messages.error(request, "Access Denied")
        return redirect('web_test:home')
    
    if request.method == 'POST':
        form = CandidateNegotiationForm(request.POST, instance=app)
        if form.is_valid():
            app = form.save(commit=False)
            app.status = 'NEGOTIATION_SUBMITTED'
            app.save()
            
            # Notify Client
            if app.job.client_contact:
                Notification.objects.create(
                    user=app.job.client_contact,
                    message=f"Counter-Offer Received: {app.candidate.full_name} has submitted expected salary & date.",
                    link=reverse('web_test:client_job_view', args=[app.job.id])
                )
            
            messages.success(request, "Your requirements have been sent to the client!")
            return redirect('web_test:candidate_job_status', job_id=app.job.id)
    else:
        form = CandidateNegotiationForm(instance=app)
        
    return render(request, 'candidates/negotiation.html', {'form': form, 'app': app})