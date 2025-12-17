from decimal import Decimal
from django.db.models import Sum, Q
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem
from customer.models import Party


def get_opening_stock(item, start_date, with_null_invoice=False):
    purchase_filter = {
        'item': item,
        'invoice__purchase_date__lt': start_date,
    }
    sale_filter = {
        'item': item,
        'invoice__sale_date__lt': start_date,
    }

    if with_null_invoice:
        purchased = PurchaseItem.objects.filter(
            (Q(invoice__status=PurchaseInvoice.STATUS_APPROVED) | Q(invoice__isnull=True)),
            **purchase_filter
        ).aggregate(total=Sum('qty'))['total'] or 0

        sold = SaleItem.objects.filter(
            (Q(invoice__status=SaleInvoice.STATUS_APPROVED) | Q(invoice__isnull=True)),
            **sale_filter
        ).aggregate(total=Sum('qty'))['total'] or 0
    else:
        purchased = PurchaseItem.objects.filter(
            invoice__status=PurchaseInvoice.STATUS_APPROVED,
            **purchase_filter
        ).aggregate(total=Sum('qty'))['total'] or 0

        sold = SaleItem.objects.filter(
            invoice__status=SaleInvoice.STATUS_APPROVED,
            **sale_filter
        ).aggregate(total=Sum('qty'))['total'] or 0

    return purchased - sold


def get_closing_stock(item, end_date, with_null_invoice=False):
    purchase_filter = {
        'item': item,
        'invoice__purchase_date__lte': end_date,
    }
    sale_filter = {
        'item': item,
        'invoice__sale_date__lte': end_date,
    }

    if with_null_invoice:
        purchased = PurchaseItem.objects.filter(
            (Q(invoice__status=PurchaseInvoice.STATUS_APPROVED) | Q(invoice__isnull=True)),
            **purchase_filter
        ).aggregate(total=Sum('qty'))['total'] or 0

        sold = SaleItem.objects.filter(
            (Q(invoice__status=SaleInvoice.STATUS_APPROVED) | Q(invoice__isnull=True)),
            **sale_filter
        ).aggregate(total=Sum('qty'))['total'] or 0
    else:
        purchased = PurchaseItem.objects.filter(
            invoice__status=PurchaseInvoice.STATUS_APPROVED,
            **purchase_filter
        ).aggregate(total=Sum('qty'))['total'] or 0

        sold = SaleItem.objects.filter(
            invoice__status=SaleInvoice.STATUS_APPROVED,
            **sale_filter
        ).aggregate(total=Sum('qty'))['total'] or 0

    return purchased - sold


def get_sundry_debtors(as_of_date, currency='aed'):
    """
    Get total amount owed by customers (debtors) as of a specific date.

    Args:
        as_of_date: Date to calculate debtors as of
        currency: 'usd' or 'aed'

    Returns:
        Decimal: Total amount owed by customers
    """
    currency_field = f'total_with_vat_{currency.lower()}'

    # Get approved sales invoices up to the specified date
    debtors_amount = SaleInvoice.objects.filter(
        status=SaleInvoice.STATUS_APPROVED,
        sale_date__lte=as_of_date
    ).aggregate(total=Sum(currency_field))['total'] or 0

    return debtors_amount


def get_sundry_creditors(as_of_date, currency='usd'):
    """
    Get total amount owed to suppliers (creditors) as of a specific date.

    Args:
        as_of_date: Date to calculate creditors as of
        currency: 'usd' or 'aed'

    Returns:
        Decimal: Total amount owed to suppliers
    """
    currency_field = f'total_with_vat_{currency.lower()}'

    # Get approved purchase invoices up to the specified date
    creditors_amount = PurchaseInvoice.objects.filter(
        status=PurchaseInvoice.STATUS_APPROVED,
        purchase_date__lte=as_of_date
    ).aggregate(total=Sum(currency_field))['total'] or 0

    return creditors_amount


def get_sundry_debtors_by_party(as_of_date, currency='aed'):
    """
    Get sundry debtors broken down by party (customer).

    Args:
        as_of_date: Date to calculate debtors as of
        currency: 'usd' or 'aed'

    Returns:
        QuerySet: Parties with their total debt amounts
    """
    currency_field = f'total_with_vat_{currency.lower()}'

    return Party.objects.filter(
        type='customer',
        sale_invoices__status=SaleInvoice.STATUS_APPROVED,
        sale_invoices__sale_date__lte=as_of_date
    ).annotate(
        total_debt=Sum(f'sale_invoices__{currency_field}')
    ).filter(total_debt__gt=0)


def get_sundry_creditors_by_party(as_of_date, currency='usd'):
    """
    Get sundry creditors broken down by party (supplier).

    Args:
        as_of_date: Date to calculate creditors as of
        currency: 'usd' or 'aed'

    Returns:
        QuerySet: Parties with their total credit amounts
    """
    currency_field = f'total_with_vat_{currency.lower()}'

    return Party.objects.filter(
        type='supplier',
        purchase_invoices__status=PurchaseInvoice.STATUS_APPROVED,
        purchase_invoices__purchase_date__lte=as_of_date
    ).annotate(
        total_credit=Sum(f'purchase_invoices__{currency_field}')
    ).filter(total_credit__gt=0)
