from django.db import models
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from products.models import ProductItem
from customer.models import Party
from inventory.models import Stock


class SaleInvoice(models.Model):
    STATUS_SALES_TEAM_PENDING = 'sales_team_pending'
    STATUS_SALES_TEAM_APPROVED = 'sales_team_approved'
    STATUS_PRODUCTION_PENDING = 'production_pending'
    STATUS_PENDING = 'pending'
    STATUS_PAYMENT_IN_PROGRESS = 'payment_in_progress'
    STATUS_APPROVED = 'approved'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RETURNED = 'returned'
    STATUS_CHOICES = [
        (STATUS_SALES_TEAM_PENDING, 'Sales Team Pending (Proforma)'),
        (STATUS_SALES_TEAM_APPROVED, 'Sales Team Approved (Proforma)'),
        (STATUS_PENDING, 'Pending'),
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
    has_tax = models.BooleanField(default=True)
    biller_name = models.CharField(max_length=100, blank=True, null=True)

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
    DELIVERY_STATUS_DELIVERED = 'delivered'
    DELIVERY_STATUS_NOT_DELIVERED = 'not_delivered'
    DELIVERY_STATUS_CHOICES = [
        (DELIVERY_STATUS_DELIVERED, 'Delivered'),
        (DELIVERY_STATUS_NOT_DELIVERED, 'Not Delivered'),
    ]

    invoice = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE, related_name='sale_items')
    item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    sale_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price_aed = models.DecimalField(max_digits=10, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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
    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default=DELIVERY_STATUS_NOT_DELIVERED
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        previous_qty = 0
        if not is_new:
            previous = SaleItem.objects.get(pk=self.pk)
            previous_qty = previous.qty

        super().save(*args, **kwargs)

        stock, _ = Stock.objects.get_or_create(product_item=self.item)
        if is_new:
            stock.quantity -= self.qty
        else:
            stock.quantity -= (self.qty - previous_qty)
        stock.save()

    def delete(self, *args, **kwargs):
        stock = Stock.objects.filter(product_item=self.item).first()
        if stock:
            stock.quantity += self.qty
            stock.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.qty}x {self.item} @ {self.sale_price_usd}"

    @property
    def total_amount_usd(self):
        return (self.sale_price_usd * self.qty) + self.shipping_usd

    @property
    def total_amount_aed(self):
        return (self.sale_price_aed * self.qty) + self.shipping_aed

class SaleReturnItem(models.Model):
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name='return_items')
    sale_invoice = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE, related_name='return_items')
    qty = models.PositiveIntegerField()
    returned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    return_date = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Update stock for the returned item
            from inventory.models import Stock
            stock, _ = Stock.objects.get_or_create(product_item=self.sale_item.item)
            stock.quantity += self.qty
            stock.save()

    def delete(self, *args, **kwargs):
        from inventory.models import Stock
        stock = Stock.objects.filter(product_item=self.sale_item.item).first()
        if stock:
            stock.quantity -= self.qty
            stock.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Return {self.qty}x {self.sale_item.item} from SaleItem {self.sale_item.id}"


class DeliveryNote(models.Model):
    DO_id = models.CharField(max_length=50, unique=True)
    sale_items = models.ManyToManyField(SaleItem, related_name='delivery_notes')
    sale_invoice = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE, related_name='delivery_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return f"Delivery Note for Invoice {self.sale_invoice.invoice_no}"

    def save(self, *args, **kwargs):
        generate_const = 'DO'
        self.DO_id = generate_const + str(self.pk)
        super().save(*args, **kwargs)