from django.db.models import Sum, Q, Count
from decimal import Decimal
from .models import Asset, Expense, ServiceFee, Commission, ExpenseType


def get_current_assets_by_status(start_date, end_date, status=None):
    """
    Get assets within a date range, optionally filtered by status.

    Args:
        start_date: Start date for filtering
        end_date: End date for filtering
        status: 'holding', 'sold', or None for both

    Returns:
        QuerySet: Assets within the date range
    """
    queryset = Asset.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )

    if status:
        queryset = queryset.filter(status=status)

    return queryset.select_related('created_by', 'modified_by')


def get_assets_summary_by_status(start_date, end_date):
    """
    Get summary of assets by status within a date range.

    Args:
        start_date: Start date for filtering
        end_date: End date for filtering

    Returns:
        dict: Summary with holding and sold asset totals
    """
    base_queryset = Asset.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )

    holding_assets = base_queryset.filter(status='holding').aggregate(
        total_value=Sum('price'),
        total_quantity=Sum('quantity')
    )

    sold_assets = base_queryset.filter(status='sold').aggregate(
        total_value=Sum('price'),
        total_quantity=Sum('quantity')
    )

    return {
        'holding': {
            'total_value': holding_assets['total_value'] or Decimal('0'),
            'total_quantity': holding_assets['total_quantity'] or 0,
            'assets': base_queryset.filter(status='holding')
        },
        'sold': {
            'total_value': sold_assets['total_value'] or Decimal('0'),
            'total_quantity': sold_assets['total_quantity'] or 0,
            'assets': base_queryset.filter(status='sold')
        }
    }


def get_expenses_by_type(start_date, end_date, currency='aed'):
    """
    Get expenses grouped by expense type within a date range.

    Args:
        start_date: Start date for filtering
        end_date: End date for filtering
        currency: 'aed' or 'usd'

    Returns:
        QuerySet: Expense types with aggregated amounts
    """
    currency_field = f'amount_{currency.lower()}'

    return ExpenseType.objects.filter(
        expense__date__gte=start_date,
        expense__date__lte=end_date
    ).annotate(
        total_amount=Sum(f'expense__{currency_field}'),
        expense_count=Count('expense')
    ).filter(total_amount__gt=0).order_by('-total_amount')


def get_service_fees_in_range(start_date, end_date, currency='usd'):
    """
    Get service fees within a specific date range.

    Args:
        start_date: Start date for filtering
        end_date: End date for filtering
        currency: 'usd' or 'aed'

    Returns:
        dict: Service fees data with total and queryset
    """
    currency_field = f'amount_{currency.lower()}'

    queryset = ServiceFee.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('sales_invoice', 'created_by')

    total_amount = queryset.aggregate(
        total=Sum(currency_field)
    )['total'] or Decimal('0')

    return {
        'service_fees': queryset,
        'total_amount': total_amount,
        'count': queryset.count(),
        'currency': currency.upper()
    }


def get_commissions_in_range(start_date, end_date, currency='usd', transaction_type=None):
    """
    Get commissions within a specific date range.

    Args:
        start_date: Start date for filtering
        end_date: End date for filtering
        currency: 'usd' or 'aed'
        transaction_type: 'credit', 'debit', or None for both

    Returns:
        dict: Commission data with totals and queryset
    """
    currency_field = f'amount_{currency.lower()}'

    queryset = Commission.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('sales_invoice', 'created_by')

    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)

    # Get totals by transaction type
    credit_total = queryset.filter(transaction_type='credit').aggregate(
        total=Sum(currency_field)
    )['total'] or Decimal('0')

    debit_total = queryset.filter(transaction_type='debit').aggregate(
        total=Sum(currency_field)
    )['total'] or Decimal('0')

    total_amount = queryset.aggregate(
        total=Sum(currency_field)
    )['total'] or Decimal('0')

    return {
        'commissions': queryset,
        'total_amount': total_amount,
        'credit_total': credit_total,
        'debit_total': debit_total,
        'net_amount': credit_total - debit_total,
        'count': queryset.count(),
        'currency': currency.upper()
    }

