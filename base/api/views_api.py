from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from base.models import *
from .serializers import *

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
    serializer_class = ProductItemSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    serializer_class = SaleInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

class SaleItemViewSet(viewsets.ModelViewSet):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer
    permission_classes = [IsAdminUser] # Only admin can update taxes

class ExpenseTypeViewSet(viewsets.ModelViewSet):
    queryset = ExpenseType.objects.all()
    serializer_class = ExpenseTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAdminUser] # Only admin manage accounts

class SalaryEntryViewSet(viewsets.ModelViewSet):
    queryset = SalaryEntry.objects.all()
    serializer_class = SalaryEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
from rest_framework.views import APIView
from rest_framework.response import Response

class InventoryReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        # Same logic as your Django view, just return JSON
        items = ProductItem.objects.all()
        purchased_qty_data = dict(
            PurchaseItem.objects.values_list('item_id')
            .annotate(s=Sum('qty')).values_list('item_id', 's')
        )
        sold_qty_data = dict(
            SaleItem.objects.values_list('item_id')
            .annotate(s=Sum('qty')).values_list('item_id', 's')
        )
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
        return Response(result)
