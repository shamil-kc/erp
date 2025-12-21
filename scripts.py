import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()

from banking.models import PaymentEntry, CashTransaction, CashAccount
from django.db import transaction

def create_missing_cash_transactions_for_payments():
    cash_account = CashAccount.objects.first()
    if not cash_account:
        print("No CashAccount found. Aborting.")
        return

    payment_entries = PaymentEntry.objects.all()
    created_count = 0

    for entry in payment_entries:
        note = f"PaymentEntry #{entry.id} ({entry.invoice_type})"
        exists = CashTransaction.objects.filter(note=note, amount=entry.amount).exists()
        if exists:
            continue

        # Determine transaction_type and account_type
        if entry.invoice_type == 'sale':
            transaction_type = 'deposit'
        elif entry.invoice_type == 'purchase':
            transaction_type = 'withdraw'
        else:
            continue

        if entry.payment_type == 'hand':
            account_type = 'cash_in_hand'
        elif entry.payment_type == 'bank':
            account_type = 'cash_in_bank'
        elif entry.payment_type == 'check':
            account_type = 'cash_in_check'
        else:
            continue

        CashTransaction.objects.create(
            cash_account=cash_account,
            transaction_type=transaction_type,
            account_type=account_type,
            amount=entry.amount,
            created_by=entry.created_by,
            note=note
        )
        created_count += 1

    print(f"Created {created_count} missing CashTransaction entries for PaymentEntry records.")

if __name__ == "__main__":
    with transaction.atomic():
        create_missing_cash_transactions_for_payments()
