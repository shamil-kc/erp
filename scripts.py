import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()

from common.models import Expense
from banking.models import CashTransaction, CashAccount, PaymentEntry
from django.db import transaction


def update_cleared_sale_purchase_checks_in_main_cash_account():
    main_account = CashAccount.objects.first()
    if not main_account:
        print("No CashAccount found. Aborting.")
        return

    # Cleared sale checks: add to cash_in_bank
    cleared_sale_checks = PaymentEntry.objects.filter(
        invoice_type='sale',
        payment_type='check',
        is_cheque_cleared=True
    )
    sale_total = sum(entry.amount for entry in cleared_sale_checks)

    # Cleared purchase checks: subtract from cash_in_bank
    cleared_purchase_checks = PaymentEntry.objects.filter(
        invoice_type='purchase',
        payment_type='check',
        is_cheque_cleared=True
    )
    purchase_total = sum(entry.amount for entry in cleared_purchase_checks)

    main_account.cash_in_bank += sale_total
    main_account.cash_in_bank -= purchase_total
    main_account.save()

    print(f"Updated main account cash_in_bank: +{sale_total} (sale checks), -{purchase_total} (purchase checks)")


if __name__ == "__main__":
    with transaction.atomic():
        update_cleared_sale_purchase_checks_in_main_cash_account()
