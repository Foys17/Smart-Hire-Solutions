from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from users.models import User
from .models import Employee, Payroll, LeaveRequest

class EmployeeSerializer(serializers.ModelSerializer):
    # Fields for creating the user
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)

    # Read-only fields to return
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'email', 'password', 'full_name', 'department', 'designation', 'phone_number', 'joining_date', 'user_email', 'user_name']

    def create(self, validated_data):
        # Extract user data
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name')

        # 1. Create the User
        user = User.objects.create_user(
            email=email, 
            password=password, 
            full_name=full_name,
            role=User.Roles.EMPLOYEE
        )

        # 2. Create the Employee Profile
        employee = Employee.objects.create(user=user, **validated_data)

        # 3. Send Email
        try:
            send_mail(
                subject='Welcome to Smart Hire Solutions - Your Login Credentials',
                message=f'Hello {full_name},\n\nYour employee account has been created.\n\nLogin Details:\nEmail: {email}\nPassword: {password}\n\nPlease login and change your password immediately.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            # Log error ideally, but don't stop creation
            print(f"Failed to send email: {e}")

        return employee

class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    total_salary = serializers.ReadOnlyField()

    class Meta:
        model = Payroll
        fields = '__all__'

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['status', 'reviewed_by', 'employee']

    def create(self, validated_data):
        # Automatically assign the request to the logged-in employee
        user = self.context['request'].user
        if not hasattr(user, 'employee_profile'):
            raise serializers.ValidationError("Only employees can apply for leave.")
        validated_data['employee'] = user.employee_profile
        return super().create(validated_data)

# Serializer for HR to update leave status
class LeaveStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['status']