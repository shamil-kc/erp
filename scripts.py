import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shiperp.settings")
django.setup()

from decimal import Decimal
from banking.models import CashAccount, PaymentEntry, CashAccountTransfer
from common.models import Expense, ServiceFee
from employee.models import SalaryEntry


def reset_cash_account_balance():
    # Only one main cash account is assumed
    cash_account = CashAccount.objects.first()
    if not cash_account:
        print("No CashAccount found.")
        return

    # Reset all balances
    cash_account.cash_in_hand = Decimal('0')
    cash_account.cash_in_bank = Decimal('0')
    cash_account.check_cash = Decimal('0')

    # 1. PaymentEntry
    for pe in PaymentEntry.objects.all():
        if pe.payment_type == 'hand':
            cash_account.cash_in_hand += pe.amount
        elif pe.payment_type == 'bank':
            cash_account.cash_in_bank += pe.amount
        elif pe.payment_type == 'check':
            cash_account.check_cash += pe.amount

    # 2. CashAccountTransfer
    for transfer in CashAccountTransfer.objects.all():
        # Withdraw from from_type
        if transfer.from_type == 'cash_in_hand':
            cash_account.cash_in_hand -= transfer.amount
        elif transfer.from_type == 'cash_in_bank':
            cash_account.cash_in_bank -= transfer.amount
        elif transfer.from_type == 'cash_in_check':
            cash_account.check_cash -= transfer.amount
        # Deposit to to_type
        if transfer.to_type == 'cash_in_hand':
            cash_account.cash_in_hand += transfer.amount
        elif transfer.to_type == 'cash_in_bank':
            cash_account.cash_in_bank += transfer.amount
        elif transfer.to_type == 'cash_in_check':
            cash_account.check_cash += transfer.amount

    # 3. Expense
    for expense in Expense.objects.all():
        if expense.payment_type == 'hand':
            cash_account.cash_in_hand -= expense.amount_aed
        elif expense.payment_type == 'bank':
            cash_account.cash_in_bank -= expense.amount_aed
        elif expense.payment_type == 'check':
            cash_account.check_cash -= expense.amount_aed

    # 4. ServiceFee (assuming ServiceFee is a deposit)
    for fee in ServiceFee.objects.all():
        cash_account.cash_in_hand += fee.amount_aed

    # 5. SalaryEntry
    for salary in SalaryEntry.objects.all():
        if salary.payment_type == 'hand':
            cash_account.cash_in_hand -= salary.amount_aed
        elif salary.payment_type == 'bank':
            cash_account.cash_in_bank -= salary.amount_aed
        elif salary.payment_type == 'check':
            cash_account.check_cash -= salary.amount_aed

    cash_account.save()
    print("CashAccount balances reset:")
    print(f"  cash_in_hand: {cash_account.cash_in_hand}")
    print(f"  cash_in_bank: {cash_account.cash_in_bank}")
    print(f"  check_cash: {cash_account.check_cash}")


if __name__ == "__main__":
    reset_cash_account_balance()
