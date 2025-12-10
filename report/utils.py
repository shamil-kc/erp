from django.db.models import Sum, Q
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem
from customer.models import Party
from datetime import date, timedelta
from calendar import monthrange


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


def get_yearly_summary_report(year):
    """
    Returns a dict with month-wise and yearly summary:
    - opening_stock, closing_stock (qty)
    - sales_qty, sales_amount
    - purchase_qty, purchase_amount
    - grand totals for the year
    """
    months = []
    # Get all products for stock calculation
    from products.models import ProductItem

    # Helper to sum all items' stock for a date
    def total_stock(as_of_date):
        total = 0
        for item in ProductItem.objects.all():
            total += get_closing_stock(item, as_of_date, with_null_invoice=True)
        return total

    # Prepare month boundaries
    year = int(year)
    monthly_data = []
    for m in range(1, 13):
        month_start = date(year, m, 1)
        month_end = date(year, m, monthrange(year, m)[1])

        # Opening stock is closing stock of previous day
        opening_stock = total_stock(month_start - timedelta(days=1))
        closing_stock = total_stock(month_end)

        # Sales
        sales_qs = SaleInvoice.objects.filter(
            status=SaleInvoice.STATUS_APPROVED,
            sale_date__gte=month_start,
            sale_date__lte=month_end
        )
        sales_qty = SaleItem.objects.filter(
            invoice__in=sales_qs
        ).aggregate(total=Sum('qty'))['total'] or 0
        sales_amount = sales_qs.aggregate(total=Sum('total_with_vat_aed'))['total'] or 0

        # Purchases
        purchase_qs = PurchaseInvoice.objects.filter(
            status=PurchaseInvoice.STATUS_APPROVED,
            purchase_date__gte=month_start,
            purchase_date__lte=month_end
        )
        purchase_qty = PurchaseItem.objects.filter(
            invoice__in=purchase_qs
        ).aggregate(total=Sum('qty'))['total'] or 0
        purchase_amount = purchase_qs.aggregate(total=Sum('total_with_vat_aed'))['total'] or 0

        monthly_data.append({
            'month': month_start.strftime('%B'),
            'opening_stock': opening_stock,
            'closing_stock': closing_stock,
            'sales_qty': sales_qty,
            'sales_amount': float(sales_amount),
            'purchase_qty': purchase_qty,
            'purchase_amount': float(purchase_amount),
        })

    # Grand totals for the year
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    opening_stock_year = total_stock(year_start - timedelta(days=1))
    closing_stock_year = total_stock(year_end)

    sales_qs_year = SaleInvoice.objects.filter(
        status=SaleInvoice.STATUS_APPROVED,
        sale_date__gte=year_start,
        sale_date__lte=year_end
    )
    sales_qty_year = SaleItem.objects.filter(
        invoice__in=sales_qs_year
    ).aggregate(total=Sum('qty'))['total'] or 0
    sales_amount_year = sales_qs_year.aggregate(total=Sum('total_with_vat_aed'))['total'] or 0

    purchase_qs_year = PurchaseInvoice.objects.filter(
        status=PurchaseInvoice.STATUS_APPROVED,
        purchase_date__gte=year_start,
        purchase_date__lte=year_end
    )
    purchase_qty_year = PurchaseItem.objects.filter(
        invoice__in=purchase_qs_year
    ).aggregate(total=Sum('qty'))['total'] or 0
    purchase_amount_year = purchase_qs_year.aggregate(total=Sum('total_with_vat_aed'))['total'] or 0

    return {
        'year': year,
        'monthly': monthly_data,
        'grand_totals': {
            'opening_stock': opening_stock_year,
            'closing_stock': closing_stock_year,
            'sales_qty': sales_qty_year,
            'sales_amount': float(sales_amount_year),
            'purchase_qty': purchase_qty_year,
            'purchase_amount': float(purchase_amount_year),
        }
    }
