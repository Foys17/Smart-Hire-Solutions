from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, PayrollViewSet, LeaveRequestViewSet

app_name = 'employees'

router = DefaultRouter()
router.register(r'list', EmployeeViewSet, basename='employee')
router.register(r'payroll', PayrollViewSet, basename='payroll')
router.register(r'leaves', LeaveRequestViewSet, basename='leaves')

urlpatterns = [
    path('', include(router.urls)),
]