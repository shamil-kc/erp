import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()

from common.models import Expense
from banking.models import CashTransaction, CashAccount
from django.db import transaction


def reset_cash_account_amounts():
    main_account = CashAccount.objects.first()
    if not main_account:
        print("No CashAccount found. Aborting.")
        return

    account_types = ['cash_in_hand', 'cash_in_bank', 'cash_in_check']
    totals = {atype: 0 for atype in account_types}

    transactions = CashTransaction.objects.filter(cash_account=main_account)
    for tx in transactions:
        sign = 1 if tx.transaction_type == 'deposit' else -1
        if tx.account_type in totals:
            totals[tx.account_type] += sign * tx.amount

    main_account.cash_in_hand = totals['cash_in_hand']
    main_account.cash_in_bank = totals['cash_in_bank']
    main_account.cash_in_check = totals['cash_in_check']
    main_account.save()
    print("Main CashAccount amounts have been reset based on CashTransaction records.")


if __name__ == "__main__":
    reset_cash_account_amounts()
