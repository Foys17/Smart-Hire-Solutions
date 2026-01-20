from django.urls import path
from . import views
from reviewer import views as reviewer_views

app_name = 'web_test'

urlpatterns = [
    # Auth URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Home
    path('', views.home, name='home'),

    # Jobs
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.create_job, name='create_job'),
    path('jobs/<int:job_id>/apply/', views.apply_for_job, name='apply_job'),
    path('jobs/<int:job_id>/ranking/', views.job_ranking, name='job_ranking'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<int:pk>/delete/', views.delete_job, name='delete_job'),
    path('jobs/<int:pk>/toggle-status/', views.toggle_job_status, name='toggle_job_status'),

    # Application Management
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('application/<int:pk>/delete/', views.delete_application, name='delete_application'), # NEW
    
    path('jobs/<int:job_id>/upload-cv/', views.hr_upload_cv, name='hr_upload_cv'),
    path('application/<int:application_id>/invite/', views.send_interview_invite, name='send_interview_invite'),
    path('bulk-invite/', views.bulk_send_invite, name='bulk_send_invite'),
    path('jobs/<int:job_id>/status/', views.candidate_job_status, name='candidate_job_status'),
    path('application/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('tools/cv-builder/', views.cv_builder, name='cv_builder'),
    path('application/<int:pk>/reject/', views.reject_application, name='reject_application'),
    path('talent-pool/', views.talent_pool, name='talent_pool'),
    path('talent-pool/invite/<int:application_id>/', views.invite_candidate, name='invite_candidate'),
    path('kanban/', views.kanban_board, name='kanban_board'),
    path('api/update-status/', views.update_application_status, name='update_status_api'),

    #for client
    path('portal/', views.client_dashboard, name='client_dashboard'),
    path('portal/request/', views.client_create_request, name='client_create_request'),  
    path('portal/job/<int:job_id>/', views.client_job_view, name='client_job_view'),
    path('portal/decide/<int:application_id>/<str:decision>/', views.client_decision, name='client_decision'),
    path('portal/job/<int:job_id>/questions/', views.add_questions_view, name='client_add_questions'),
    path('portal/question/<int:question_id>/delete/', views.delete_question, name='client_delete_question'),
    path('portal/request/<int:job_id>/edit/', views.client_edit_request, name='client_edit_request'),
    path('portal/request/<int:job_id>/delete/', views.client_delete_request, name='client_delete_request'),
    path('portal/question/<int:question_id>/edit/', views.client_edit_question, name='client_edit_question'),

    # HR Actions
    path('hr/requests/', views.hr_pending_requests, name='hr_pending_requests'),
    path('hr/request/<int:job_id>/approve/', views.hr_approve_request, name='hr_approve_request'),
    path('hr/request/<int:job_id>/reject/', views.hr_reject_request, name='hr_reject_request'),
    #for primary exam
    path('exam/<int:application_id>/', views.take_exam, name='take_exam'),

    # --- REVIEWER PORTAL ---
    path('reviewer/dashboard/', reviewer_views.reviewer_dashboard, name='reviewer_dashboard'),
    path('reviewer/score/<int:app_id>/', reviewer_views.submit_review, name='submit_review'),
    path('candidate/<int:app_id>/schedule/', views.schedule_interview_view, name='schedule_interview'),

    # --- KANBAN ACTIONS ---
    path('candidate/move/<int:app_id>/<str:target_stage>/', views.quick_move_candidate, name='quick_move'),
    path('candidate/<int:app_id>/schedule/', views.schedule_interview_view, name='schedule_interview'),


    # --- OFFER MANAGEMENT ---
    path('application/<int:application_id>/create-offer/', views.create_offer, name='create_offer'),
    path('application/<int:application_id>/view-offer/', views.view_offer, name='view_offer'),
    path('offer/<int:offer_id>/respond/<str:response>/', views.respond_offer, name='respond_offer'),
]

