from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from inventory.models import Stock
from products.models import ProductItem
from customer.models import Party
from common.models import Tax


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
    currency = models.CharField(max_length=3, default='AED')
    currency_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    vat_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_vat_usd = models.DecimalField(max_digits=13, decimal_places=2, default=0)
    vat_amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_vat_aed = models.DecimalField(max_digits=13, decimal_places=2, default=0)

    custom_duty_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    custom_duty_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    custom_duty_usd_enter = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=0)
    custom_duty_aed_enter  = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=0)


    discount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    discount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    outside_or_inside = models.CharField(
        max_length=20, choices=[('inside', 'Inside'), ('outside', 'Outside')],
        default='inside')
    has_tax = models.BooleanField(default=True)
    has_custom_duty = models.BooleanField(default=False)

    def __str__(self):
        return f"Invoice {self.invoice_no}"

    def calculate_totals(self):
        total_usd = sum([item.amount_usd for item in self.purchase_items.all()])
        total_aed = sum([item.amount_aed for item in self.purchase_items.all()])

        discounted_usd = max(total_usd - (self.discount_usd or Decimal('0')), Decimal('0'))
        discounted_aed = max(total_aed - (self.discount_aed or Decimal('0')), Decimal('0'))

        tax = Tax.objects.filter(active=True).first()
        vat_usd = discounted_usd * (tax.vat_percent / 100) if tax and self.has_tax else Decimal('0')
        vat_aed = discounted_aed * (tax.vat_percent / 100) if tax and self.has_tax else Decimal('0')

        custom_duty_usd = sum([item.custom_duty_usd_enter for item in self.purchase_items.all()])
        custom_duty_aed = sum([item.custom_duty_aed_enter for item in self.purchase_items.all()])

        # Correct calculation: total_with_vat = discounted + vat + custom duty
        self.vat_amount_usd = vat_usd
        self.vat_amount_aed = vat_aed
        self.total_with_vat_usd = discounted_usd
        self.total_with_vat_aed = discounted_aed

        PurchaseInvoice.objects.filter(pk=self.pk).update(
            vat_amount_usd=vat_usd,
            total_with_vat_usd=self.total_with_vat_usd,
            vat_amount_aed=vat_aed,
            total_with_vat_aed=self.total_with_vat_aed,
            custom_duty_usd=custom_duty_usd,
            custom_duty_aed=custom_duty_aed
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.calculate_totals()


class PurchaseItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE,
                                related_name='purchase_items', null=True, blank=True)
    item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    sold_qty = models.PositiveIntegerField(default=0)
    unit_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_aed = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_per_unit_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_per_unit_aed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    factors = models.CharField(max_length=100, blank=True, null=True)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    tax = models.ForeignKey(Tax, on_delete=models.PROTECT,
                            related_name="purchase_items" , null=True, blank=True)

    custom_duty_usd_enter = models.DecimalField(max_digits=12,
                                                decimal_places=2, default=0)
    custom_duty_aed_enter = models.DecimalField(max_digits=12,
                                                decimal_places=2, default=0)

    @property
    def remaining_qty(self):
        """Calculate remaining quantity available for sale"""
        return max(0, self.qty - self.sold_qty)

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
        is_new = self.pk is None
        previous_qty = 0

        if not is_new:
            previous = PurchaseItem.objects.get(pk=self.pk)
            previous_qty = previous.qty

        # Calculate shipping totals
        self.shipping_total_usd = self.shipping_per_unit_usd * self.qty
        self.shipping_total_aed = self.shipping_per_unit_aed * self.qty

        # Calculate amounts including shipping
        self.amount_usd = (self.unit_price_usd * self.qty)
        self.amount_aed = (self.unit_price_aed * self.qty)

        super().save(*args, **kwargs)

        # Update stock based on quantity changes
        stock, _ = Stock.objects.get_or_create(product_item=self.item)
        if is_new:
            stock.quantity += self.qty
        else:
            qty_difference = self.qty - previous_qty
            stock.quantity += qty_difference
        stock.save()

        # Recalculate invoice totals if this item belongs to an invoice
        if self.invoice:
            self.invoice.calculate_totals()

    def delete(self, *args, **kwargs):
        stock = Stock.objects.filter(product_item=self.item).first()
        if stock:
            stock.quantity -= self.qty
            stock.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.qty}x {self.item} @ {self.unit_price_usd}" if self.invoice else "Uninvoiced Purchase Item"


class PurchaseReturnItem(models.Model):
    purchase_item = models.ForeignKey('PurchaseItem', on_delete=models.CASCADE, related_name='return_items')
    purchase_invoice = models.ForeignKey('PurchaseInvoice', on_delete=models.CASCADE, related_name='return_items')
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
            stock, _ = Stock.objects.get_or_create(product_item=self.purchase_item.item)
            stock.quantity -= self.qty
            stock.save()

    def delete(self, *args, **kwargs):
        stock = Stock.objects.filter(product_item=self.purchase_item.item).first()
        if stock:
            stock.quantity += self.qty
            stock.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Return {self.qty}x {self.purchase_item.item} from PurchaseItem {self.purchase_item.id}"
