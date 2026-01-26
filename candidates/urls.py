from django.urls import path
from .views import (
    ApplyJobView, 
    CandidateMyApplicationsView, 
    JobApplicationsListView,
    HRAddReferenceView,      
    SendInterviewInviteView   
)
app_name = 'candidates'

urlpatterns = [
    # Candidate
    path('apply/', ApplyJobView.as_view(), name='apply'),
    path('my-applications/', CandidateMyApplicationsView.as_view(), name='my-applications'),

    # HR / Reviewer
    path('job/<int:job_id>/ranking/', JobApplicationsListView.as_view(), name='job-ranking'),
    
    path('hr/upload-reference/', HRAddReferenceView.as_view(), name='hr-upload-reference'),
    path('application/<int:pk>/invite/', SendInterviewInviteView.as_view(), name='send-invite'),
]