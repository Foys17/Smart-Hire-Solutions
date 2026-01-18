from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Application

@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = (
        'candidate_name', 
        'job_title', 
        'match_score_display', 
        'status', 
        'has_reference', 
        'created_at'
    )
    list_filter = ('job', 'status', 'has_reference', 'created_at')
    search_fields = (
        'candidate__full_name', 
        'candidate__email', 
        'job__title', 
        'reference_name'
    )
    

    fieldsets = (
        ('Application Info', {
            'fields': ('job', 'candidate', 'status', 'cv_file')
        }),
        ('Reference Info', {
            'fields': ('has_reference', 'reference_name')
        }),
        ('Interview Details', {
            'fields': ('interview_date',)
        }),
        ('AI Analysis (Editable)', {
            'classes': ('collapse',),
            'fields': ('match_score', 'extracted_data', 'cv_text_content', 'cv_embedding')
        }),
    )

    def candidate_name(self, obj):
        return obj.candidate.full_name
    candidate_name.short_description = 'Candidate'

    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job Applied For'

    def match_score_display(self, obj):
        return f"{obj.match_score}%"
    match_score_display.short_description = 'AI Score'