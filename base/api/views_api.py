from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from base.models import *
from .serializers import *
from django.db.models import Sum

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import generics, permissions
from django.contrib.auth.models import User
from base.api.pagination import CustomPagination

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

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ProductItemUpdateSerializer
        return ProductItemSerializer

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

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PurchaseInvoiceUpdateSerializer
        return PurchaseInvoiceSerializer



class PurchaseItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return PurchaseItemUpdateSerializer
        return PurchaseItemSerializer


class SaleInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SaleInvoice.objects.all()
    permission_classes = [permissions.IsAuthenticated]

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

class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExpenseTypeViewSet(viewsets.ModelViewSet):
    queryset = ExpenseType.objects.all()
    serializer_class = ExpenseTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

class SalaryEntryViewSet(viewsets.ModelViewSet):
    queryset = SalaryEntry.objects.all()
    serializer_class = SalaryEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    permission_classes = [permissions.IsAuthenticated]


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
        # PURCHASES
        purchase_invoices = PurchaseInvoice.objects.all()
        total_purchase_with_vat_usd = purchase_invoices.aggregate(total=Sum('total_with_vat_usd'))['total'] or Decimal('0')
        total_purchase_with_vat_aed = purchase_invoices.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
        total_purchase_vat_usd = purchase_invoices.aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
        total_purchase_vat_aed = purchase_invoices.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
        total_purchase_without_vat_usd = total_purchase_with_vat_usd - total_purchase_vat_usd
        total_purchase_without_vat_aed = total_purchase_with_vat_aed - total_purchase_vat_aed

        # Sum shipping for all PurchaseItems
        purchase_shipping_usd = PurchaseItem.objects.aggregate(total=Sum('shipping_per_unit_usd'))['total'] or Decimal('0')
        purchase_shipping_aed = PurchaseItem.objects.aggregate(total=Sum('shipping_per_unit_aed'))['total'] or Decimal('0')

        # SALES
        sales_invoices = SaleInvoice.objects.all()
        total_sales_with_vat_usd = sales_invoices.aggregate(total=Sum('total_with_vat_usd'))['total'] or Decimal('0')
        total_sales_with_vat_aed = sales_invoices.aggregate(total=Sum('total_with_vat_aed'))['total'] or Decimal('0')
        total_sales_vat_usd = sales_invoices.aggregate(total=Sum('vat_amount_usd'))['total'] or Decimal('0')
        total_sales_vat_aed = sales_invoices.aggregate(total=Sum('vat_amount_aed'))['total'] or Decimal('0')
        total_sales_without_vat_usd = total_sales_with_vat_usd - total_sales_vat_usd
        total_sales_without_vat_aed = total_sales_with_vat_aed - total_sales_vat_aed

        # Sum shipping for all SaleItems
        sales_shipping_usd = SaleItem.objects.aggregate(total=Sum('shipping_usd'))['total'] or Decimal('0')
        sales_shipping_aed = SaleItem.objects.aggregate(total=Sum('shipping_aed'))['total'] or Decimal('0')

        # SALES Discounts
        total_sales_discount_usd = sales_invoices.aggregate(total=Sum('discount_usd'))['total'] or Decimal('0')
        total_sales_discount_aed = sales_invoices.aggregate(total=Sum('discount_aed'))['total'] or Decimal('0')

        # EXPENSES
        total_expense_usd = Expense.objects.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0')
        total_expense_aed = Expense.objects.aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

        total_salary_usd = SalaryEntry.objects.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0')
        total_salary_aed = SalaryEntry.objects.aggregate(total=Sum('amount_aed'))['total'] or Decimal('0')

        all_expenses_usd = total_expense_usd + total_salary_usd
        all_expenses_aed = total_expense_aed + total_salary_aed

        report = {
            "purchase": {
                "total_with_vat_usd": str(total_purchase_with_vat_usd),
                "total_with_vat_aed": str(total_purchase_with_vat_aed),
                "total_without_vat_usd": str(total_purchase_without_vat_usd),
                "total_without_vat_aed": str(total_purchase_without_vat_aed),
                "vat_usd": str(total_purchase_vat_usd),
                "vat_aed": str(total_purchase_vat_aed),
                "total_shipping_usd": str(purchase_shipping_usd),
                "total_shipping_aed": str(purchase_shipping_aed),
            },
            "sales": {
                "total_with_vat_usd": str(total_sales_with_vat_usd),
                "total_with_vat_aed": str(total_sales_with_vat_aed),
                "total_without_vat_usd": str(total_sales_without_vat_usd),
                "total_without_vat_aed": str(total_sales_without_vat_aed),
                "vat_usd": str(total_sales_vat_usd),
                "vat_aed": str(total_sales_vat_aed),
                "total_shipping_usd": str(sales_shipping_usd),
                "total_shipping_aed": str(sales_shipping_aed),
                "total_discount_usd": str(total_sales_discount_usd),
                "total_discount_aed": str(total_sales_discount_aed),
            },
            "expenses": {
                "total_expense_usd": str(total_expense_usd),
                "total_expense_aed": str(total_expense_aed),
                "total_salary_usd": str(total_salary_usd),
                "total_salary_aed": str(total_salary_aed),
                "all_expenses_usd": str(all_expenses_usd),
                "all_expenses_aed": str(all_expenses_aed),
            }
        }
        return Response(report)


