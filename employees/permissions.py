from rest_framework import permissions
from users.models import User

class IsHROrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in [User.Roles.HR, User.Roles.ADMIN] or request.user.is_superuser
        )

class IsEmployeeOwnerOrHRAdmin(permissions.BasePermission):
    """
    Allows Employees to see only their own records.
    HR/Admin can see all.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in [User.Roles.HR, User.Roles.ADMIN] or user.is_superuser:
            return True
        
        # Check if the object belongs to the employee
        if hasattr(obj, 'user'): # For Employee model
            return obj.user == user
        if hasattr(obj, 'employee'): # For Payroll/Leave models
            return obj.employee.user == user
            
        return False