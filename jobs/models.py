from django.db import models
from django.conf import settings
from clients.models import ClientCompany   

class Job(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested by Client'
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
    client_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
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
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)

    # CLIENT REQUEST FIELDS
    target_candidates_count = models.IntegerField(default=1, help_text="How many candidates the client wants")
    
    # Workflow Settings
    client_does_final_interview = models.BooleanField(default=True, help_text="Will the client interview the final shortlist?")
    
    # --- NEW: JOINING & SALARY DETAILS ---
    
    # We keep monthly_salary for internal fee calculations
    monthly_salary = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Monthly Salary offered to the candidate per person (or Avg of Range)"
    )
    
    # New Fields for Range and Location
    salary_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        help_text="Minimum Monthly Salary"
    )
    salary_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        help_text="Maximum Monthly Salary"
    )
    office_location = models.CharField(
        max_length=255, null=True, blank=True, 
        help_text="Office Location (e.g. Dhaka, Remote)"
    )

    joining_date = models.DateField(null=True, blank=True, help_text="Expected Joining Date")

    # Exam Settings
    has_primary_exam = models.BooleanField(default=False)
    exam_passing_score = models.IntegerField(default=60, help_text="Score % required to pass")

    # FINANCIALS 
    salary_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Annual Salary Budget (Optional/Legacy)"
    )
    
    # Dynamic Service Fee %
    # Default set to 20.00 as requested, but editable per job
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00,
        help_text="Agency Fee % for this specific job (Dynamic)"
    )

    # AI DATA
    processed_text = models.TextField(blank=True, null=True)
    gliner_entities = models.JSONField(blank=True, null=True)
    jina_embedding = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """
        Auto-calculates monthly_salary from the range if not explicitly provided.
        This ensures agency fee calculations continue to work.
        """
        if self.salary_min and self.salary_max and not self.monthly_salary:
            self.monthly_salary = (self.salary_min + self.salary_max) / 2
        super().save(*args, **kwargs)

    @property
    def agency_fee_total(self):
        """
        Calculates total fee: (Monthly Salary * Commission Rate %) * Number of Hires
        """
        if self.monthly_salary and self.commission_rate and self.target_candidates_count:
            # Fee per candidate
            one_candidate_fee = self.monthly_salary * (self.commission_rate / 100)
            # Total fee for all requested candidates
            return one_candidate_fee * self.target_candidates_count
        return 0

    @property
    def expected_revenue(self):
        # Kept for backward compatibility if templates use it
        return self.agency_fee_total

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