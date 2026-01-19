from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Job

@admin.register(Job)
class JobAdmin(ModelAdmin):
    list_display = ('title', 'get_client', 'status', 'salary_budget', 'commission_rate', 'created_at')
    
    # Filter by Client to see "All Jobs for Google"
    list_filter = ('client', 'status', 'created_at')
    
    search_fields = ('title', 'client__name', 'description_text')

    fieldsets = (
        ('Client & Role', {
            'fields': ('client', 'title', 'status')
        }),
        ('Job Description', {
            'fields': ('description_text', 'description_file')
        }),
        ('Financials (Internal Only)', {
            'classes': ('collapse',),
            'fields': ('salary_budget', 'commission_rate')
        }),
        ('AI Processing', {
            'classes': ('collapse',),
            'fields': ('processed_text', 'gliner_entities', 'jina_embedding')
        }),
    )

    def get_client(self, obj):
        return obj.client.name if obj.client else "Internal"
    get_client.short_description = 'Client Company'

    def has_file(self, obj):
        return bool(obj.description_file)
    has_file.boolean = True
    has_file.short_description = "Has PDF?"


    # Helper to check if AI processed the job
    def has_ai_data(self, obj):
        return bool(obj.jina_embedding)
    has_ai_data.boolean = True
    has_ai_data.short_description = "AI Processed"