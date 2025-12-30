from django.db import models
from django.conf import settings

class Job(models.Model):
    STATUS_CHOICES = [('OPEN', 'Open'), ('CLOSED', 'Closed')]

    title = models.CharField(max_length=255)
    description_file = models.FileField(upload_to='job_descriptions/', null=True, blank=True)
    description_text = models.TextField(null=True, blank=True)
    
    # The text we actually used for AI processing
    processed_text = models.TextField(blank=True)
    
    # GLiNER Output: {"skills": ["Python", "Django"], "experience": ["3 years"]}
    gliner_entities = models.JSONField(default=dict, blank=True)
    
    # Jina Output: The vector representation (list of floats)
    # Storing as JSON for simplicity, but pgvector is better for production
    jina_embedding = models.JSONField(default=list, blank=True)

    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title