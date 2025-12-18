from datetime import date, timedelta
from calendar import monthrange
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem
from django.db.models import Sum, Q, F
from decimal import Decimal

def get_yearly_summary_report(year):
    """
    Returns a dict with month-wise and yearly summary:
    - opening_stock, closing_stock (qty)
    - sales_qty, sales_amount
    - purchase_qty, purchase_amount
    - grand totals for the year

    Opening/closing stock is calculated as sum of all PurchaseItem.qty (including orphan items)
    minus sum of all SaleItem.qty (approved sales) up to the date.
    Stock amount is proportional to remaining qty of each purchase item.
    """
    year = int(year)
    monthly_data = []

    # Helper: Get all purchase items up to a date (including orphan)
    def get_total_stock_qty_and_amount(as_of_date):
        purchases = PurchaseItem.objects.filter(
            Q(invoice__status=PurchaseInvoice.STATUS_APPROVED, invoice__purchase_date__lte=as_of_date) |
            Q(invoice__isnull=True)
        )
        total_purchased_qty = purchases.aggregate(total=Sum('qty'))['total'] or 0
        total_purchased_amount = purchases.aggregate(total=Sum('total_price_aed'))['total'] or Decimal('0')

        # Subtract all sales up to as_of_date
        sales = SaleItem.objects.filter(
            invoice__status=SaleInvoice.STATUS_APPROVED,
            invoice__sale_date__lte=as_of_date
        )
        sales_qty = sales.aggregate(total=Sum('qty'))['total'] or 0
        total_sales_amount = sales.aggregate(
            total=Sum(F('qty') * F('purchase_item__unit_price_aed'))
        )['total'] or Decimal('0')

        # Stock and amount after sales
        closing_qty = total_purchased_qty - sales_qty
        closing_amount = Decimal('0')
        if total_purchased_qty > 0:
            closing_amount = total_purchased_amount - total_sales_amount
        return closing_qty, closing_amount

    # Get previous year closing as opening for this year
    prev_year_end = date(year - 1, 12, 31)
    opening_stock, opening_stock_amount = get_total_stock_qty_and_amount(prev_year_end)

    # For each month, opening = previous closing
    month_closing_qty = opening_stock
    month_closing_amount = opening_stock_amount

    for m in range(1, 13):
        month_start = date(year, m, 1)
        month_end = date(year, m, monthrange(year, m)[1])

        # Opening stock for the month
        opening_stock_month = month_closing_qty
        opening_stock_amount_month = month_closing_amount

        # Purchases in this month (approved invoices only)
        purchases = PurchaseItem.objects.filter(
            Q(invoice__status=PurchaseInvoice.STATUS_APPROVED, invoice__purchase_date__gte=month_start, invoice__purchase_date__lte=month_end)
        )
        purchase_qty = purchases.aggregate(total=Sum('qty'))['total'] or 0
        purchase_amount = purchases.aggregate(total=Sum('total_price_aed'))['total'] or 0

        # Orphan purchases created in this month (no invoice)
        orphan_purchases = PurchaseItem.objects.filter(
            invoice__isnull=True,
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        )
        orphan_purchase_qty = orphan_purchases.aggregate(total=Sum('qty'))['total'] or 0
        orphan_purchase_amount = orphan_purchases.aggregate(total=Sum('total_price_aed'))['total'] or 0

        # Add orphan purchases to this month's purchase totals
        purchase_qty += orphan_purchase_qty
        purchase_amount += orphan_purchase_amount

        # Sales in this month (approved invoices only)
        sales = SaleItem.objects.filter(
            invoice__status=SaleInvoice.STATUS_APPROVED,
            invoice__sale_date__gte=month_start,
            invoice__sale_date__lte=month_end
        )
        sales_qty = sales.aggregate(total=Sum('qty'))['total'] or 0
        sales_amount = sales.aggregate(total=Sum('total_price_aed'))['total'] or 0

        # Closing stock for the month
        closing_stock, closing_stock_amount = get_total_stock_qty_and_amount(month_end)

        monthly_data.append({
            'month': month_start.strftime('%B'),
            'opening_stock': opening_stock_month,
            'opening_stock_amount': float(opening_stock_amount_month),
            'purchase_qty': purchase_qty,
            'purchase_amount': float(purchase_amount),
            'sales_qty': sales_qty,
            'sales_amount': float(sales_amount),
            'closing_stock': closing_stock,
            'closing_stock_amount': float(closing_stock_amount),
        })

        # Set for next month
        month_closing_qty = closing_stock
        month_closing_amount = closing_stock_amount

    # Grand totals for the year
    year_end = date(year, 12, 31)
    closing_stock_year, closing_stock_amount_year = get_total_stock_qty_and_amount(year_end)

    return {
        'year': year,
        'monthly': monthly_data,
        'grand_totals': {
            'opening_stock': opening_stock,
            'opening_stock_amount': float(opening_stock_amount),
            'closing_stock': closing_stock_year,
            'closing_stock_amount': float(closing_stock_amount_year),
        }
    }