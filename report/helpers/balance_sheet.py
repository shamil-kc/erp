from core.models import CapitalAccount
from banking.models import CashAccount
from common.models import Asset
from sale.models import SaleInvoice
from purchase.models import PurchaseInvoice
from customer.models import Party
from decimal import Decimal
from django.db.models import Sum
from report.utils import get_sundry_debtors, get_sundry_creditors
from report.helpers.profict_loss import get_profit_and_loss_report


def get_balance_sheet_report(as_of_date=None):
    """
    Returns a dict with balance sheet data as of a given date.
    All totals are shown separately (not grouped), and lists are included for sundry debtors/creditors.
    """

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
            from report.utils import get_closing_stock
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

    # Sale cheque pending: sum of sale payments by cheque not cleared
    sale_cheque_pending = PaymentEntry.objects.filter(
        invoice_type='sale',
        payment_type='check',
        is_cheque_cleared=False,
        payment_date__lte=as_of_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Purchase cheque pending: sum of purchase payments by cheque not cleared
    purchase_cheque_pending = PaymentEntry.objects.filter(
        invoice_type='purchase',
        payment_type='check',
        is_cheque_cleared=False,
        payment_date__lte=as_of_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Salary paid and pending
    from employee.models import SalaryEntry, SalaryPayment
    # Total salary paid: sum of all payments made up to as_of_date
    total_salary_paid = SalaryPayment.objects.filter(
        date__lte=as_of_date
    ).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

    # Total salary pending: sum of all salary entries minus sum of all payments
    total_salary_entry = SalaryEntry.objects.filter(
        date__lte=as_of_date
    ).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')
    total_salary_pending = total_salary_entry - total_salary_paid

    # Profit and loss total (net profit till date)
    profit_loss = get_profit_and_loss_report('2000-01-01', as_of_date)
    net_profit = profit_loss['profit']['net_profit']

    # Total sale VAT up to as_of_date
    total_sale_vat = SaleInvoice.objects.filter(
        status=SaleInvoice.STATUS_APPROVED,
        sale_date__lte=as_of_date
    ).aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')

    # Total purchase VAT up to as_of_date
    total_purchase_vat = PurchaseInvoice.objects.filter(
        status=PurchaseInvoice.STATUS_APPROVED,
        purchase_date__lte=as_of_date
    ).aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')

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
        # Cheque pending
        'sale_cheque_pending': float(sale_cheque_pending),
        'purchase_cheque_pending': float(purchase_cheque_pending),
        # Salary
        'total_salary_entry': float(total_salary_entry),
        'total_salary_paid': float(total_salary_paid),
        'total_salary_pending': float(total_salary_pending),
        # VAT
        'total_sale_vat': float(total_sale_vat),
        'total_purchase_vat': float(total_purchase_vat),
    }
