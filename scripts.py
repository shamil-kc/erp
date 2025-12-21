import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()

from common.models import Expense
from banking.models import CashTransaction, CashAccount
from django.db import transaction

def create_missing_cash_transactions_for_expenses():
    cash_account = CashAccount.objects.first()
    if not cash_account:
        print("No CashAccount found. Aborting.")
        return

    expenses = Expense.objects.all()
    created_count = 0

    for expense in expenses:
        note = f"Expense #{expense.id}"
        exists = CashTransaction.objects.filter(note=note, amount=expense.amount_aed).exists()
        if exists:
            continue

        # Map payment_type to account_type
        if expense.payment_type == 'hand':
            account_type = 'cash_in_hand'
        elif expense.payment_type == 'bank':
            account_type = 'cash_in_bank'
        elif expense.payment_type == 'check':
            account_type = 'cash_in_check'
        else:
            continue  # skip unknown types

        CashTransaction.objects.create(
            cash_account=cash_account,
            transaction_type='withdraw',
            account_type=account_type,
            amount=expense.amount_aed,
            created_by=expense.created_by,
            note=note
        )
        created_count += 1

    print(f"Created {created_count} missing CashTransaction entries for Expense records.")

if __name__ == "__main__":
    with transaction.atomic():
        create_missing_cash_transactions_for_expenses()
