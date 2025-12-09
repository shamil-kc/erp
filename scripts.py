import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()


from purchase.models import PurchaseItem
from inventory.models import Stock
from django.core.management.base import BaseCommand
from django.db import models
from banking.models import PaymentEntry, CashAccount

def reset_main_cash_account():
    # Get the main cash account
    try:
        cash_account = CashAccount.objects.get(type='main')
    except CashAccount.DoesNotExist:
        print("Main CashAccount does not exist.")
        return

    # Calculate net amounts for each payment_type
    def net_amount(payment_type):
        sale = PaymentEntry.objects.filter(payment_type=payment_type, invoice_type='sale').aggregate(total=models.Sum('amount'))['total'] or 0
        purchase = PaymentEntry.objects.filter(payment_type=payment_type, invoice_type='purchase').aggregate(total=models.Sum('amount'))['total'] or 0
        return sale - purchase

    cash_account.cash_in_hand = net_amount('hand')
    cash_account.cash_in_bank = net_amount('bank')
    cash_account.check_cash = net_amount('check')
    cash_account.save()
    print(f"Main CashAccount reset: Cash={cash_account.cash_in_hand}, Bank={cash_account.cash_in_bank}, Check={cash_account.check_cash}")

class Command(BaseCommand):
    help = 'Reset stock quantity to sum of all purchase item quantities for each product item (no sales considered)'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        reset_main_cash_account()
        return

if __name__ == "__main__":
    command = Command()
    command.handle(dry_run=False)