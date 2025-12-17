from datetime import date, timedelta
from calendar import monthrange
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem
from django.db.models import Sum, Q

def get_yearly_summary_report(year):
    """
    Returns a dict with month-wise and yearly summary:
    - opening_stock, closing_stock (qty)
    - sales_qty, sales_amount
    - purchase_qty, purchase_amount
    - grand totals for the year
    """
    from products.models import ProductItem
    from inventory.models import Stock

    year = int(year)
    monthly_data = []

    # Prefetch all product items and their stocks
    product_items = list(ProductItem.objects.all())
    product_item_ids = [item.id for item in product_items]
    stocks = {s.product_item_id: s.quantity for s in Stock.objects.filter(product_item_id__in=product_item_ids)}
    # Prefetch all orphan purchase items (no invoice)
    orphan_purchase_items = list(PurchaseItem.objects.filter(invoice__isnull=True))
    orphan_purchase_item_amounts = sum([float(p.total_price_aed or 0) for p in orphan_purchase_items])
    orphan_purchase_item_qty = sum([float(p.qty or 0) for p in orphan_purchase_items])

    # Helper: get all purchase/sale items for all products up to a date, grouped by item_id
    def get_qty_dict(model, date_field, status_field, status_value, item_field, date_limit):
        qs = model.objects.filter(
            **{f"{status_field}": status_value, f"{date_field}__lte": date_limit}
        ).values(item_field).annotate(total=Sum('qty'))
        return {row[item_field]: row['total'] or 0 for row in qs}

    def get_qty_dict_lt(model, date_field, status_field, status_value, item_field, date_limit):
        qs = model.objects.filter(
            **{f"{status_field}": status_value, f"{date_field}__lt": date_limit}
        ).values(item_field).annotate(total=Sum('qty'))
        return {row[item_field]: row['total'] or 0 for row in qs}

    # Helper: get latest purchase price for all items up to a date
    def get_latest_purchase_price_dict(as_of_date):
        latest_prices = {}
        # Get all purchases up to as_of_date, order by date desc, id desc
        purchases = PurchaseItem.objects.filter(
            invoice__purchase_date__lte=as_of_date,
            invoice__status=PurchaseInvoice.STATUS_APPROVED
        ).order_by('item_id', '-invoice__purchase_date', '-pk')
        seen = set()
        for p in purchases:
            if p.item_id not in seen:
                latest_prices[p.item_id] = float(p.amount_aed or 0)
                seen.add(p.item_id)
        return latest_prices

    # Helper: get closing stock qty for all items as of a date
    def get_closing_stock_dict(as_of_date):
        purchased = get_qty_dict(PurchaseItem, 'invoice__purchase_date', 'invoice__status', PurchaseInvoice.STATUS_APPROVED, 'item_id', as_of_date)
        sold = get_qty_dict(SaleItem, 'invoice__sale_date', 'invoice__status', SaleInvoice.STATUS_APPROVED, 'item_id', as_of_date)
        closing = {}
        for item in product_items:
            pid = item.id
            closing[pid] = (purchased.get(pid, 0) - sold.get(pid, 0))
        # Add orphan stock
        for p in orphan_purchase_items:
            closing[p.item_id] = closing.get(p.item_id, 0) + (stocks.get(p.item_id, 0))
        return closing

    # Helper: get opening stock qty for all items as of a date
    def get_opening_stock_dict(as_of_date):
        purchased = get_qty_dict_lt(PurchaseItem, 'invoice__purchase_date', 'invoice__status', PurchaseInvoice.STATUS_APPROVED, 'item_id', as_of_date)
        sold = get_qty_dict_lt(SaleItem, 'invoice__sale_date', 'invoice__status', SaleInvoice.STATUS_APPROVED, 'item_id', as_of_date)
        opening = {}
        for item in product_items:
            pid = item.id
            opening[pid] = (purchased.get(pid, 0) - sold.get(pid, 0))
        # Add orphan stock
        for p in orphan_purchase_items:
            opening[p.item_id] = opening.get(p.item_id, 0) + (stocks.get(p.item_id, 0))
        return opening

    # Helper: total stock qty as of a date (includes orphan_purchase_item_qty)
    def total_stock(as_of_date):
        closing = get_closing_stock_dict(as_of_date)
        # Add orphan_purchase_item_qty to total stock count
        return sum(closing.values()) + orphan_purchase_item_qty

    # Helper: total stock amount as of a date (includes orphan_purchase_item_amounts)
    def total_stock_amount(as_of_date):
        closing = get_closing_stock_dict(as_of_date)
        latest_prices = get_latest_purchase_price_dict(as_of_date)
        total = 0
        for pid, qty in closing.items():
            price = latest_prices.get(pid, 0)
            if qty > 0:
                total += qty * price
        total += orphan_purchase_item_amounts
        return total

    def opening_stock_amount(as_of_date):
        opening = get_opening_stock_dict(as_of_date)
        latest_prices = get_latest_purchase_price_dict(as_of_date)
        total = 0
        for pid, qty in opening.items():
            price = latest_prices.get(pid, 0)
            if qty > 0:
                total += qty * price
        total += orphan_purchase_item_amounts
        return total

    # Prepare month boundaries
    for m in range(1, 13):
        month_start = date(year, m, 1)
        month_end = date(year, m, monthrange(year, m)[1])

        opening_stock = total_stock(month_start - timedelta(days=1))
        closing_stock = total_stock(month_end)
        closing_stock_amt = total_stock_amount(month_end)
        opening_stock_amt = opening_stock_amount(month_end)

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
            'closing_stock_amount': float(closing_stock_amt),
            'opening_stock_amount': float(opening_stock_amt),
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
    closing_stock_amount_year = total_stock_amount(year_end)
    opening_stock_amount_year = opening_stock_amount(year_end)

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
            'closing_stock_amount': float(closing_stock_amount_year),
            'opening_stock_amount': float(opening_stock_amount_year),
            'sales_qty': sales_qty_year,
            'sales_amount': float(sales_amount_year),
            'purchase_qty': purchase_qty_year,
            'purchase_amount': float(purchase_amount_year),
        }
    }