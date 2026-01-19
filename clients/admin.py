from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ClientCompany

@admin.register(ClientCompany)
class ClientCompanyAdmin(ModelAdmin):
    list_display = ('name', 'industry', 'contact_person', 'contract_status', 'created_at')
    list_filter = ('contract_status', 'industry')
    search_fields = ('name', 'email', 'contact_person')
    
    fieldsets = (
        ('Company Profile', {
            'fields': ('name', 'logo', 'industry', 'website', 'contract_status')
        }),
        ('Point of Contact', {
            'fields': ('contact_person', 'email', 'phone')
        }),
        ('Agency Terms', {
            'fields': ('default_commission',)
        }),
    )