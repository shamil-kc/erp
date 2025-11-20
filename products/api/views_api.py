from rest_framework import viewsets, status
from rest_framework.views import APIView
from django.forms.models import model_to_dict
from .serializers import *
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import permissions
from base.utils import log_activity
from sale.models import SaleInvoice
from purchase.models import PurchaseInvoice, PurchaseItem
from common.models import ServiceFee, Tax, Expense
from employee.models import SalaryEntry
from .filters import ProductItemFilter

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
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
    queryset = ProductType.objects.all().order_by('-created_at')
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
    queryset = ProductGrade.objects.all().order_by('-created_at')
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
    queryset = ProductItem.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = ProductItemFilter

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

    def list(self, request, *args, **kwargs):
        search_query = request.query_params.get('search')
        if search_query:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='purchase-info')
    def full_info(self, request):
        """
        Returns all product items (only once), each with all approved purchase items and invoice data,
        only for products with stock > 0.
        If 'product_id' is passed as a query param, returns only that product's purchase item, invoice info, and stock.
        """
        product_id = request.query_params.get('product_id')
        items = ProductItem.objects.all()
        if product_id:
            items = items.filter(id=product_id)
            for item in items:
                stock = getattr(item, 'stock', None)
                if stock and stock.quantity > 0:
                    purchase_items = PurchaseItem.objects.filter(
                        item=item
                    )
                    purchases = []
                    for p_item in purchase_items:
                        if p_item.qty == p_item.sold_qty:
                            continue
                        purchases.append({
                            'purchase_item': {
                                'id': p_item.id,
                                'product_id' : p_item.item.id,
                                'qty': p_item.qty,
                                'sold_qty': p_item.sold_qty,
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
                                'supplier': p_item.invoice.party.id,
                                'purchase_date': p_item.invoice.purchase_date,
                                'status': p_item.invoice.status,
                            } if p_item.invoice else None
                        })
                    # Only return purchase item, invoice details, and stock
                    return Response({
                        'stock': stock.quantity,
                        'purchases': purchases
                    })
            return Response({'stock': None, 'purchases': []})
        for item in items:
            stock = getattr(item, 'stock', None)
            if stock and stock.quantity > 0:
                purchase_items = PurchaseItem.objects.filter(item=item,
                    invoice__status=PurchaseInvoice.STATUS_APPROVED)
                purchases = []
                for p_item in purchase_items:
                    if p_item.qty == p_item.sold_qty:
                        continue
                    purchases.append({
                        'purchase_item': {
                            'id': p_item.id,
                            'product_id': p_item.item.id,
                            'qty': p_item.qty,
                            'sold_qty': p_item.sold_qty,
                            'unit_price_usd': p_item.unit_price_usd,
                            'unit_price_aed': p_item.unit_price_aed,
                            'shipping_per_unit_usd': p_item.shipping_per_unit_usd,
                            'shipping_per_unit_aed': p_item.shipping_per_unit_aed,
                            'factors': p_item.factors, 'tax': p_item.tax_id, },
                        'purchase_invoice': {'id': p_item.invoice.id,
                            'invoice_no': p_item.invoice.invoice_no,
                            'supplier': p_item.invoice.party.id,
                            'purchase_date': p_item.invoice.purchase_date,
                            'status': p_item.invoice.status, }})
                # Only return purchase item, invoice details, and stock
                return Response(
                    {'stock': stock.quantity, 'purchases': purchases})
        return Response({'stock': None, 'purchases': []})


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
