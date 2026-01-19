# clients/models.py
from django.db import models

class ClientCompany(models.Model):
    class ContractStatus(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        SUSPENDED = 'Suspended', 'Suspended'
        PENDING = 'Pending', 'Pending'

    # Company Details
    name = models.CharField(max_length=255, unique=True, help_text="e.g. Google, Acme Corp")
    logo = models.ImageField(upload_to='client_logos/', blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, help_text="e.g. Fintech, Healthcare")
    website = models.URLField(blank=True)
    
    # Contact Person (The Hiring Manager at the external company)
    contact_person = models.CharField(max_length=255, help_text="Who do we send CVs to?")
    email = models.EmailField(help_text="Contact email for invoicing and updates")
    phone = models.CharField(max_length=50, blank=True)
    
    # Agency Business Logic
    contract_status = models.CharField(
        max_length=20, 
        choices=ContractStatus.choices, 
        default=ContractStatus.ACTIVE
    )
    # Default commission percentage for this client (e.g., 15%)
    default_commission = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00, 
        help_text="Default Agency Fee (%)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Client Companies"