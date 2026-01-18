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
    list_display = ['email', 'full_name', 'role', 'is_staff', 'is_active']
    list_filter = ('role', 'is_staff', 'is_active', 'groups')
    search_fields = ('email', 'full_name')
    
    # Layout for "Edit User"
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Layout for "Add User" (Must match forms.py fields exactly!)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )