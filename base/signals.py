from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PurchaseInvoice, SaleInvoice, PaymentEntry


@receiver(post_save, sender=PurchaseInvoice)
def create_purchase_payment(sender, instance, created, **kwargs):
    if created:
        PaymentEntry.objects.create(purchase_invoice=instance,
            amount_usd=instance.total_with_vat_usd,
            amount_aed=instance.total_with_vat_aed,
            payment_date=instance.purchase_date,
            created_by=instance.created_by, modified_by=instance.modified_by)


@receiver(post_save, sender=SaleInvoice)
def create_sale_payment(sender, instance, created, **kwargs):
    if created:
        PaymentEntry.objects.create(sale_invoice=instance,
            amount_usd=instance.total_with_vat_usd,
            amount_aed=instance.total_with_vat_aed,
            payment_date=instance.sale_date, created_by=instance.created_by,
            modified_by=instance.modified_by)