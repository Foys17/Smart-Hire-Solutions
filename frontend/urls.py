from django.urls import path
from . import views

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
    # Employee Module
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.add_employee, name='add_employee'),
    path('payroll/', views.payroll_dashboard, name='payroll_dashboard'),
    path('leaves/', views.leave_dashboard, name='leave_dashboard'),
]