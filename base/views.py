from django.shortcuts import render, get_object_or_404,redirect
from .models import (Product, ProductType, ProductGrade, ProductItem,
                     PurchaseItem,PurchaseInvoice, SaleInvoice, SaleItem, Tax,ExpenseType,
                     Expense, Account, SalaryEntry
                     )
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
import datetime
from django.utils.timezone import now
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import JsonResponse
from datetime import timedelta
from collections import defaultdict


def product_list(request):
    items = ProductItem.objects.select_related('grade__product_type__product').all()
    return render(request, 'erp/product_list.html', {'items': items})


from django.db.models import Sum
from django.shortcuts import render
from .models import ProductItem, PurchaseItem, SaleItem

def inventory_report(request):
    items = ProductItem.objects.all()

    purchased_qty_data = dict(
        PurchaseItem.objects.values_list('item_id')
        .annotate(s=Sum('qty')).values_list('item_id', 's')
    )
    sold_qty_data = dict(
        SaleItem.objects.values_list('item_id')
        .annotate(s=Sum('qty')).values_list('item_id', 's')
    )

    item_list = []
    for item in items:
        purchased = purchased_qty_data.get(item.id, 0)
        sold = sold_qty_data.get(item.id, 0)
        stock = purchased - sold
        item_list.append({
            'item': item,
            'purchased': purchased,
            'sold': sold,
            'stock': stock,
        })

    return render(request, 'erp/inventory_report.html', {'items': item_list})


def sales_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    month = request.GET.get('month')

    invoices = SaleInvoice.objects.prefetch_related('sale_items')

    # Filter invoices by date range or month
    if start_date and end_date:
        try:
            from_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date() + timezone.timedelta(days=1)
            invoices = invoices.filter(sale_date__gte=from_date, sale_date__lt=to_date)
        except Exception:
            pass
    elif month:
        try:
            year, mon = map(int, month.split('-'))
            from_date = timezone.datetime(year, mon, 1).date()
            to_date = (from_date + timezone.timedelta(days=32)).replace(day=1)
            invoices = invoices.filter(sale_date__gte=from_date, sale_date__lt=to_date)
        except Exception:
            pass

    context = {
        'invoices': invoices,
        'month': month or 'All',
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'erp/sales_report.html', context)



def sales_add(request):
    if request.method == 'POST':
        invoice_no = request.POST.get('invoice_no')
        customer_name = request.POST.get('customer_name')
        sale_date = request.POST.get('sale_date') or timezone.now().date()

        invoice = SaleInvoice.objects.create(
            invoice_no=invoice_no,
            customer_name=customer_name,
            sale_date=sale_date,
        )

        total = int(request.POST.get('form-TOTAL_FORMS', 1))
        for i in range(total):
            item_id = request.POST.get(f'form-{i}-item')
            qty = request.POST.get(f'form-{i}-qty')
            sale_price_usd = request.POST.get(f'form-{i}-sale_price_usd')
            sale_price_aed = request.POST.get(f'form-{i}-sale_price_aed')
            shipping_usd = request.POST.get(f'form-{i}-shipping_usd', '0')
            shipping_aed = request.POST.get(f'form-{i}-shipping_aed', '0')

            if not (item_id and qty and sale_price_usd and sale_price_aed):
                continue

            try:
                qty = int(qty)
                sale_price_usd = Decimal(sale_price_usd)
                sale_price_aed = Decimal(sale_price_aed)
                shipping_usd = Decimal(shipping_usd)
                shipping_aed = Decimal(shipping_aed)
            except Exception:
                continue

            SaleItem.objects.create(
                invoice=invoice,
                item_id=item_id,
                qty=qty,
                sale_price_usd=sale_price_usd,
                sale_price_aed=sale_price_aed, shipping_usd=shipping_usd,
                shipping_aed=shipping_aed,
            )

        # HERE: call totals calculation after all items are created
        invoice.calculate_totals()

        return redirect('sales-report')

    items = ProductItem.objects.all()
    return render(request, 'erp/sales_add.html', {'items': items, 'today': timezone.now().date()})


def generate_invoice(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, pk=invoice_id)
    return render(request, 'erp/invoice.html', {'invoice': invoice})


from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
import datetime
from django.shortcuts import render
from .models import SaleInvoice, PurchaseInvoice, Expense, Tax

def profit_and_corporate_tax_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sales = SaleInvoice.objects.prefetch_related('sale_items__item__grade__product_type__product')
    purchases = PurchaseInvoice.objects.prefetch_related('purchase_items__item__grade__product_type__product')
    expenses = Expense.objects.all()

    if start_date and end_date:
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            sales = sales.filter(sale_date__gte=start, sale_date__lte=end)
            purchases = purchases.filter(purchase_date__gte=start, purchase_date__lte=end)
            expenses = expenses.filter(date__gte=start, date__lte=end)
        except Exception:
            start = None
            end = None
    else:
        start = None
        end = None

    tax = Tax.objects.filter(active=True).first()

    # Aggregate summary totals for profit calculations
    total_sales_aed = sales.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
    total_sales_usd = sales.aggregate(total=Sum('total_with_vat_usd'))['total'] or Decimal('0')
    total_purchases_aed = purchases.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
    total_purchases_usd = purchases.aggregate(total=Sum('total_with_vat_usd'))['total'] or Decimal('0')
    total_expenses_aed = expenses.aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')
    total_expenses_usd = expenses.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0')

    profit_aed = total_sales_aed - (total_purchases_aed + total_expenses_aed)
    profit_usd = total_sales_usd - (total_purchases_usd + total_expenses_usd)

    vat_collected_aed = sales.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
    vat_collected_usd = sales.aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
    vat_paid_aed = purchases.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
    vat_paid_usd = purchases.aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')

    corp_tax_percent = tax.corporate_tax_percent if tax else Decimal('9')
    corp_tax_aed = profit_aed * (corp_tax_percent / Decimal('100'))
    corp_tax_usd = profit_usd * (corp_tax_percent / Decimal('100'))

    context = {
        'start': start_date or '',
        'end': end_date or '',
        'tax': tax,
        'total_sales_aed': total_sales_aed,
        'total_sales_usd': total_sales_usd,
        'total_purchases_aed': total_purchases_aed,
        'total_purchases_usd': total_purchases_usd,
        'total_expenses_aed': total_expenses_aed,
        'total_expenses_usd': total_expenses_usd,
        'profit_aed': profit_aed,
        'profit_usd': profit_usd,
        'vat_collected_aed': vat_collected_aed,
        'vat_collected_usd': vat_collected_usd,
        'vat_paid_aed': vat_paid_aed,
        'vat_paid_usd': vat_paid_usd,
        'corp_tax_aed': corp_tax_aed,
        'corp_tax_usd': corp_tax_usd,
        # Add invoices data to show detailed table info
        'sales': sales.order_by('sale_date', 'invoice_no'),
        'purchases': purchases.order_by('purchase_date', 'invoice_no'),
        'expenses': expenses.order_by('date'),
    }
    return render(request, 'erp/profit_report.html', context)





def product_item_add(request):
    if request.method == 'POST':
        total = int(request.POST.get('form-TOTAL_FORMS', 1))
        items_data = []
        for i in range(total):
            product = request.POST.get(f'form-{i}-product', '').strip()
            product_type = request.POST.get(f'form-{i}-product_type', '').strip()
            grade = request.POST.get(f'form-{i}-grade', '').strip()
            size = request.POST.get(f'form-{i}-size', '').strip()
            unit = request.POST.get(f'form-{i}-unit', '').strip()
            weight = request.POST.get(f'form-{i}-weight_kg_each', '').strip()

            # Skip empty rows
            if not (product and product_type and grade and size and unit and weight):
                continue

            # Get or create Product
            prod_obj, _ = Product.objects.get_or_create(name=product)
            # Get or create ProductType
            prodtype_obj, _ = ProductType.objects.get_or_create(product=prod_obj, type_name=product_type)
            # Get or create Grade
            grade_obj, _ = ProductGrade.objects.get_or_create(product_type=prodtype_obj, grade=grade)
            # Create ProductItem (size+unit+weight are unique per grade)
            ProductItem.objects.get_or_create(
                grade=grade_obj,
                size=size,
                unit=unit,
                weight_kg_each=weight,
            )
        return redirect('product-list')

    # For autocomplete fields, supply all existing values for select options
    products = Product.objects.values_list('name', flat=True).distinct()
    types = ProductType.objects.values_list('type_name', flat=True).distinct()
    grades = ProductGrade.objects.values_list('grade', flat=True).distinct()
    return render(request, 'erp/product_item_add.html', {
        'products': products,
        'types': types,
        'grades': grades,
    })


from collections import defaultdict
from django.shortcuts import render
from django.db.models import Sum
import datetime
from .models import PurchaseInvoice, PurchaseItem

def purchase_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    month = request.GET.get('month')

    invoices = PurchaseInvoice.objects.prefetch_related('purchase_items__item__grade__product_type__product').order_by('invoice_no', 'id')

    if start_date and end_date:
        try:
            from_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            to_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
            invoices = invoices.filter(purchase_date__gte=from_date, purchase_date__lt=to_date)
        except Exception:
            pass
    elif month:
        try:
            year, mon = map(int, month.split('-'))
            from_date = datetime.date(year, mon, 1)
            to_date = (from_date + datetime.timedelta(days=32)).replace(day=1)
            invoices = invoices.filter(purchase_date__gte=from_date, purchase_date__lt=to_date)
        except Exception:
            pass

    # To pass data to template with totals
    purchase_invoices = []
    for invoice in invoices:
        items = invoice.purchase_items.all()
        total_amount_usd = sum([(item.unit_price_usd * item.qty) + (item.shipping_per_unit_usd * item.qty) for item in items])
        total_amount_aed = sum([(item.unit_price_aed * item.qty) + (item.shipping_per_unit_aed * item.qty) for item in items])
        total_vat_usd = sum([item.vat_amount_usd or 0 for item in items])
        total_vat_aed = sum([item.vat_amount_aed or 0 for item in items])
        total_shipping_usd = sum([item.shipping_per_unit_usd * item.qty for item in items])
        total_shipping_aed = sum([item.shipping_per_unit_aed * item.qty for item in items])
        purchase_date = invoice.purchase_date

        purchase_invoices.append({
            'invoice_no': invoice.invoice_no,
            'purchase_date': purchase_date,
            'items': items,
            'total_amount_usd': total_amount_usd,
            'total_amount_aed': total_amount_aed,
            'total_vat_usd': total_vat_usd,
            'total_vat_aed': total_vat_aed,
            'total_shipping_usd': total_shipping_usd,
            'total_shipping_aed': total_shipping_aed,
        })

    context = {
        'purchase_invoices': purchase_invoices,
        'month': month or 'All',
        'start_date': start_date or '',
        'end_date': end_date or '',
    }
    return render(request, 'erp/purchase_report.html', context)





# API endpoint to create or get related model for AJAX
def get_or_create_product_related(request):
    kind = request.GET.get("kind")
    value = request.GET.get("value", "").strip()
    parent = request.GET.get("parent", "")
    res = None
    if kind == "product":
        obj, _ = Product.objects.get_or_create(name=value)
        res = {"id": obj.id, "display": obj.name}
    elif kind == "product_type":
        prod = Product.objects.get(name=parent)
        obj, _ = ProductType.objects.get_or_create(product=prod, type_name=value)
        res = {"id": obj.id, "display": obj.type_name}
    elif kind == "grade":
        prod_type = ProductType.objects.get(type_name=parent)
        obj, _ = ProductGrade.objects.get_or_create(product_type=prod_type, grade=value)
        res = {"id": obj.id, "display": obj.grade}
    return JsonResponse(res)

def dashboard(request):
    today = timezone.now().date()
    labels = []
    sales_data = []

    # Last 12 months sales total (AED)
    for i in range(11, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        total_sales = SaleInvoice.objects.filter(
            sale_date__gte=month_start,
            sale_date__lt=next_month
        ).aggregate(total=Sum('total_with_vat_aed'))['total'] or 0
        labels.append(month_start.strftime('%b %Y'))
        sales_data.append(float(total_sales))

    total_sales = sum(sales_data)

    # Aggregate total purchases from PurchaseInvoice instead of Purchase
    total_purchases = PurchaseInvoice.objects.aggregate(
        tot=Sum('total_with_vat_aed')
    )['tot'] or 0

    profit = total_sales - float(total_purchases)

    context = {
        'labels': labels,
        'sales_data': sales_data,
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'profit': profit,
    }
    return render(request, 'erp/dashboard.html', context)



def product_item_delete(request, pk):
    item = get_object_or_404(ProductItem, pk=pk)
    item.delete()
    return redirect('product-list')


def purchase_invoice_add(request):
    if request.method == 'POST':
        invoice_no = request.POST.get('invoice_no', '').strip()
        purchase_date_str = request.POST.get('purchase_date')
        supplier = request.POST.get('supplier', '').strip()
        notes = request.POST.get('notes', '').strip()
        purchase_date = timezone.now().date()
        if purchase_date_str:
            try:
                purchase_date = timezone.datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
            except Exception:
                pass
        invoice = PurchaseInvoice.objects.create(
            invoice_no=invoice_no,
            supplier=supplier,
            purchase_date=purchase_date,
            notes=notes
        )

        total = int(request.POST.get('form-TOTAL_FORMS', 1))
        for i in range(total):
            item_id = request.POST.get(f'form-{i}-item')
            qty = request.POST.get(f'form-{i}-qty')
            unit_price_usd = request.POST.get(f'form-{i}-unit_price_usd')
            unit_price_aed = request.POST.get(f'form-{i}-unit_price_aed')
            shipping_usd = request.POST.get(f'form-{i}-shipping_per_unit_usd', '0')
            shipping_aed = request.POST.get(f'form-{i}-shipping_per_unit_aed', '0')
            factors = request.POST.get(f'form-{i}-factors', '')
            if not (item_id and qty and unit_price_usd and unit_price_aed):
                continue
            try:
                qty = int(qty)
                unit_price_usd = Decimal(unit_price_usd)
                unit_price_aed = Decimal(unit_price_aed)
                shipping_usd = Decimal(shipping_usd)
                shipping_aed = Decimal(shipping_aed)
            except (ValueError, ArithmeticError):
                continue

            PurchaseItem.objects.create(
                invoice=invoice,
                item_id=item_id,
                qty=qty,
                unit_price_usd=unit_price_usd,
                unit_price_aed=unit_price_aed,
                shipping_per_unit_usd=shipping_usd,
                shipping_per_unit_aed=shipping_aed,
                factors=factors,
            )
        invoice.calculate_totals()
        return redirect('purchase-report')

    items = ProductItem.objects.all()
    today = timezone.now().date()
    return render(request, 'erp/purchase_invoice_add.html', {'items': items, 'today': today})


def expense_add(request):
    if request.method == 'POST':
        total = int(request.POST.get('form-TOTAL_FORMS', 1))
        for i in range(total):
            type_id = request.POST.get(f'form-{i}-type')
            amount_aed = request.POST.get(f'form-{i}-amount_aed')
            amount_usd = request.POST.get(f'form-{i}-amount_usd')
            date = request.POST.get(f'form-{i}-date')
            notes = request.POST.get(f'form-{i}-notes', '')
            if not (type_id and amount_aed and amount_usd and date):
                continue
            try:
                amount_aed = Decimal(amount_aed)
                amount_usd = Decimal(amount_usd)
            except Exception:
                continue
            Expense.objects.create(
                type_id=type_id,
                amount_aed=amount_aed,
                amount_usd=amount_usd,
                date=date,
                notes=notes
            )
        return redirect('expense-list')
    types = ExpenseType.objects.all()
    return render(request, 'erp/expense_add.html', {'types': types, 'today': timezone.now().date()})


def expense_list(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    expenses = Expense.objects.select_related('type').order_by('-date')
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            expenses = expenses.filter(date__gte=start, date__lt=end +
            timedelta(days=1))
            print(expenses)
        except Exception as e:
            print(e)
            pass

    return render(request, 'erp/expense_list.html', {
        'expenses': expenses,
        'start_date': start_date or '',
        'end_date': end_date or '',
    })


def salary_add(request):
    if request.method == 'POST':
        total = int(request.POST.get('form-TOTAL_FORMS', 1))
        for i in range(total):
            account_id = request.POST.get(f'form-{i}-account')
            amount_aed = request.POST.get(f'form-{i}-amount_aed')
            amount_usd = request.POST.get(f'form-{i}-amount_usd')
            entry_type = request.POST.get(f'form-{i}-entry_type')
            date = request.POST.get(f'form-{i}-date')
            notes = request.POST.get(f'form-{i}-notes', '')
            print(amount_usd, amount_aed)
            if not (account_id and amount_aed and amount_usd and entry_type and date):
                continue

            try:
                amount_aed = Decimal(amount_aed)
                amount_usd = Decimal(amount_usd)
            except Exception:
                continue

            SalaryEntry.objects.create(
                account_id=account_id,
                amount_aed=amount_aed,
                amount_usd=amount_usd,
                entry_type=entry_type,
                date=date,
                notes=notes,
            )
        return redirect('salary-list')
    accounts = Account.objects.all()
    return render(request, 'erp/salary_add.html', {'accounts': accounts})


def salary_list(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    entries = SalaryEntry.objects.select_related('account').order_by('-date')

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            entries = entries.filter(date__gte=start, date__lt=end + timedelta(days=1))
        except Exception:
            pass  # Ignore filter errors, show unfiltered

    context = {
        'entries': entries,
        'start_date': start_date or '',
        'end_date': end_date or '',
    }
    return render(request, 'erp/salary_list.html', context)







