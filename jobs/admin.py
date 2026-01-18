from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Job

@admin.register(Job)
class JobAdmin(ModelAdmin):
    # Columns shown in the list view
    list_display = ('title', 'posted_by', 'status', 'created_at', 'has_file')
    
    # Sidebar filters
    list_filter = ('status', 'created_at', 'posted_by')
    
    # Search box functionality
    search_fields = ('title', 'description_text', 'posted_by__email')
    

    # Organize the detail view nicely
    fieldsets = (
        ('Job Details', {
            'fields': ('title', 'posted_by', 'status', 'description_text', 'description_file')
        }),
        ('AI Processing (Editable)', {
            'classes': ('collapse',),
            'fields': ('processed_text', 'gliner_entities', 'jina_embedding')
        }),
    )

    def has_file(self, obj):
        return bool(obj.description_file)
    has_file.boolean = True  # Shows a nice green checkmark icon
    has_file.short_description = "Has PDF?"


    # Helper to check if AI processed the job
    def has_ai_data(self, obj):
        return bool(obj.jina_embedding)
    has_ai_data.boolean = True
    has_ai_data.short_description = "AI Processed"