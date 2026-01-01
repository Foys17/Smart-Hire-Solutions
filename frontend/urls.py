from django.urls import path
from . import views

app_name = 'web_test'

urlpatterns = [
    # Auth URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Your existing URLs
    path('', views.dashboard, name='dashboard'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.create_job, name='create_job'),
    path('jobs/<int:job_id>/apply/', views.apply_for_job, name='apply_job'),
    path('jobs/<int:job_id>/ranking/', views.job_ranking, name='job_ranking'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),      # New: View Details
    path('jobs/<int:pk>/edit/', views.job_edit, name='job_edit'),     # New: Edit Job
    
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),

]