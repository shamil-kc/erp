from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from django.utils import timezone
from base.models import *
from base.models import UserActivity, PaymentEntry
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from .serializers import *
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from .filters import PurchaseInvoiceFilter, SaleInvoiceFilter, PaymentEntryFilter
from decimal import Decimal
from datetime import date
from django.db import transaction
from rest_framework.decorators import action

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import generics, permissions
from django.contrib.auth.models import User
from base.api.pagination import CustomPagination
from collections import defaultdict
from django.db.models import Q
from base.utils import log_activity


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        roles = list(user.groups.values_list('name', flat=True))  # example with Groups as roles
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'roles': roles
        })


class UserCreateAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]  # or restrict as needed



class IsAdminUser(permissions.BasePermission):
    """Allow only admin users (is_staff=True)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsEmployeeUser(permissions.BasePermission):
    """Allow only employee users (is_staff=False)."""
    def has_permission(self, request, view):
        return request.user and not request.user.is_staff

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())

    def create(self, request, *args, **kwargs):
        product_name = request.data.get('name', '').strip()
        if Product.objects.filter(name__iexact=product_name).exists():
            return Response({
                "detail": f"Product with name '{product_name}' already exists."},
                status=status.HTTP_409_CONFLICT)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        product_name = request.data.get('name', '').strip()
        product_id = self.get_object().id
        if Product.objects.filter(name__iexact=product_name).exclude(
                id=product_id).exists():
            return Response({
                "detail": f"Product with name '{product_name}' already exists."},
                status=status.HTTP_409_CONFLICT)
        return super().update(request, *args, **kwargs)

class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        type_name = request.data.get('type_name', '').strip()
        if product_id and type_name:
            exists = ProductType.objects.filter(
                product_id=product_id,
                type_name__iexact=type_name
            ).exists()
            if exists:
                return Response(
                    {"detail": f"ProductType with product ID {product_id} and type '{type_name}' already exists."},
                    status=status.HTTP_409_CONFLICT
                )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        type_name = request.data.get('type_name', '').strip()
        pt_id = self.get_object().id
        if product_id and type_name:
            exists = ProductType.objects.filter(product_id=product_id,
                type_name__iexact=type_name).exclude(id=pt_id).exists()
            if exists:
                return Response({
                    "detail": f"ProductType with product ID {product_id} and type '{type_name}' already exists."},
                    status=status.HTTP_409_CONFLICT)
        return super().update(request, *args, **kwargs)

class ProductGradeViewSet(viewsets.ModelViewSet):
    queryset = ProductGrade.objects.all()
    serializer_class = ProductGradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        if type(instance) in [PurchaseInvoice, SaleInvoice, ServiceFee, Tax,
                              Expense, SalaryEntry]:
            log_activity(self.request.user, 'CREATE',
                instance._meta.verbose_name, str(instance))

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())

    def create(self, request, *args, **kwargs):
        product_type_id = request.data.get('product_type')
        grade = request.data.get('grade', '').strip()
        if product_type_id and grade:
            exists = ProductGrade.objects.filter(
                product_type_id=product_type_id,
                grade__iexact=grade
            ).exists()
            if exists:
                return Response(
                    {"detail": f"ProductGrade with product_type ID {product_type_id} and grade '{grade}' already exists."},
                    status=status.HTTP_409_CONFLICT
                )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        product_type_id = request.data.get('product_type')
        grade = request.data.get('grade', '').strip()
        pg_id = self.get_object().id
        if product_type_id and grade:
            exists = ProductGrade.objects.filter(
                product_type_id=product_type_id, grade__iexact=grade).exclude(
                id=pg_id).exists()
            if exists:
                return Response({
                    "detail": f"ProductGrade with product_type ID {product_type_id} and grade '{grade}' already exists."},
                    status=status.HTTP_409_CONFLICT)
        return super().update(request, *args, **kwargs)

class ProductItemViewSet(viewsets.ModelViewSet):
    queryset = ProductItem.objects.all()
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

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ProductItemUpdateSerializer
        return ProductItemSerializer


    @action(detail=False, methods=['get'], url_path='purchase-info')
    def full_info(self, request):
        """
        Returns all product items, each with purchase item and invoice data
        only for products with stock > 0.
        """
        items = ProductItem.objects.all()
        result = []
        for item in items:
            stock = getattr(item, 'stock', None)
            if stock and stock.quantity > 0:
                purchase_items = PurchaseItem.objects.filter(item=item)
                for p_item in purchase_items:
                    result.append({
                        'product_item': ProductItemSerializer(item).data,
                        'stock': stock.quantity,
                        'purchase_item': {
                            'id': p_item.id,
                            'qty': p_item.qty,
                            'unit_price_usd': p_item.unit_price_usd,
                            'unit_price_aed': p_item.unit_price_aed,
                            'shipping_per_unit_usd': p_item.shipping_per_unit_usd,
                            'shipping_per_unit_aed': p_item.shipping_per_unit_aed,
                            'factors': p_item.factors,
                            'tax': p_item.tax_id,
                        },
                        'purchase_invoice': {
                            'id': p_item.invoice.id,
                            'invoice_no': p_item.invoice.invoice_no,
                            'supplier': p_item.invoice.supplier,
                            'purchase_date': p_item.invoice.purchase_date,
                            'status': p_item.invoice.status,
                        }
                    })
        return Response(result)


class ProductItemBulkCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ProductItemBulkCreateSerializer(data=request.data)
        if serializer.is_valid():
            created_items = serializer.save()
            return Response({
                "created_count": len(created_items)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseInvoiceViewSet(viewsets.ModelViewSet):
    queryset = PurchaseInvoice.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PurchaseInvoiceFilter

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(created_by=self.request.user)
            if instance.status == PurchaseInvoice.STATUS_APPROVED:
                cash_account = CashAccount.objects.first()
                payment_entries = PaymentEntry.objects.filter(
                    invoice_id=instance.id, invoice_type='purchase')
                for entry in payment_entries:
                    cash_account.withdraw(entry.amount, f"cash_in_{entry.payment_type}")

    def perform_update(self, serializer):
        with transaction.atomic():
            old_instance = self.get_object()
            old_status = old_instance.status
            instance = serializer.save(modified_by=self.request.user, modified_at=timezone.now())

            if old_status != PurchaseInvoice.STATUS_APPROVED and instance.status == PurchaseInvoice.STATUS_APPROVED:
                cash_account = CashAccount.objects.first()
                payment_entries = PaymentEntry.objects.filter(
                    invoice_id=instance.id, invoice_type='sale')
                for entry in payment_entries:
                    cash_account.withdraw(entry.amount,
                                          f"cash_in_{entry.payment_type}")

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PurchaseInvoiceUpdateSerializer
        return PurchaseInvoiceSerializer



class PurchaseItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseItem.objects.all()
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

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return PurchaseItemUpdateSerializer
        return PurchaseItemSerializer


class SaleInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SaleInvoice.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SaleInvoiceFilter

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(created_by=self.request.user)
            if instance.status == SaleInvoice.STATUS_APPROVED:
                cash_account = CashAccount.objects.first()
                payment_entries = PaymentEntry.objects.filter(
                    invoice_id=instance.id, invoice_type='sale')
                for entry in payment_entries:
                    cash_account.withdraw(entry.amount,
                                          f"cash_in_{entry.payment_type}")


    def perform_update(self, serializer):
        def convert_decimal(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return obj

        with transaction.atomic():
            old_instance = self.get_object()
            old_status = old_instance.status

            old_data = {k: convert_decimal(v) for k, v in
                        model_to_dict(old_instance).items()}
            instance = serializer.save(modified_by=self.request.user,
                                       modified_at=timezone.now())
            new_data = {k: convert_decimal(v) for k, v in
                        model_to_dict(instance).items()}
            changes = {k: {'old': old_data[k], 'new': v} for k, v in
                       new_data.items() if old_data[k] != v}
            if old_status != SaleInvoice.STATUS_APPROVED and instance.status == SaleInvoice.STATUS_APPROVED:
                cash_account = CashAccount.objects.first()
                payment_entries = PaymentEntry.objects.filter(
                    invoice_id=instance.id, invoice_type='sale')
                for entry in payment_entries:
                    cash_account.withdraw(entry.amount,
                                          f"cash_in_{entry.payment_type}")
            log_activity(self.request, 'update', instance, changes)

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SaleInvoiceUpdateSerializer
        return SaleInvoiceSerializer  # your existing read serializer


class SaleItemViewSet(viewsets.ModelViewSet):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.all()
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
    queryset = ExpenseType.objects.all()
    serializer_class = ExpenseTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        cash_account = CashAccount.objects.first()
        cash_account.withdraw(instance.amount_aed, CashAccount.ACCOUNT_TYPE_CASH)
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = model_to_dict(old_instance)
        instance = serializer.save(modified_by=self.request.user,
                                   modified_at=timezone.now())
        new_data = model_to_dict(instance)
        changes = {k: {'old': old_data[k], 'new': v} for k, v in
                   new_data.items() if old_data[k] != v}
        log_activity(self.request, 'update', instance, changes)


class SalaryEntryViewSet(viewsets.ModelViewSet):
    queryset = SalaryEntry.objects.all()
    serializer_class = SalaryEntrySerializer
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

        # No cash logic on update (only on create)
class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class InventoryReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        items = ProductItem.objects.all()

        purchased_qty_data = dict(
            PurchaseItem.objects.values_list('item_id')
            .annotate(s=Sum('qty')).values_list('item_id', 's')
        )
        sold_qty_data = dict(
            SaleItem.objects.values_list('item_id')
            .annotate(s=Sum('qty')).values_list('item_id', 's')
        )

        # Calculate stock data list
        result = []
        for item in items:
            purchased = purchased_qty_data.get(item.id, 0)
            sold = sold_qty_data.get(item.id, 0)
            stock = purchased - sold
            result.append({
                'item': ProductItemSerializer(item).data,
                'purchased': purchased,
                'sold': sold,
                'stock': stock,
            })

        # Paginate result list
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(result, request)
        if page is not None:
            return paginator.get_paginated_response(page)

        # If no pagination applied, return full list
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


class ServiceFeeViewSet(viewsets.ModelViewSet):
    queryset = ServiceFee.objects.all()
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


class PaymentEntryViewSet(viewsets.ModelViewSet):
    queryset = PaymentEntry.objects.all()
    serializer_class = PaymentEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentEntryFilter

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())

class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())
