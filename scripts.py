import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()


from purchase.models import PurchaseItem
from inventory.models import Stock
from django.core.management.base import BaseCommand
from django.db import models

class Command(BaseCommand):
    help = 'Reset stock quantity to sum of all purchase item quantities for each product item (no sales considered)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Show what would be updated without making changes', )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        # Get all product_item ids from PurchaseItem
        product_item_ids = PurchaseItem.objects.values_list('item_id', flat=True).distinct()
        for product_item_id in product_item_ids:
            total_qty = PurchaseItem.objects.filter(item_id=product_item_id).aggregate(total=models.Sum('qty'))['total'] or 0
            stock, created = Stock.objects.get_or_create(product_item_id=product_item_id)
            if dry_run:
                self.stdout.write(f"[DRY RUN] Would set stock for ProductItem {product_item_id} to {total_qty}")
            else:
                stock.quantity = total_qty
                stock.save()
                self.stdout.write(f"Set stock for ProductItem {product_item_id} to {total_qty}")

if __name__ == "__main__":
    command = Command()
    command.handle(dry_run=False)