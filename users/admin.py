from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    add_form = CustomUserCreationForm 
    form = CustomUserChangeForm
    model = User
    ordering = ['email']
    list_display = ['email', 'full_name', 'role', 'is_staff']
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'full_name')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )