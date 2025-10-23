from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction


class Product(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return self.name

class ProductType(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    type_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.product.name} - {self.type_name}"

class ProductGrade(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    grade = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.product_type} - {self.grade}"

class ProductItem(models.Model):
    grade = models.ForeignKey(ProductGrade, on_delete=models.CASCADE)
    size = models.FloatField()
    unit = models.CharField(max_length=20, default='PCs')
    weight_kg_each = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.grade} - Size {self.size}"

class Party(models.Model):
    TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.type})"

class PurchaseInvoice(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_APPROVED = 'approved'
    STATUS_CANCELLED = 'cancelled'
    STATUS_Returned = 'returned'
    STATUS_CHOICES = [(STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'Payment In Progress'),
        (STATUS_APPROVED, 'Approved'),(STATUS_CANCELLED, 'Cancelled'),
                      (STATUS_Returned, 'Returned')]

    invoice_no = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_PENDING)
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_invoices')
    purchase_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')
    notes = models.TextField(blank=True, null=True)

    vat_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_vat_usd = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    vat_amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_vat_aed = models.DecimalField(max_digits=13, decimal_places=2, default=0)

    discount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    discount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    outside_or_inside = models.CharField(
        max_length=20, choices=[('inside', 'Inside'), ('outside', 'Outside')],
        default='inside')
    has_tax = models.BooleanField(default=True)  # Add this field

    def __str__(self):
        return f"Invoice {self.invoice_no}"

    def calculate_totals(self):
        total_usd = sum([item.amount_usd for item in self.purchase_items.all()])
        total_aed = sum([item.amount_aed for item in self.purchase_items.all()])
        # Subtract discount (not below zero)
        discounted_usd = max(total_usd - (self.discount_usd or Decimal('0')), Decimal('0'))
        discounted_aed = max(total_aed - (self.discount_aed or Decimal('0')), Decimal('0'))
        tax = Tax.objects.filter(active=True).first()
        vat_usd = discounted_usd * (tax.vat_percent / 100) if tax and self.has_tax else Decimal('0')
        vat_aed = discounted_aed * (tax.vat_percent / 100) if tax and self.has_tax else Decimal('0')
        self.vat_amount_usd = vat_usd
        self.total_with_vat_usd = discounted_usd + vat_usd
        self.vat_amount_aed = vat_aed
        self.total_with_vat_aed = discounted_aed + vat_aed
        PurchaseInvoice.objects.filter(pk=self.pk).update(
            vat_amount_usd=vat_usd,
            total_with_vat_usd=discounted_usd + vat_usd,
            vat_amount_aed=vat_aed,
            total_with_vat_aed=discounted_aed + vat_aed
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.calculate_totals()


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

class PurchaseItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='purchase_items')
    item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    unit_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_aed = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_per_unit_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_per_unit_aed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    factors = models.CharField(max_length=100, blank=True, null=True)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    tax = models.ForeignKey(Tax, on_delete=models.PROTECT,
                            related_name="purchase_items")

    @property
    def vat_amount_usd(self):
        # Use the related Tax instance to access the VAT percent
        vat_rate = self.tax.vat_percent if self.tax is not None else 0
        total_price = self.unit_price_usd * self.qty
        return total_price * (vat_rate / 100)

    @property
    def vat_amount_aed(self):
        vat_rate = self.tax.vat_percent if self.tax is not None else 0
        total_price = self.unit_price_aed * self.qty
        return total_price * (vat_rate / 100)

    def save(self, *args, **kwargs):
        self.amount_usd = (self.unit_price_usd + self.shipping_per_unit_usd) * self.qty
        self.amount_aed = (self.unit_price_aed + self.shipping_per_unit_aed) * self.qty
        super().save(*args, **kwargs)
        # Update stock
        stock, created = Stock.objects.get_or_create(product_item=self.item)
        stock.quantity += self.qty
        stock.save()

    def __str__(self):
        return f"{self.qty}x {self.item} @ {self.unit_price_usd}"


class SaleInvoice(models.Model):
    STATUS_SALES_TEAM_PENDING = 'sales_team_pending'
    STATUS_SALES_TEAM_APPROVED = 'sales_team_approved'
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_APPROVED = 'approved'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RETURNED = 'returned'
    STATUS_CHOICES = [
        (STATUS_SALES_TEAM_PENDING, 'Sales Team Pending (Proforma)'),
        (STATUS_SALES_TEAM_APPROVED, 'Sales Team Approved (Proforma)'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'Payment In Progress'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_RETURNED, 'Returned'),
    ]

    invoice_no = models.CharField(max_length=50, unique=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES,
                              default=STATUS_SALES_TEAM_PENDING)
    is_sales_approved = models.BooleanField(default=False)
    sale_date = models.DateField(default=timezone.now)
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True, related_name='sale_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    vat_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_vat_usd = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    vat_amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_vat_aed = models.DecimalField(max_digits=13, decimal_places=2, default=0)

    # Add these fields -- default to zero
    discount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    outside_or_inside = models.CharField(
        max_length=20, choices=[('inside', 'Inside'), ('outside', 'Outside')],
        default='inside')
    has_tax = models.BooleanField(default=True)  # Add this field

    def calculate_totals(self):
        total_usd = sum(item.amount_usd for item in self.sale_items.all())
        total_aed = sum(item.amount_aed for item in self.sale_items.all())

        # Sum service fee amounts if any
        service_fee_usd = sum(
            fee.amount_usd for fee in self.service_fees.all())
        service_fee_aed = sum(
            fee.amount_aed for fee in self.service_fees.all())

        # Total before discount includes service fees
        total_usd += service_fee_usd
        total_aed += service_fee_aed

        # Subtract discount, never below zero
        discounted_usd = max(total_usd - (self.discount_usd or Decimal('0')),
                             Decimal('0'))
        discounted_aed = max(total_aed - (self.discount_aed or Decimal('0')),
                             Decimal('0'))

        tax = Tax.objects.filter(active=True).first()
        vat_usd = discounted_usd * (tax.vat_percent / 100) if tax and self.has_tax else Decimal('0')
        vat_aed = discounted_aed * (tax.vat_percent / 100) if tax and self.has_tax else Decimal('0')

        self.vat_amount_usd = vat_usd
        self.total_with_vat_usd = discounted_usd + vat_usd
        self.vat_amount_aed = vat_aed
        self.total_with_vat_aed = discounted_aed + vat_aed

        SaleInvoice.objects.filter(pk=self.pk).update(vat_amount_usd=vat_usd,
            total_with_vat_usd=self.total_with_vat_usd, vat_amount_aed=vat_aed,
            total_with_vat_aed=self.total_with_vat_aed)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.calculate_totals()

    def __str__(self):
        return f"Invoice {self.invoice_no}"


class SaleItem(models.Model):
    invoice = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE, related_name='sale_items')
    item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    sale_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price_aed = models.DecimalField(max_digits=10, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2,
                                     default=0)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    shipping_usd = models.DecimalField(max_digits=12, decimal_places=2,
                                       default=0)
    shipping_aed = models.DecimalField(max_digits=12, decimal_places=2,
                                       default=0)

    # Mapping to identify which purchase this sale item comes from
    purchase_item = models.ForeignKey(
        'PurchaseItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_items',
        help_text='The purchase item this sale item is sourced from'
    )

    def save(self, *args, **kwargs):
        self.amount_usd = self.qty * self.sale_price_usd
        self.amount_aed = self.qty * self.sale_price_aed
        super().save(*args, **kwargs)
        # Reduce stock
        stock, created = Stock.objects.get_or_create(product_item=self.item)
        stock.quantity -= self.qty
        stock.save()

    def __str__(self):
        return f"{self.qty}x {self.item} @ {self.sale_price_usd}"

    @property
    def total_amount_usd(self):
        return (self.sale_price_usd * self.qty) + self.shipping_usd

    @property
    def total_amount_aed(self):
        return (self.sale_price_aed * self.qty) + self.shipping_aed



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
    PAYMENT_TYPE_CHOICES = (('hand', 'Cash'), ('bank', 'Bank'),
                            ('check', 'Check'),)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=25, choices=[
        ('salary', 'Salary'),
        ('bonus', 'Bonus'),
        ('reimbursement', 'Reimbursement')
    ])
    payment_type = models.CharField(max_length=25,
                                    choices=PAYMENT_TYPE_CHOICES,
                                    default='hand')
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


class PaymentEntry(models.Model):
    PAYMENT_TYPE_CHOICES = (('hand', 'Cash'), ('bank', 'Bank'),
                            ('check', 'Check'),)

    invoice_type = models.CharField(max_length=10,
        choices=(('sale', 'Sale'), ('purchase', 'Purchase')),
        help_text='Type of invoice this payment belongs to')

    invoice_id = models.PositiveIntegerField(
        help_text='ID of related Sale or Purchase invoice')

    payment_type = models.CharField(max_length=10,
                                    choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                   null=True)

    class Meta:
        verbose_name_plural = "Payment Entries"

    def __str__(self):
        return f"{self.payment_type} payment of {self.amount} for {self.invoice_type} invoice #{self.invoice_id}"



class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey('contenttypes.ContentType',
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=[('create', 'Created'),
        ('update', 'Updated'), ('delete', 'Deleted')])
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} {self.action} {self.content_type} at {self.timestamp}"


class CashAccount(models.Model):
    # Only one row should exist for the company
    cash_in_hand = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cash_in_bank = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    check_cash = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    type = models.CharField(
        max_length=20, choices=(('main', 'Main'), ('profit', 'Profit')),
        default='main', unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    def deposit(self, amount, account_type):
        if account_type == 'cash_in_hand':
            self.cash_in_hand += amount
        elif account_type == 'cash_in_bank':
            self.cash_in_bank += amount
        elif account_type == 'cash_in_cash':
            self.check_cash += amount
        else:
            raise ValueError("Invalid account type")
        self.save()

    def withdraw(self, amount, account_type):
        if account_type == 'cash_in_hand':
            if amount > self.cash_in_hand:
                raise ValueError("Insufficient funds in cash in hand!")
            self.cash_in_hand -= amount
        elif account_type == 'cash_in_bank':
            if amount > self.cash_in_bank:
                raise ValueError("Insufficient funds in cash in bank!")
            self.cash_in_bank -= amount
        elif account_type == 'check_cash':
            if amount > self.check_cash:
                raise ValueError("Insufficient funds in check cash!")
            self.check_cash -= amount
        else:
            raise ValueError("Invalid account type")
        self.save()

    def transfer(self, from_type, to_type, amount):
        if from_type == to_type:
            raise ValueError("Cannot transfer to the same account type!")
        self.withdraw(amount, from_type)
        self.deposit(amount, to_type)

    def __str__(self):
        return f"CashAccount — Cash: ₹{self.cash_in_hand}, Bank: ₹{self.cash_in_bank}, Check: ₹{self.check_cash}"


class Stock(models.Model):
    product_item = models.OneToOneField(ProductItem, on_delete=models.CASCADE, related_name='stock')
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stock for {self.product_item}: {self.quantity}"

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