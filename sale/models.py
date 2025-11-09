from django.db import models
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from products.models import ProductItem
from customer.models import Party


class SaleInvoice(models.Model):
    STATUS_SALES_TEAM_PENDING = 'sales_team_pending'
    STATUS_SALES_TEAM_APPROVED = 'sales_team_approved'
    STATUS_PRODUCTION_PENDING = 'production_pending'
    STATUS_PAYMENT_PENDING = 'payment_pending'
    STATUS_PAYMENT_IN_PROGRESS = 'payment_in_progress'
    STATUS_APPROVED = 'approved'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RETURNED = 'returned'
    STATUS_CHOICES = [
        (STATUS_SALES_TEAM_PENDING, 'Sales Team Pending (Proforma)'),
        (STATUS_SALES_TEAM_APPROVED, 'Sales Team Approved (Proforma)'),
        (STATUS_PAYMENT_PENDING, 'Payment Pending'),
        (STATUS_PAYMENT_IN_PROGRESS, 'Payment In Progress'),
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
        from common.models import Tax
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
        'purchase.PurchaseItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_items',
        help_text='The purchase item this sale item is sourced from'
    )

    def save(self, *args, **kwargs):
        # Track old quantity and purchase item for updates
        old_qty = 0
        old_purchase_item = None

        if self.pk:  # If updating an existing SaleItem
            try:
                old_instance = SaleItem.objects.get(pk=self.pk)
                old_qty = old_instance.qty
                old_purchase_item = old_instance.purchase_item
            except SaleItem.DoesNotExist:
                pass

        # Calculate amounts
        self.amount_usd = self.qty * self.sale_price_usd
        self.amount_aed = self.qty * self.sale_price_aed
        super().save(*args, **kwargs)

        # Update sold_qty for the associated PurchaseItem
        with db_transaction.atomic():
            # If the purchase item has changed, adjust the old and new items
            if old_purchase_item and old_purchase_item != self.purchase_item:
                old_purchase_item.sold_qty -= old_qty
                old_purchase_item.save()

            if self.purchase_item:
                qty_difference = self.qty - old_qty
                self.purchase_item.sold_qty += qty_difference
                self.purchase_item.save()

    def delete(self, *args, **kwargs):
        # Decrease sold_qty when a SaleItem is deleted
        if self.purchase_item:
            with db_transaction.atomic():
                self.purchase_item.sold_qty -= self.qty
                self.purchase_item.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.qty}x {self.item} @ {self.sale_price_usd}"

    @property
    def total_amount_usd(self):
        return (self.sale_price_usd * self.qty) + self.shipping_usd

    @property
    def total_amount_aed(self):
        return (self.sale_price_aed * self.qty) + self.shipping_aed

