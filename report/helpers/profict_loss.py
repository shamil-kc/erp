from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem, SaleReturnItem, SaleReturnItemEntry
from purchase.models import PurchaseReturnItemEntry, PurchaseReturnItem
from common.models import Expense, Wage, Commission, ServiceFee, ExtraCharges,Asset, ExpenseType
from employee.models import SalaryEntry
from inventory.models import Stock
from products.models import ProductItem
from django.db.models import Sum, Q
from decimal import Decimal



def get_profit_and_loss_report(start_date, end_date):
    """
    Returns a dict with profit and loss data for the given period.
    Includes: purchase, sale, direct/indirect expenses (type-wise), opening/closing stock,
    service fees, commission, wage, extra charges, salary, assets, liabilities.
    """

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
            from report.utils import get_closing_stock
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

    # --- Sales Return ---
    sales_return_entries = SaleReturnItemEntry.objects.filter(
        sale_return__return_date__gte=start_date,
        sale_return__return_date__lte=end_date
    )
    sales_return_aed = sales_return_entries.aggregate(
        total=Sum('sale_item__amount_aed')
    )['total'] or Decimal('0')

    # --- Purchase Return ---
    purchase_return_entries = PurchaseReturnItemEntry.objects.filter(
        purchase_return__return_date__gte=start_date,
        purchase_return__return_date__lte=end_date
    )
    purchase_return_aed = purchase_return_entries.aggregate(
        total=Sum('purchase_item__amount_aed')
    )['total'] or Decimal('0')

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
            'purchase_return_aed': float(purchase_return_aed),
        },
        'sales': {
            'total_with_vat_aed': float(total_sales_with_vat_aed),
            'total_without_vat_aed': float(total_sales_without_vat_aed),
            'vat_aed': float(total_sales_vat_aed),
            'discount_aed': float(total_sales_discount_aed),
            'shipping_aed': float(sales_shipping_aed),
            'sales_return_aed': float(sales_return_aed),
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