from django.db import models
from django.conf import settings
from clients.models import ClientCompany   

class Job(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'
        FILLED = 'FILLED', 'Filled'

    # The Company Entity (e.g. "Google")
    client = models.ForeignKey(
        ClientCompany, 
        on_delete=models.CASCADE, 
        related_name='jobs',
        null=True, blank=True 
    )
    
    # NEW: The Human Client (e.g. "John Doe at Google")
    # This allows the specific user to log in and see this job.
    client_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, # If user is deleted, keep the job
        related_name='client_jobs',
        null=True, 
        blank=True,
        help_text="The external client user who can view this job in the portal."
    )
    
    # The Recruiter (You)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='posted_jobs' # Added related_name to avoid conflicts
    )

    # JOB DETAILS
    title = models.CharField(max_length=255)
    description_text = models.TextField(blank=True, null=True)
    description_file = models.FileField(upload_to='job_descriptions/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    # FINANCIALS 
    salary_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Annual Salary Budget (for commission calc)"
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00,
        help_text="Agency Fee % for this specific job"
    )

    # AI DATA
    processed_text = models.TextField(blank=True, null=True)
    gliner_entities = models.JSONField(blank=True, null=True)
    jina_embedding = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        client_name = self.client.name if self.client else "Internal"
        return f"{self.title} ({client_name})"
    
    @property
    def expected_revenue(self):
        if self.salary_budget and self.commission_rate:
            return (self.salary_budget * self.commission_rate) / 100
        return 0