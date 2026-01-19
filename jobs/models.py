from django.db import models
from django.conf import settings
from clients.models import ClientCompany   

class Job(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested by Client' # <--- NEW STATUS
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
    
    # The Human Client (e.g. "John Doe at Google")
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
        related_name='posted_jobs' 
    )

    # JOB DETAILS
    title = models.CharField(max_length=255)
    description_text = models.TextField(blank=True, null=True)
    description_file = models.FileField(upload_to='job_descriptions/', blank=True, null=True)
    
    # Updated max_length to 20 to fit 'REQUESTED' and set default
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)

    # CLIENT REQUEST FIELDS
    target_candidates_count = models.IntegerField(default=1, help_text="How many candidates the client wants")
    
    # Workflow Settings
    client_does_final_interview = models.BooleanField(default=True, help_text="Will the client interview the final shortlist?")
    
    # Exam Settings
    has_primary_exam = models.BooleanField(default=False)
    exam_passing_score = models.IntegerField(default=60, help_text="Score % required to pass")
    # REMOVED: exam_link = models.URLField(...) 

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
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def expected_revenue(self):
        if self.salary_budget and self.commission_rate:
            return (self.salary_budget * self.commission_rate) / 100
        return 0

# --- NEW EXAM MODELS ---

class Question(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    
    # We store choices as a simple list: ["Option A", "Option B", "Option C", "Option D"]
    choices = models.JSONField(help_text='List of 4 options strings') 
    
    # 0 for Option A, 1 for Option B, etc.
    correct_answer_index = models.IntegerField(help_text="Index of the correct option (0-3)")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:50]}..."

class ExamAttempt(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    score = models.FloatField()
    passed = models.BooleanField(default=False)
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "PASSED" if self.passed else "FAILED"
        return f"{self.candidate.full_name} - {self.job.title}: {self.score}% ({status})"