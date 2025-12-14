from decimal import Decimal

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
    from products.models import ProductItem
    from inventory.models import Stock

    def total_stock(as_of_date):
        total = 0
        for item in ProductItem.objects.all():
            total += get_closing_stock(item, as_of_date, with_null_invoice=False)
        purchased_items = PurchaseItem.objects.filter(invoice__isnull=True).values_list('item_id', flat=True).distinct()
        if purchased_items:
            for item_id in purchased_items:
                stock_qty = Stock.objects.filter(product_item_id=item_id).aggregate(total=Sum('quantity'))['total'] or 0
                total += stock_qty
        return total

    def closing_stock_amount(as_of_date):
        """
        Calculate the total value (amount_aed) of closing stock as of a date.
        Uses latest purchase price for each item in stock.
        """
        total_amount = 0
        for item in ProductItem.objects.all():
            qty = get_closing_stock(item, as_of_date, with_null_invoice=False)
            if qty > 0:
                # Get latest purchase price (amount_aed) for this item before as_of_date
                latest_purchase = PurchaseItem.objects.filter(
                    item=item,
                    invoice__purchase_date__lte=as_of_date,
                    invoice__status=PurchaseInvoice.STATUS_APPROVED
                ).order_by('-invoice__purchase_date', '-pk').first()
                price = latest_purchase.amount_aed if latest_purchase else 0
                total_amount += qty * float(price)
        # Add orphan stock (items with stock but no purchase invoice)
        purchased_items = PurchaseItem.objects.filter(invoice__isnull=True, ).values_list('total_price_aed', flat=True)
        total_amount += float(sum(purchased_items))
        return total_amount

    # Prepare month boundaries
    year = int(year)
    monthly_data = []
    for m in range(1, 13):
        month_start = date(year, m, 1)
        month_end = date(year, m, monthrange(year, m)[1])

        # Opening stock is closing stock of previous day
        opening_stock = total_stock(month_start - timedelta(days=1))
        closing_stock = total_stock(month_end)
        closing_stock_amt = closing_stock_amount(month_end)

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
    closing_stock_amount_year = closing_stock_amount(year_end)

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
            'sales_qty': sales_qty_year,
            'sales_amount': float(sales_amount_year),
            'purchase_qty': purchase_qty_year,
            'purchase_amount': float(purchase_amount_year),
        }
    }


def get_profit_and_loss_report(start_date, end_date):
    """
    Returns a dict with profit and loss data for the given period.
    Includes: purchase, sale, direct/indirect expenses (type-wise), opening/closing stock,
    service fees, commission, wage, extra charges, salary, assets, liabilities.
    """
    from purchase.models import PurchaseInvoice, PurchaseItem
    from sale.models import SaleInvoice, SaleItem
    from common.models import Expense, Wage, Commission, ServiceFee, ExtraCharges, Asset, ExpenseType
    from employee.models import SalaryEntry
    from inventory.models import Stock
    from products.models import ProductItem
    from django.db.models import Sum, Q
    from decimal import Decimal

    # Purchases
    purchase_invoices = PurchaseInvoice.objects.filter(
        status=PurchaseInvoice.STATUS_APPROVED,
        purchase_date__gte=start_date,
        purchase_date__lte=end_date
    )
    total_purchase_with_vat_aed = purchase_invoices.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
    total_purchase_vat_aed = purchase_invoices.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
    total_purchase_without_vat_aed = total_purchase_with_vat_aed - total_purchase_vat_aed
    total_purchase_discount_aed = purchase_invoices.aggregate(total=Sum('discount_aed'))['total'] or Decimal('0')
    purchase_ids = list(purchase_invoices.values_list('id', flat=True))
    purchase_shipping_aed = PurchaseItem.objects.filter(invoice_id__in=purchase_ids).aggregate(
        total=Sum('shipping_per_unit_aed'))['total'] or Decimal('0')

    # Sales
    sales_invoices = SaleInvoice.objects.filter(
        status=SaleInvoice.STATUS_APPROVED,
        sale_date__gte=start_date,
        sale_date__lte=end_date
    )
    total_sales_with_vat_aed = sales_invoices.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
    total_sales_vat_aed = sales_invoices.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
    total_sales_without_vat_aed = total_sales_with_vat_aed - total_sales_vat_aed
    total_sales_discount_aed = sales_invoices.aggregate(total=Sum('discount_aed'))['total'] or Decimal('0')
    sales_ids = list(sales_invoices.values_list('id', flat=True))
    sales_shipping_aed = SaleItem.objects.filter(invoice_id__in=sales_ids).aggregate(
        total=Sum('shipping_aed'))['total'] or Decimal('0')

    # Expenses (type-wise for direct and indirect)
    direct_expenses_qs = Expense.objects.filter(
        type__category='direct',
        date__gte=start_date,
        date__lte=end_date
    )
    indirect_expenses_qs = Expense.objects.filter(
        type__category='indirect',
        date__gte=start_date,
        date__lte=end_date
    )

    # Aggregate totals
    direct_expenses_aed = direct_expenses_qs.aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')
    indirect_expenses_aed = indirect_expenses_qs.aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

    # Type-wise breakdowns
    direct_expenses_typewise = list(
        direct_expenses_qs.values('type__name').annotate(total=Sum('amount_aed'))
    )
    indirect_expenses_typewise = list(
        indirect_expenses_qs.values('type__name').annotate(total=Sum('amount_aed'))
    )

    # Wages
    total_wages_aed = Wage.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

    # Salary
    total_salary_aed = SalaryEntry.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

    # Service Fees
    total_service_fees_aed = ServiceFee.objects.filter(
        sales_invoice__sale_date__gte=start_date,
        sales_invoice__sale_date__lte=end_date
    ).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

    # Commission
    total_commission_aed = Commission.objects.filter(
        sales_invoice__sale_date__gte=start_date,
        sales_invoice__sale_date__lte=end_date
    ).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

    # Extra Charges (for sales and purchases)
    extra_charges_sales = ExtraCharges.objects.filter(
        content_type__model='saleinvoice',
        sale_invoices__sale_date__gte=start_date,
        sale_invoices__sale_date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    extra_charges_purchase = ExtraCharges.objects.filter(
        content_type__model='purchaseinvoice',
        purchase_invoices__purchase_date__gte=start_date,
        purchase_invoices__purchase_date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_extra_charges_aed = extra_charges_sales + extra_charges_purchase

    # Opening Stock (as of start_date)
    def get_total_stock_value(as_of_date):
        total = Decimal('0')
        for item in ProductItem.objects.all():
            # Get closing stock qty as of as_of_date
            from .utils import get_closing_stock
            qty = get_closing_stock(item, as_of_date)
            if qty > 0:
                # Get latest purchase price (amount_aed) for this item before as_of_date
                latest_purchase = PurchaseItem.objects.filter(
                    item=item,
                    invoice__purchase_date__lte=as_of_date,
                    invoice__status=PurchaseInvoice.STATUS_APPROVED
                ).order_by('-invoice__purchase_date', '-pk').first()
                price = latest_purchase.amount_aed if latest_purchase else Decimal('0')
                total += qty * price
        return total

    opening_stock_aed = get_total_stock_value(start_date)
    closing_stock_aed = get_total_stock_value(end_date)

    # Assets
    assets = Asset.objects.all()
    assets_total = assets.aggregate(total=Sum('price'))['total'] or Decimal('0')
    assets_list = [
        {
            'name': a.name,
            'price': float(a.price),
            'quantity': a.quantity,
            'status': a.status,
            'description': a.description
        }
        for a in assets
    ]

    # Liabilities (Sundry Creditors)
    from customer.models import Party
    creditors = Party.objects.filter(
        type='supplier',
        purchase_invoices__status=PurchaseInvoice.STATUS_APPROVED,
        purchase_invoices__purchase_date__lte=end_date
    ).annotate(
        total_credit=Sum('purchase_invoices__total_with_vat_aed')
    ).filter(total_credit__gt=0)
    liabilities_total = sum([c.total_credit for c in creditors]) if creditors else Decimal('0')
    liabilities_list = [
        {
            'party': c.name,
            'amount': float(c.total_credit)
        }
        for c in creditors
    ]

    # Net Profit Calculation
    gross_profit = (total_sales_without_vat_aed + closing_stock_aed) - (total_purchase_without_vat_aed + opening_stock_aed)
    net_profit = gross_profit - (direct_expenses_aed + indirect_expenses_aed + total_wages_aed + total_salary_aed + total_commission_aed)

    # --- Return flat dict, no asset/liability sections ---
    return {
        'period': {
            'start_date': str(start_date),
            'end_date': str(end_date)
        },
        'purchase': {
            'total_with_vat_aed': float(total_purchase_with_vat_aed),
            'total_without_vat_aed': float(total_purchase_without_vat_aed),
            'vat_aed': float(total_purchase_vat_aed),
            'discount_aed': float(total_purchase_discount_aed),
            'shipping_aed': float(purchase_shipping_aed),
        },
        'sales': {
            'total_with_vat_aed': float(total_sales_with_vat_aed),
            'total_without_vat_aed': float(total_sales_without_vat_aed),
            'vat_aed': float(total_sales_vat_aed),
            'discount_aed': float(total_sales_discount_aed),
            'shipping_aed': float(sales_shipping_aed),
        },
        'expenses': {
            'direct_expenses_aed': float(direct_expenses_aed),
            'direct_expenses_typewise': [
                {'type': e['type__name'], 'total': float(e['total'] or 0)}
                for e in direct_expenses_typewise
            ],
            'indirect_expenses_aed': float(indirect_expenses_aed),
            'indirect_expenses_typewise': [
                {'type': e['type__name'], 'total': float(e['total'] or 0)}
                for e in indirect_expenses_typewise
            ],
            'wages_aed': float(total_wages_aed),
            'salary_aed': float(total_salary_aed),
            'commission_aed': float(total_commission_aed),
            'service_fees_aed': float(total_service_fees_aed),
            'extra_charges_aed': float(total_extra_charges_aed),
        },
        'stock': {
            'opening_stock_aed': float(opening_stock_aed),
            'closing_stock_aed': float(closing_stock_aed),
        },
        'profit': {
            'gross_profit': float(gross_profit),
            'net_profit': float(net_profit),
        }
    }


def get_balance_sheet_report(as_of_date=None):
    """
    Returns a dict with balance sheet data as of a given date.
    All totals are shown separately (not grouped), and lists are included for sundry debtors/creditors.
    """
    from core.models import CapitalAccount
    from banking.models import CashAccount
    from common.models import Asset
    from sale.models import SaleInvoice
    from purchase.models import PurchaseInvoice
    from customer.models import Party
    from decimal import Decimal
    from django.db.models import Sum

    # Use today if no date provided
    import datetime
    if not as_of_date:
        as_of_date = datetime.date.today()

    # Total capital
    total_capital = CapitalAccount.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0')

    # Profit cash account (type='profit')
    profit_cash = CashAccount.objects.filter(type='profit').first()
    profit_cash_in_hand = profit_cash.cash_in_hand if profit_cash else Decimal('0')
    profit_cash_in_bank = profit_cash.cash_in_bank if profit_cash else Decimal('0')
    profit_cash_total = (profit_cash_in_hand or Decimal('0')) + (profit_cash_in_bank or Decimal('0'))

    # Fixed assets
    fixed_assets_qs = Asset.objects.filter(status='holding')
    fixed_assets_total = fixed_assets_qs.aggregate(total=Sum('price'))['total'] or Decimal('0')
    fixed_assets = [
        {'name': a.name, 'price': float(a.price), 'quantity': a.quantity, 'description': a.description}
        for a in fixed_assets_qs
    ]

    # Closing stock (current assets)
    from products.models import ProductItem
    from purchase.models import PurchaseItem
    def get_total_stock_value(as_of_date):
        total = Decimal('0')
        for item in ProductItem.objects.all():
            from .utils import get_closing_stock
            qty = get_closing_stock(item, as_of_date)
            if qty > 0:
                latest_purchase = PurchaseItem.objects.filter(
                    item=item,
                    invoice__purchase_date__lte=as_of_date,
                    invoice__status=PurchaseInvoice.STATUS_APPROVED
                ).order_by('-invoice__purchase_date', '-pk').first()
                price = latest_purchase.amount_aed if latest_purchase else Decimal('0')
                total += qty * price
        return total
    closing_stock = get_total_stock_value(as_of_date)

    # Sundry debtors (current assets)
    sundry_debtors_total = get_sundry_debtors(as_of_date, currency='aed')
    sundry_debtors_qs = Party.objects.filter(
        type='customer',
        sale_invoices__status=SaleInvoice.STATUS_APPROVED,
        sale_invoices__sale_date__lte=as_of_date
    ).annotate(
        total_debt=Sum('sale_invoices__total_with_vat_aed')
    ).filter(total_debt__gt=0)
    sundry_debtors_list = [
        {'party': p.name, 'amount': float(p.total_debt)}
        for p in sundry_debtors_qs
    ]

    # Cash in hand and bank (main cash account)
    main_cash = CashAccount.objects.filter(type='main').first()
    cash_in_hand = main_cash.cash_in_hand if main_cash else Decimal('0')
    cash_in_bank = main_cash.cash_in_bank if main_cash else Decimal('0')

    # Current liabilities: amount payable (approved purchases not paid), sundry creditors
    sundry_creditors_total = get_sundry_creditors(as_of_date, currency='aed')
    sundry_creditors_qs = Party.objects.filter(
        type='supplier',
        purchase_invoices__status=PurchaseInvoice.STATUS_APPROVED,
        purchase_invoices__purchase_date__lte=as_of_date
    ).annotate(
        total_credit=Sum('purchase_invoices__total_with_vat_aed')
    ).filter(total_credit__gt=0)
    sundry_creditors_list = [
        {'party': p.name, 'amount': float(p.total_credit)}
        for p in sundry_creditors_qs
    ]

    # Amount payable: total of approved purchases minus payments made
    total_purchases = PurchaseInvoice.objects.filter(
        status=PurchaseInvoice.STATUS_APPROVED,
        purchase_date__lte=as_of_date
    ).aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
    from banking.models import PaymentEntry
    payments_made = PaymentEntry.objects.filter(
        invoice_type='purchase',
        payment_date__lte=as_of_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0'
    )
    amount_payable = total_purchases - payments_made

    # Profit and loss total (net profit till date)
    from report.utils import get_profit_and_loss_report
    profit_loss = get_profit_and_loss_report('2000-01-01', as_of_date)
    net_profit = profit_loss['profit']['net_profit']

    return {
        'as_of_date': str(as_of_date),
        # Assets
        'fixed_assets_total': float(fixed_assets_total),
        'fixed_assets_list': fixed_assets,
        'closing_stock': float(closing_stock),
        'sundry_debtors_total': float(sundry_debtors_total),
        'sundry_debtors_list': sundry_debtors_list,
        'cash_in_hand': float(cash_in_hand),
        'cash_in_bank': float(cash_in_bank),
        'profit_cash_in_hand': float(profit_cash_in_hand),
        'profit_cash_in_bank': float(profit_cash_in_bank),
        'profit_cash_total': float(profit_cash_total),
        # Liabilities
        'total_capital': float(total_capital),
        'amount_payable': float(amount_payable),
        'sundry_creditors_total': float(sundry_creditors_total),
        'sundry_creditors_list': sundry_creditors_list,
        'profit_and_loss': float(net_profit),
    }
