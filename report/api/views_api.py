from rest_framework.views import APIView
from django.db.models import Sum
from decimal import Decimal
from rest_framework.response import Response
from rest_framework import permissions
from base.api.pagination import CustomPagination
from collections import defaultdict
from django.db.models import Q
from products.api.serializers import ProductItemSerializer
from products.models import ProductItem
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem
from common.models import Expense
from employee.models import SalaryEntry
from inventory.models import Stock


class InventoryReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        items = ProductItem.objects.all().order_by('-stock__last_updated')

        result = []
        for item in items:
            # Use correct field name for Stock model
            stock_obj = Stock.objects.filter(product_item=item).first()
            stock = stock_obj.quantity if stock_obj else 0

            purchased = PurchaseItem.objects.filter(item=item, invoice__status=PurchaseInvoice.STATUS_APPROVED).aggregate(total=Sum('qty'))['total'] or 0
            sold = SaleItem.objects.filter(item=item, invoice__status=SaleInvoice.STATUS_APPROVED).aggregate(total=Sum('qty'))['total'] or 0

            result.append({
                'item': ProductItemSerializer(item).data,
                'purchased': purchased,
                'sold': sold,
                'stock': stock,
            })

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(result, request)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(result)



class PurchaseSalesReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # --- Parse date filters from query params ---
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        purchase_filters = {}
        sales_filters = {}

        if start_date:
            purchase_filters['purchase_date__gte'] = start_date
            sales_filters['sale_date__gte'] = start_date
        if end_date:
            purchase_filters['purchase_date__lte'] = end_date
            sales_filters['sale_date__lte'] = end_date

        # PURCHASES
        purchase_invoices = PurchaseInvoice.objects.filter(
            status=PurchaseInvoice.STATUS_APPROVED, **purchase_filters)
        total_purchase_with_vat_usd = purchase_invoices.aggregate(total=Sum('total_with_vat_usd'))['total'] or Decimal('0')
        total_purchase_with_vat_aed = purchase_invoices.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
        total_purchase_vat_usd = purchase_invoices.aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
        total_purchase_vat_aed = purchase_invoices.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
        total_purchase_without_vat_usd = total_purchase_with_vat_usd - total_purchase_vat_usd
        total_purchase_without_vat_aed = total_purchase_with_vat_aed - total_purchase_vat_aed

        total_purchase_discount_usd = \
        purchase_invoices.aggregate(total=Sum('discount_usd'))[
            'total'] or Decimal('0')
        total_purchase_discount_aed = \
        purchase_invoices.aggregate(total=Sum('discount_aed'))[
            'total'] or Decimal('0')

        purchase_ids = list(purchase_invoices.values_list('id', flat=True))
        purchase_shipping_usd = PurchaseItem.objects.filter(invoice_id__in=purchase_ids).aggregate(
            total=Sum('shipping_per_unit_usd'))['total'] or Decimal('0')
        purchase_shipping_aed = PurchaseItem.objects.filter(invoice_id__in=purchase_ids).aggregate(
            total=Sum('shipping_per_unit_aed'))['total'] or Decimal('0')


        # SALES
        sales_invoices = SaleInvoice.objects.filter(
            status=SaleInvoice.STATUS_APPROVED, **sales_filters)
        total_sales_with_vat_usd = sales_invoices.aggregate(total=Sum('total_with_vat_usd'))['total'] or Decimal('0')
        total_sales_with_vat_aed = sales_invoices.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
        total_sales_vat_usd = sales_invoices.aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
        total_sales_vat_aed = sales_invoices.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
        total_sales_without_vat_usd = total_sales_with_vat_usd - total_sales_vat_usd
        total_sales_without_vat_aed = total_sales_with_vat_aed - total_sales_vat_aed

        sales_ids = list(sales_invoices.values_list('id', flat=True))
        sales_shipping_usd = SaleItem.objects.filter(invoice_id__in=sales_ids).aggregate(
            total=Sum('shipping_usd'))['total'] or Decimal('0')
        sales_shipping_aed = SaleItem.objects.filter(invoice_id__in=sales_ids).aggregate(
            total=Sum('shipping_aed'))['total'] or Decimal('0')

        total_sales_discount_usd = sales_invoices.aggregate(total=Sum('discount_usd'))['total'] or Decimal('0')
        total_sales_discount_aed = sales_invoices.aggregate(total=Sum('discount_aed'))['total'] or Decimal('0')

        # EXPENSES & SALARY (filtering by date if present)
        expense_filters = {}
        salary_filters = {}
        if start_date:
            expense_filters['date__gte'] = start_date
            salary_filters['date__gte'] = start_date
        if end_date:
            expense_filters['date__lte'] = end_date
            salary_filters['date__lte'] = end_date

        total_expense_usd = Expense.objects.filter(**expense_filters).aggregate(total=Sum('amount_usd'))['total'] or Decimal('0')
        total_expense_aed = Expense.objects.filter(**expense_filters).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')
        total_salary_usd = SalaryEntry.objects.filter(**salary_filters).aggregate(total=Sum('amount_usd'))['total'] or Decimal('0')
        total_salary_aed = SalaryEntry.objects.filter(**salary_filters).aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')
        all_expenses_usd = total_expense_usd + total_salary_usd
        all_expenses_aed = total_expense_aed + total_salary_aed

        report = {
            "purchase": {
                "total_with_vat_usd": float(total_purchase_with_vat_usd),
                "total_with_vat_aed": float(total_purchase_with_vat_aed),
                "total_without_vat_usd": float(total_purchase_without_vat_usd),
                "total_without_vat_aed": float(total_purchase_without_vat_aed),
                "vat_usd": float(total_purchase_vat_usd),
                "vat_aed": float(total_purchase_vat_aed),
                "total_shipping_usd": float(purchase_shipping_usd),
                "total_shipping_aed": float(purchase_shipping_aed),
                "total_discount_usd": float(total_purchase_discount_usd),
                "total_discount_aed": float(total_purchase_discount_aed),

            },
            "sales": {
                "total_with_vat_usd": float(total_sales_with_vat_usd),
                "total_with_vat_aed": float(total_sales_with_vat_aed),
                "total_without_vat_usd": float(total_sales_without_vat_usd),
                "total_without_vat_aed": float(total_sales_without_vat_aed),
                "vat_usd": float(total_sales_vat_usd),
                "vat_aed": float(total_sales_vat_aed),
                "total_shipping_usd": float(sales_shipping_usd),
                "total_shipping_aed": float(sales_shipping_aed),
                "total_discount_usd": float(total_sales_discount_usd),
                "total_discount_aed": float(total_sales_discount_aed),
            },
            "expenses": {
                "total_expense_usd": float(total_expense_usd),
                "total_expense_aed": float(total_expense_aed),
                "total_salary_usd": float(total_salary_usd),
                "total_salary_aed": float(total_salary_aed),
                "all_expenses_usd": float(all_expenses_usd),
                "all_expenses_aed": float(all_expenses_aed),
            }
        }
        return Response(report)


class ProductBatchSalesReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        products = ProductItem.objects.all()
        report = []

        for product in products:
            purchases = PurchaseItem.objects.filter(item=product,
                                                    invoice__status=PurchaseInvoice.STATUS_APPROVED).order_by(
                'invoice__purchase_date', 'id')
            sales = SaleItem.objects.filter(item=product,
                                            invoice__status=SaleInvoice.STATUS_APPROVED).order_by(
                'invoice__sale_date', 'id')

            # Prepare purchase batches with available quantity
            purchase_batches = []
            for p in purchases:
                purchase_batches.append({'batch_id': p.id,
                    'purchase_invoice': p.invoice.invoice_no,
                    'purchase_date': p.invoice.purchase_date, 'qty': p.qty,
                    'unit_price': p.unit_price_usd,
                    # adjust currency as per need
                    'shipping_per_unit': p.shipping_per_unit_usd,
                    # optional include shipment cost
                    'available': p.qty, 'factors': p.factors or '', })

            batch_pointer = 0
            sales_entries_by_batch = defaultdict(list)

            # Iterate over sales and allocate qty FIFO to purchase batches
            for s in sales:
                sale_qty = s.qty
                while sale_qty > 0 and batch_pointer < len(purchase_batches):
                    batch = purchase_batches[batch_pointer]
                    available_qty = batch['available']
                    if available_qty == 0:
                        batch_pointer += 1
                        continue
                    consume_qty = min(sale_qty, available_qty)

                    # Calculate profit = (sale_price - purchase_price) * qty
                    profit = (s.sale_price_usd - batch[
                        'unit_price']) * consume_qty

                    # Save sales mapped data under purchase batch
                    sales_entries_by_batch[batch['batch_id']].append(
                        {'sale_invoice': s.invoice.invoice_no,
                            'sale_date': s.invoice.sale_date,
                            'qty_sold': consume_qty,
                            'sale_price_per_unit': s.sale_price_usd,
                            'total_sale_amount': s.sale_price_usd * consume_qty,
                            'profit': float(profit),
                            'batch_balance_after_sale': available_qty - consume_qty, })

                    batch['available'] -= consume_qty
                    sale_qty -= consume_qty

                    if batch['available'] == 0:
                        batch_pointer += 1

                # If sale_qty >0 here: sales qty more than available purchase - handle as needed

            # Prepare report for each purchase batch
            batch_reports = []
            total_profit = 0
            closing_qty = 0
            for batch in purchase_batches:
                batch_id = batch['batch_id']
                sales_for_batch = sales_entries_by_batch.get(batch_id, [])
                batch_profit = sum(s['profit'] for s in sales_for_batch)
                batch_reports.append(
                    {'purchase_invoice_no': batch['purchase_invoice'],
                        'purchase_date': batch['purchase_date'],
                        'purchase_qty': batch['qty'],
                        'unit_price': float(batch['unit_price']),
                        'shipping_per_unit': float(
                            batch.get('shipping_per_unit', 0)),
                        'factors': batch['factors'], 'sales': sales_for_batch,
                        'batch_profit': float(batch_profit),
                        'batch_balance': batch['available'], })
                total_profit += batch_profit
                closing_qty += batch['available']

            report.append(
                {'product': str(product), 'batch_reports': batch_reports,
                    'total_profit': float(total_profit),
                    'closing_quantity': closing_qty, })

        return Response(report)


class TaxSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        sale_invoice_filter = Q()
        purchase_invoice_filter = Q()
        sale_item_filter = Q()
        purchase_item_filter = Q()
        expense_filter = Q()
        salary_filter = Q()

        if start_date:
            sale_invoice_filter &= Q(sale_date__gte=start_date)
            purchase_invoice_filter &= Q(purchase_date__gte=start_date)
            sale_item_filter &= Q(invoice__sale_date__gte=start_date)
            purchase_item_filter &= Q(invoice__purchase_date__gte=start_date)
            expense_filter &= Q(date__gte=start_date)
            salary_filter &= Q(date__gte=start_date)
        if end_date:
            sale_invoice_filter &= Q(sale_date__lte=end_date)
            purchase_invoice_filter &= Q(purchase_date__lte=end_date)
            sale_item_filter &= Q(invoice__sale_date__lte=end_date)
            purchase_item_filter &= Q(invoice__purchase_date__lte=end_date)
            expense_filter &= Q(date__lte=end_date)
            salary_filter &= Q(date__lte=end_date)

        # VAT aggregation
        total_sales_vat_usd = \
        SaleInvoice.objects.filter(status=SaleInvoice.STATUS_APPROVED).filter(
            sale_invoice_filter).aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
        total_sales_vat_aed = SaleInvoice.objects.filter(sale_invoice_filter).aggregate(
            total=Sum('vat_amount_aed'))['total'] or Decimal('0')

        total_purchase_vat_usd = PurchaseInvoice.objects.filter(
            status=PurchaseInvoice.STATUS_APPROVED).filter(
            purchase_invoice_filter).aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
        total_purchase_vat_aed = PurchaseInvoice.objects.filter(purchase_invoice_filter).aggregate(
            total=Sum('vat_amount_aed'))['total'] or Decimal('0')

        # Sales base amount (qty * price + shipping), carefully cast to Decimal
        sales_items = SaleItem.objects.filter(
            invoice__status=SaleInvoice.STATUS_APPROVED).filter(
            sale_item_filter)
        total_sales_base_usd = sum(
            (Decimal(item.sale_price_usd) * item.qty) + Decimal(item.shipping_usd)
            for item in sales_items
        )
        total_sales_base_aed = sum(
            (Decimal(item.sale_price_aed) * item.qty) + Decimal(item.shipping_aed)
            for item in sales_items
        )

        # Purchase base amount (qty * price + shipping)
        purchase_items = PurchaseItem.objects.filter(
            invoice__status=PurchaseInvoice.STATUS_APPROVED).filter(
            purchase_item_filter)
        total_purchase_base_usd = sum(
            (Decimal(item.unit_price_usd) * item.qty) + (Decimal(item.shipping_per_unit_usd) * item.qty)
            for item in purchase_items
        )
        total_purchase_base_aed = sum(
            (Decimal(item.unit_price_aed) * item.qty) + (Decimal(item.shipping_per_unit_aed) * item.qty)
            for item in purchase_items
        )

        # Expenses & Salary
        total_expenses_usd = Expense.objects.filter(expense_filter).aggregate(
            total=Sum('amount_usd'))['total'] or Decimal('0')
        total_expenses_aed = Expense.objects.filter(expense_filter).aggregate(
            total=Sum('amount_aed'))['total'] or Decimal('0')

        total_salary_usd = SalaryEntry.objects.filter(salary_filter).aggregate(
            total=Sum('amount_usd'))['total'] or Decimal('0')
        total_salary_aed = SalaryEntry.objects.filter(salary_filter).aggregate(
            total=Sum('amount_aed'))['total'] or Decimal('0')

        # Corporate tax calculation (Decimal math)
        corporate_tax_usd = total_sales_base_usd - (
            total_purchase_base_usd + total_expenses_usd + total_salary_usd
        )
        corporate_tax_aed = total_sales_base_aed - (
            total_purchase_base_aed + total_expenses_aed + total_salary_aed
        )

        # Build response, convert Decimals to float for JSON
        data = {
            "sales": {
                "total_vat_usd": float(total_sales_vat_usd),
                "total_vat_aed": float(total_sales_vat_aed),
            },
            "purchase": {
                "total_vat_usd": float(total_purchase_vat_usd),
                "total_vat_aed": float(total_purchase_vat_aed),
            },
            "corporate_tax": {
                "usd": float(corporate_tax_usd),
                "aed": float(corporate_tax_aed),
            }
        }
        return Response(data)
