from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Job

@admin.register(Job)
class JobAdmin(ModelAdmin):
    # Added 'client_contact' to the columns list
    list_display = ('title', 'get_client', 'client_contact', 'status', 'salary_budget', 'commission_rate', 'created_at')
    
    # Filter by Client Contact user too
    list_filter = ('client', 'client_contact', 'status', 'created_at')
    
    search_fields = ('title', 'client__name', 'description_text', 'client_contact__email')

    fieldsets = (
        ('Client & Role', {
            # --- ACTION: Added 'client_contact' here ---
            'fields': ('client', 'client_contact', 'title', 'status')
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