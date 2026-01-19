from django.db import models
from django.conf import settings
from jobs.models import Job

# --- UPDATED KANBAN STAGES ---
STATUS_CHOICES = (
    ('PENDING_EXAM', 'Pending Exam'),
    ('APPLIED', 'New Applied'),
    ('SCREENING', 'Screening'),
    ('INTERVIEW', 'Internal Interview'),
    ('CLIENT_REVIEW', 'Shared with Client'),
    ('FINAL_INTERVIEW', 'Final Interview'),
    ('OFFER', 'Offer Sent'),
    ('HIRED', 'Hired'),
    ('REJECTED', 'Rejected'),
)

class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    
    # CV Data
    cv_file = models.FileField(upload_to='cvs/')
    cv_text_content = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    
    # AI Fields
    # Changed to null=True so we can easily filter non-embedded CVs
    cv_embedding = models.JSONField(blank=True, null=True) 
    match_score = models.FloatField(default=0.0)
    
    # Additional Info
    has_reference = models.BooleanField(default=False)
    reference_name = models.CharField(max_length=255, blank=True, null=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    
    # Pipeline Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLIED')
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_interviews'
    )

    class Meta:
        unique_together = ('job', 'candidate')

    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title} ({self.status})"
    
    