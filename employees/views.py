from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Employee, Payroll, LeaveRequest
from .serializers import (
    EmployeeSerializer, PayrollSerializer, 
    LeaveRequestSerializer, LeaveStatusUpdateSerializer
)
from .permissions import IsHROrAdmin, IsEmployeeOwnerOrHRAdmin
from users.models import User

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
            return [IsHROrAdmin()]
        return [IsAuthenticated(), IsEmployeeOwnerOrHRAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Roles.HR, User.Roles.ADMIN] or user.is_superuser:
            return Employee.objects.all()
        return Employee.objects.filter(user=user)

class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
            return [IsHROrAdmin()]
        return [IsAuthenticated(), IsEmployeeOwnerOrHRAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Roles.HR, User.Roles.ADMIN] or user.is_superuser:
            return Payroll.objects.all()
        # Employee sees only their own payroll
        if hasattr(user, 'employee_profile'):
            return Payroll.objects.filter(employee=user.employee_profile)
        return Payroll.objects.none()

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Roles.HR, User.Roles.ADMIN] or user.is_superuser:
            return LeaveRequest.objects.all()
        if hasattr(user, 'employee_profile'):
            return LeaveRequest.objects.filter(employee=user.employee_profile)
        return LeaveRequest.objects.none()

    # Custom action for HR to approve/reject
    @action(detail=True, methods=['patch'], permission_classes=[IsHROrAdmin])
    def update_status(self, request, pk=None):
        leave_request = self.get_object()
        serializer = LeaveStatusUpdateSerializer(leave_request, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(reviewed_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)