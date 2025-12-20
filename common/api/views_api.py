from rest_framework import viewsets, status
from rest_framework.views import APIView
from django.forms.models import model_to_dict
from .serializers import *
from django.db.models import Sum
from decimal import Decimal
from datetime import date
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Q
from base.utils import log_activity
from common.api.serializers import WageSerializer
from django.utils import timezone
from banking.models import CashAccount
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleItem,SaleInvoice
from employee.models import SalaryEntry
from common.api.filters import ExpenseFilter
from django_filters.rest_framework import DjangoFilterBackend


class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.all().order_by('-created_at')
    serializer_class = TaxSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_activity(self.request, 'create', instance)

    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = model_to_dict(old_instance)
        instance = serializer.save(modified_by=self.request.user,
                                   modified_at=timezone.now())
        new_data = model_to_dict(instance)
        changes = {k: {'old': old_data[k], 'new': v} for k, v in
                   new_data.items() if old_data[k] != v}
        log_activity(self.request, 'update', instance, changes)


class ExpenseTypeViewSet(viewsets.ModelViewSet):
    queryset = ExpenseType.objects.all().order_by('-created_at')
    serializer_class = ExpenseTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-created_at')
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExpenseFilter

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        cash_account = CashAccount.objects.first()
        cash_account.withdraw(instance.amount_aed, f'cash_in_{instance.payment_type}')
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = model_to_dict(old_instance)
        instance = serializer.save(modified_by=self.request.user,
                                   modified_at=timezone.now())
        new_data = model_to_dict(instance)
        changes = {k: {'old': old_data[k], 'new': v} for k, v in
                   new_data.items() if old_data[k] != v}
        log_activity(self.request, 'update', instance, changes)



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


class ServiceFeeViewSet(viewsets.ModelViewSet):
    queryset = ServiceFee.objects.all().order_by('-created_at')
    serializer_class = ServiceFeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())

        instance = serializer.save(created_by=self.request.user)
        cash_account = CashAccount.objects.first()
        cash_account.deposit(instance.amount_aed, CashAccount.ACCOUNT_TYPE_CASH)
        log_activity(self.request, 'create', instance)
    def get(self, request):
        """Return all reminders for today that are not shown yet."""
        today = date.today()
        reminders = Expense.objects.filter(
            is_reminder_needed=True,
            reminder_date=today
        )
        serializer = ExpenseSerializer(reminders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Mark a specific reminder as shown (requires 'id' in request body)."""
        expense_id = request.data.get("id")
        if not expense_id:
            return Response({"error": "id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            expense = Expense.objects.get(pk=expense_id)
            expense.is_shown = True
            expense.save()
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Expense.DoesNotExist:
            return Response({"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND)


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.all().order_by('-created_at')
    serializer_class = CommissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class WageViewSet(viewsets.ModelViewSet):
    queryset = Wage.objects.all().order_by('-created_at')
    serializer_class = WageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        cash_account = CashAccount.objects.first()
        cash_account.withdraw(instance.amount_aed, f'cash_in_{instance.payment_type}')
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = model_to_dict(old_instance)
        instance = serializer.save(modified_by=self.request.user,
                                   modified_at=timezone.now())
        new_data = model_to_dict(instance)
        changes = {k: {'old': old_data[k], 'new': v} for k, v in
                   new_data.items() if old_data[k] != v}
        log_activity(self.request, 'update', instance, changes)


class RemindersAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        expense_reminders = Expense.objects.filter(
            is_reminder_needed=True,
            reminder_date=today
        )
        expense_data = ExpenseSerializer(expense_reminders, many=True).data

        # Future: add other reminder types here as needed
        reminders = {
            "expense": expense_data,
        }
        return Response(reminders, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Mark a reminder as shown. Future-compatible: supports 'type' and 'id'.
        Example payload: { "type": "expense", "id": 123 }
        """
        reminder_type = request.data.get("type", "expense")
        reminder_id = request.data.get("id")
        if not reminder_id:
            return Response({"error": "id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if reminder_type == "expense":
            try:
                expense = Expense.objects.get(pk=reminder_id)
                expense.is_shown = True
                expense.save()
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except Expense.DoesNotExist:
                return Response({"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Unsupported reminder type"}, status=status.HTTP_400_BAD_REQUEST)

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all().order_by('-created_at')
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user, modified_at=timezone.now())
