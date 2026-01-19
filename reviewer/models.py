from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from candidates.models import Application

class InterviewScore(models.Model):
    # Link to the specific application (Candidate + Job)
    application = models.OneToOneField(
        Application, 
        on_delete=models.CASCADE, 
        related_name='interview_score'
    )
    
    # Who gave this score?
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='reviews_given'
    )
    
    # SCORING METRICS (Scale 1-10)
    technical_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], 
        help_text="Coding capabilities and technical knowledge (1-10)"
    )
    communication_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], 
        help_text="Clarity, language, and articulation (1-10)"
    )
    problem_solving_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], 
        help_text="Logical thinking and approach to challenges (1-10)"
    )
    cultural_fit_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], 
        help_text="Attitude, teamwork, and company fit (1-10)"
    )
    
    # Qualitative Feedback
    comments = models.TextField(
        blank=True, 
        help_text="Detailed feedback or notes for the Client/HR"
    )
    
    # Auto-calculated Average
    average_score = models.FloatField(editable=False, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Automatically calculate the average before saving
        total = (
            self.technical_score + 
            self.communication_score + 
            self.problem_solving_score + 
            self.cultural_fit_score
        )
        self.average_score = round(total / 4.0, 1) # Round to 1 decimal
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application.candidate.full_name} - Score: {self.average_score}"