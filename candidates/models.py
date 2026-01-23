from django.db import models
from django.conf import settings
from jobs.models import Job

STATUS_CHOICES = (
    ('PENDING_EXAM', 'Pending Exam'),
    ('APPLIED', 'Applied'),
    ('INTERVIEW', 'Internal Interview'),
    ('CLIENT_REVIEW', 'Client Review'),
    ('FINAL_INTERVIEW', 'Final Interview'),
    ('NEGOTIATION', 'Salary Negotiation'),           
    ('NEGOTIATION_SUBMITTED', 'Negotiation Submitted'), 
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
    cv_embedding = models.JSONField(blank=True, null=True) 
    match_score = models.FloatField(default=0.0)
    
    # Additional Info
    has_reference = models.BooleanField(default=False)
    reference_name = models.CharField(max_length=255, blank=True, null=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_location = models.CharField(max_length=255, null=True, blank=True)
    interview_note = models.TextField(null=True, blank=True)
    offer_salary = models.CharField(max_length=100, null=True, blank=True, help_text="e.g. $5,000/month")
    offer_start_date = models.DateField(null=True, blank=True)
    offer_message = models.TextField(null=True, blank=True, help_text="Personal note or official terms")
    candidate_expected_salary = models.CharField(
        max_length=100, null=True, blank=True, 
        help_text="Candidate's expected salary input"
    )
    candidate_joining_date = models.DateField(
        null=True, blank=True,
        help_text="Candidate's expected joining date"
    )
    # Pipeline Status
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='APPLIED')
    
    # Reviewer Assignment
    assigned_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_interviews'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('job', 'candidate')

    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title} ({self.status})"
    

class Offer(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='offer_letter')
    salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly or Yearly Salary")
    start_date = models.DateField()
    benefits = models.TextField(blank=True, help_text="List of benefits (Health, Remote, etc.)")
    expiration_date = models.DateField(null=True, blank=True)
    
    # Status of the specific offer document
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending Decision'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined')
    ], default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Offer for {self.application.candidate.full_name} - {self.status}"