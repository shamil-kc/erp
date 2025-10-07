from django.utils import timezone
from .models import CashAccount, Transaction, UserActivity
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


def log_activity(request, action, instance, changes=None):
    def convert_decimal(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    if changes:
        changes = {k: {'old': convert_decimal(v['old']),
                       'new': convert_decimal(v['new'])} for k, v in
                   changes.items()}

    content_type = ContentType.objects.get_for_model(instance)
    UserActivity.objects.create(user=request.user, content_type=content_type,
        object_id=instance.id, action=action, changes=changes,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'))


def update_cash_account(payment_type, amount, action, user):
    account_map = {
        'cash': 'cash_in_hand',
        'bank': 'cash_in_bank',
        'check': 'check_cash'
    }
    account_type = account_map.get(payment_type)
    if not account_type:
        raise Exception(f"Unknown payment type: {payment_type}")

    account = CashAccount.objects.filter(account_type=account_type).first()
    if not account:
        raise Exception(f"CashAccount with account_type {account_type} not found")

    if action == 'deposit':
        account.balance += amount
    elif action == 'withdrawal':
        if account.balance < amount:
            raise Exception("Insufficient funds in cash account")
        account.balance -= amount
    account.save()

    Transaction.objects.create(
        account=account, amount=amount, transaction_type=action, timestamp=timezone.now()
    )
    log_activity(user, f"{action} ₹{amount} to {account_type}", account)
