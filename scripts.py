import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()


from purchase.models import PurchaseItem, PurchaseInvoice
from django.db import transaction
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Update shipping_total_usd and shipping_total_aed fields for all existing PurchaseItem records'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Show what would be updated without making changes', )

    def handle(self, *args, **options):
        # dry_run = options['dry_run']
        #
        # if dry_run:
        #     self.stdout.write(
        #         self.style.WARNING('DRY RUN MODE - No changes will be made'))
        #
        # # Get all PurchaseItem records
        # purchase_items = PurchaseItem.objects.all()
        # total_items = purchase_items.count()
        #
        # self.stdout.write(
        #     f'Found {total_items} PurchaseItem records to update')
        #
        # updated_count = 0
        # invoice_ids_to_recalculate = set()
        #
        # with transaction.atomic():
        #     for item in purchase_items:
        #         # Calculate shipping totals
        #         old_shipping_total_usd = item.shipping_total_usd
        #         old_shipping_total_aed = item.shipping_total_aed
        #
        #         new_shipping_total_usd = item.shipping_per_unit_usd * item.qty
        #         new_shipping_total_aed = item.shipping_per_unit_aed * item.qty
        #
        #         # Check if update is needed
        #         if (
        #                 old_shipping_total_usd != new_shipping_total_usd or old_shipping_total_aed != new_shipping_total_aed):
        #
        #             if not dry_run:
        #                 # Update the fields
        #                 item.shipping_total_usd = new_shipping_total_usd
        #                 item.shipping_total_aed = new_shipping_total_aed
        #
        #                 # Recalculate amount including shipping
        #                 item.amount_usd = (
        #                                               item.unit_price_usd * item.qty) + new_shipping_total_usd
        #                 item.amount_aed = (
        #                                               item.unit_price_aed * item.qty) + new_shipping_total_aed
        #
        #                 item.save(update_fields=['shipping_total_usd',
        #                                          'shipping_total_aed',
        #                                          'amount_usd', 'amount_aed'])
        #
        #                 # Track invoice for recalculation
        #                 if item.invoice:
        #                     invoice_ids_to_recalculate.add(item.invoice.id)
        #
        #             updated_count += 1
        #
        #             self.stdout.write(f'Item ID {item.id}: '
        #                               f'USD {old_shipping_total_usd} -> {new_shipping_total_usd}, '
        #                               f'AED {old_shipping_total_aed} -> {new_shipping_total_aed}')
        #
        #     # Recalculate invoice totals for affected invoices
        #     if not dry_run and invoice_ids_to_recalculate:
        #         self.stdout.write(
        #             f'Recalculating totals for {len(invoice_ids_to_recalculate)} invoices...')
        #
        #         for invoice_id in invoice_ids_to_recalculate:
        #             try:
        #                 invoice = PurchaseInvoice.objects.get(id=invoice_id)
        #                 invoice.calculate_totals()
        #                 self.stdout.write(
        #                     f'Updated invoice {invoice.invoice_no}')
        #             except PurchaseInvoice.DoesNotExist:
        #                 self.stdout.write(self.style.WARNING(
        #                     f'Invoice with ID {invoice_id} not found'))
        #
        # if dry_run:
        #     self.stdout.write(self.style.SUCCESS(
        #         f'DRY RUN COMPLETE: {updated_count} items would be updated'))
        # else:
        #     self.stdout.write(self.style.SUCCESS(
        #         f'Successfully updated {updated_count} PurchaseItem records and recalculated {len(invoice_ids_to_recalculate)} invoice totals'))
        print("12234455")


if __name__ == "__main__":
    command = Command()
    command.handle(dry_run=False)