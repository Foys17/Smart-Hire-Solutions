from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Employee, Payroll, LeaveRequest

@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ('get_full_name', 'department', 'designation', 'phone_number', 'joining_date')
    search_fields = ('user__email', 'user__full_name', 'department')
    list_filter = ('department', 'designation')

    fieldsets = (
        ('Employee Details', {
            'fields': ('user', 'department', 'designation', 'phone_number')
        }),
    )

    def get_full_name(self, obj):
        return obj.user.full_name
    get_full_name.short_description = 'Name'

@admin.register(Payroll)
class PayrollAdmin(ModelAdmin):
    list_display = ('get_employee', 'month', 'basic_salary', 'total_salary_display', 'is_paid')
    list_filter = ('is_paid', 'month')
    search_fields = ('employee__user__email', 'employee__user__full_name')
    list_editable = ('is_paid',)

    fieldsets = (
        ('Payroll Info', {
            'fields': ('employee', 'month', 'is_paid')
        }),
        ('Salary Breakdown', {
            'fields': ('basic_salary', 'bonuses', 'deductions')
        }),
    )

    def get_employee(self, obj):
        return obj.employee.user.full_name
    get_employee.short_description = 'Employee'

    def total_salary_display(self, obj):
        return f"${obj.total_salary}"
    total_salary_display.short_description = 'Total Payout'

@admin.register(LeaveRequest)
class LeaveRequestAdmin(ModelAdmin):
    list_display = ('get_employee', 'leave_type', 'start_date', 'end_date', 'status', 'reviewed_by')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('employee__user__full_name',)
    actions = ['approve_leave', 'reject_leave']

    fieldsets = (
        ('Request Details', {
            'fields': ('employee', 'leave_type', 'reason')
        }),
        ('Duration', {
            'fields': ('start_date', 'end_date')
        }),
        ('Approval Status', {
            'fields': ('status', 'reviewed_by')
        }),
    )

    def get_employee(self, obj):
        return obj.employee.user.full_name
    get_employee.short_description = 'Employee'

    @admin.action(description='Approve selected leave requests')
    def approve_leave(self, request, queryset):
        queryset.update(status='Approved', reviewed_by=request.user)

    @admin.action(description='Reject selected leave requests')
    def reject_leave(self, request, queryset):
        queryset.update(status='Rejected', reviewed_by=request.user)