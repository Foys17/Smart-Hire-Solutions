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
        'created_at'
    )
    list_filter = ('status', 'job__client', 'created_at') 
    search_fields = ('candidate__full_name', 'candidate__email', 'job__title')
    
    fieldsets = (
        ('Application Info', {
            'fields': ('job', 'candidate', 'status', 'cv_file')
        }),
        ('AI Analysis', {
            'classes': ('collapse',),
            'fields': ('match_score', 'extracted_data', 'cv_text_content')
        }),
    )

    def candidate_name(self, obj):
        return obj.candidate.full_name
    candidate_name.short_description = 'Candidate'

    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Role'

    def match_score_display(self, obj):
        return f"{obj.match_score}%"
    match_score_display.short_description = 'AI Score'