from django.db import models
from django.contrib.auth.models import User
from sale.models import SaleInvoice
from django.utils import timezone


class ServiceFee(models.Model):
    sales_invoice = models.ForeignKey(
        SaleInvoice,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='service_fees',
        help_text='Optional: Associated sales invoice'
    )
    description = models.TextField(blank=True, null=True)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        if self.sales_invoice:
            return f"Service Fee for Invoice {self.sales_invoice.invoice_no}"
        return f"Standalone Service Fee {self.id}"


class Commission(models.Model):
    TRANSACTION_TYPE_CHOICES = [('credit', 'Credit'), ('debit', 'Debit'),]
    sales_invoice = models.ForeignKey(
        SaleInvoice,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='commissions',  # changed from 'service_fees'
        help_text='Optional: Associated sales invoice'
    )
    description = models.TextField(blank=True, null=True)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')
    transaction_type = models.CharField(max_length=25, choices=TRANSACTION_TYPE_CHOICES,
                                        default='debit')

    def __str__(self):
        if self.sales_invoice:
            return f"Commission Fee for Invoice {self.sales_invoice.invoice_no}"
        return f"Service Fee {self.id}"


class Tax(models.Model):
    name = models.CharField(max_length=100, default="Default Taxes")
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    corporate_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=9.00)
    custom_duty_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.name}"


class ExpenseType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return self.name


class Expense(models.Model):
    PAYMENT_TYPE_CHOICES = (('hand', 'Cash'), ('bank', 'Bank'),
                            ('check', 'Check'),)
    type = models.ForeignKey(ExpenseType, on_delete=models.CASCADE)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=250, blank=True, null=True)
    is_reminder_needed = models.BooleanField(default=False)
    reminder_date = models.DateField(blank=True, null=True)
    is_shown = models.BooleanField(default=False)
    payment_type= models.CharField(max_length=25,
                                   choices=PAYMENT_TYPE_CHOICES, default='hand')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.type.name} AED {self.amount_aed} / USD {self.amount_usd} on {self.date}"


class Wage(models.Model):
    PAYMENT_TYPE_CHOICES = (('hand', 'Cash'), ('bank', 'Bank'),
                            ('check', 'Check'),)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=250, blank=True, null=True)
    payment_type= models.CharField(max_length=25,
                                   choices=PAYMENT_TYPE_CHOICES, default='hand')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return (f"{self.id} AED {self.amount_aed} / USD {self.amount_usd} on"
                f" {self.date}")


class Asset(models.Model):
    STATUS_CHOICES = (
        ('holding', 'Holding'),
        ('sold', 'Sold'),
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='holding')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return f"{self.name} ({self.status})"
