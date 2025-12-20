from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Designation(models.Model):
    title = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return self.title


class Account(models.Model):
    name = models.CharField(max_length=100, unique=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL,
                                    null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return self.name


class SalaryEntry(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=25, choices=[
        ('salary', 'Salary'),
        ('bonus', 'Bonus'),
        ('reimbursement', 'Reimbursement')
    ])
    date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.account.name} {self.entry_type}: AED {self.amount_aed}, USD {self.amount_usd}"


class SalaryPayment(models.Model):
    PAYMENT_TYPE_CHOICES = (('hand', 'Cash'), ('bank', 'Bank'), ('check', 'Check'),)
    salary_entry = models.ForeignKey(SalaryEntry, on_delete=models.CASCADE, related_name='payments')
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=25, choices=PAYMENT_TYPE_CHOICES, default='hand')
    date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return f"Payment for {self.salary_entry} - AED {self.amount_aed} ({self.payment_type})"


class EmployeeLeave(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('annual', 'Annual'),
        ('sick', 'Sick'),
        ('unpaid', 'Unpaid'),
        ('other', 'Other'),
    ]
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return f"{self.account.name} - {self.leave_type} ({self.start_date} to {self.end_date})"
