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
        # Sum item amounts (already includes unit price, shipping, and custom duty per your API logic)
        total_usd = sum([item.amount_usd or Decimal('0') for item in self.purchase_items.all()])
        total_aed = sum([item.amount_aed or Decimal('0') for item in self.purchase_items.all()])

        # Apply discount
        discounted_usd = max(total_usd - (self.discount_usd or Decimal('0')), Decimal('0'))
        discounted_aed = max(total_aed - (self.discount_aed or Decimal('0')), Decimal('0'))

        # VAT calculation (on discounted total, not including custom duty)
        tax = Tax.objects.filter(active=True).first()
        print(tax, "Tax obj ")
        print(self.has_tax, "Has tax")
        if tax and tax.vat_percent and self.has_tax:
            vat_usd = sum([item.vat_amount or Decimal('0') for item in self.purchase_items.all()])
            vat_aed = sum([item.vat_amount or Decimal('0') for item in self.purchase_items.all()])
        else:
            vat_usd = Decimal('0')
            vat_aed = Decimal('0')

        # Custom duty (sum of all items' custom_duty_usd_enter * qty)
        custom_duty_usd = sum([(item.custom_duty_usd_enter or Decimal('0')) * item.qty for item in self.purchase_items.all()])
        custom_duty_aed = sum([(item.custom_duty_aed_enter or Decimal('0')) * item.qty for item in self.purchase_items.all()])

        self.vat_amount_usd = vat_usd
        self.vat_amount_aed = vat_aed
        self.custom_duty_usd = custom_duty_usd
        self.custom_duty_aed = custom_duty_aed

        # Final total = discounted + VAT + custom duty
        total_with_vat_usd = discounted_usd + vat_usd
        total_with_vat_aed = discounted_aed + vat_aed

        # Save the updated totals to the DB
        PurchaseInvoice.objects.filter(pk=self.pk).update(
            vat_amount_usd=self.vat_amount_usd,
            total_with_vat_usd=total_with_vat_usd,
            vat_amount_aed=self.vat_amount_aed,
            total_with_vat_aed=total_with_vat_aed,
            custom_duty_usd=self.custom_duty_usd,
            custom_duty_aed=self.custom_duty_aed
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Restock inventory for each purchase item before deleting
        for purchase_item in self.purchase_items.all():
            # Restock: add back the qty to stock
            stock = Stock.objects.filter(product_item=purchase_item.item).first()
            if stock:
                stock.quantity -= purchase_item.qty
                stock.save()
            # Optionally, handle related sale items if you want to update them

        self.purchase_items.all().delete()
        super().delete(*args, **kwargs)


class PurchaseItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE,
                                related_name='purchase_items', null=True, blank=True)
    item = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField()
    sold_qty = models.PositiveIntegerField(default=0)

    # pricing details
    unit_price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_aed = models.DecimalField(max_digits=10, decimal_places=2)
    total_price_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # shipping details
    shipping_per_unit_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_per_unit_aed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # custom duty details
    custom_duty_usd_enter = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    custom_duty_aed_enter = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    custom_duty_usd_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    custom_duty_aed_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # vat details
    vat_per_unit_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_per_unit_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_total_aed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

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



    @property
    def remaining_qty(self):
        """Calculate remaining quantity available for sale"""
        return max(0, self.qty - self.sold_qty)

    @property
    def vat_amount_usd(self):
        """Calculate VAT in USD based on amount_usd and tax percent."""
        vat_rate = self.tax.vat_percent if self.tax is not None else 0
        return (self.amount_usd or Decimal('0')) * (vat_rate / 100)

    @property
    def vat_amount_aed(self):
        """Calculate VAT in AED based on amount_aed and tax percent."""
        vat_rate = self.tax.vat_percent if self.tax is not None else 0
        return (self.amount_aed or Decimal('0')) * (vat_rate / 100)

    def calculate_totals(self):
        # Calculate total prices
        self.total_price_usd = (self.unit_price_usd or Decimal('0')) * self.qty
        self.total_price_aed = (self.unit_price_aed or Decimal('0')) * self.qty

        # Calculate shipping totals
        self.shipping_total_usd = (self.shipping_per_unit_usd or Decimal('0')) * self.qty
        self.shipping_total_aed = (self.shipping_per_unit_aed or Decimal('0')) * self.qty

        # Calculate custom duty totals
        self.custom_duty_usd_total = (self.custom_duty_usd_enter or Decimal('0')) * self.qty
        self.custom_duty_aed_total = (self.custom_duty_aed_enter or Decimal('0')) * self.qty

        # Calculate VAT per unit
        vat_rate = self.tax.vat_percent if self.tax else Decimal('0')
        base_usd = self.total_price_usd + self.shipping_total_usd + self.custom_duty_usd_total
        base_aed = self.total_price_aed + self.shipping_total_aed + self.custom_duty_aed_total

        self.vat_per_unit_usd = ((self.unit_price_usd or Decimal('0')) + (self.shipping_per_unit_usd or Decimal('0')) + (self.custom_duty_usd_enter or Decimal('0'))) * (vat_rate / 100)
        self.vat_per_unit_aed = ((self.unit_price_aed or Decimal('0')) + (self.shipping_per_unit_aed or Decimal('0')) + (self.custom_duty_aed_enter or Decimal('0'))) * (vat_rate / 100)

        self.vat_total_usd = self.vat_per_unit_usd * self.qty
        self.vat_total_aed = self.vat_per_unit_aed * self.qty


    def save(self, *args, **kwargs):
        self.calculate_totals()
        is_new = self.pk is None
        previous_qty = 0

        if not is_new:
            previous = PurchaseItem.objects.get(pk=self.pk)
            previous_qty = previous.qty

        super().save(*args, **kwargs)

        # Update stock based on quantity changes
        stock, _ = Stock.objects.get_or_create(product_item=self.item)
        if is_new:
            stock.quantity += self.qty
        else:
            qty_difference = self.qty - previous_qty
            stock.quantity += qty_difference
        stock.save()

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
