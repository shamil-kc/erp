from rest_framework import viewsets
from django.forms.models import model_to_dict
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from .filters import PurchaseInvoiceFilter, PurchaseItemFilter, PurchaseReturnItemFilter
from django.db import transaction
from rest_framework import permissions
from base.utils import log_activity
from purchase.models import PurchaseReturnItem
from purchase.api.serializers import PurchaseReturnItemSerializer
from inventory.models import Stock
from rest_framework.decorators import action
from rest_framework.response import Response
from common.models import ExtraPurchase
from purchase.api.serializers import ExtraPurchaseSerializer
from django.db.models import Sum


class PurchaseInvoiceViewSet(viewsets.ModelViewSet):
    queryset = PurchaseInvoice.objects.all().order_by('-modified_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PurchaseInvoiceFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PurchaseInvoiceUpdateSerializer
        return PurchaseInvoiceSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        with transaction.atomic():
            old_instance = self.get_object()
            old_status = old_instance.status
            instance = serializer.save(modified_by=self.request.user, modified_at=timezone.now())


    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PurchaseInvoiceUpdateSerializer
        return PurchaseInvoiceSerializer

    @action(detail=False, methods=['get'], url_path='totals')
    def totals(self, request):
        """
        Returns total amounts (AED & USD) for filtered purchase invoices.
        """
        queryset = self.filter_queryset(self.get_queryset())
        total_aed = queryset.aggregate(total=Sum('total_with_vat_aed'))['total'] or 0
        total_usd = queryset.aggregate(total=Sum('total_with_vat_usd'))['total'] or 0
        return Response({
            "total_aed": float(total_aed),
            "total_usd": float(total_usd)
        })


class PurchaseItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PurchaseItemFilter

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

    @action(detail=False, methods=['post'], url_path='stock-info')
    def get_stock_info(self, request):
        purchase_item_ids = request.data.get('purchase_item_ids', [])

        if not isinstance(purchase_item_ids, list) or not purchase_item_ids:
            return Response({'error': 'purchase_item_ids (list) is required'}, status=400)

        purchase_items = PurchaseItem.objects.filter(id__in=purchase_item_ids).select_related('item', 'item__stock')

        if not purchase_items.exists():
            return Response({'error': 'No purchase items found for the provided IDs'}, status=404)

        stock_info = []
        for purchase_item in purchase_items:
            try:
                stock = Stock.objects.get(product_item=purchase_item.item)
                current_stock = stock.quantity
            except Stock.DoesNotExist:
                current_stock = 0

            # Calculate remaining_qty for this purchase item
            # If you have a field or logic for remaining_qty, use it here.
            # For now, assuming remaining_qty = purchase_item.qty - sum of related sale quantities (if applicable)
            # If not tracked, just return purchase_item.qty

            stock_data = {
                'purchase_item_id': purchase_item.id,
                'product_item': {
                    'product_id': purchase_item.item.id,
                    'name': str(purchase_item.item),
                },
                'current_stock': current_stock,
                'purchase_item_qty': purchase_item.qty,
                'remaining_qty': purchase_item.remaining_qty
            }
            stock_info.append(stock_data)

        return Response({
            'stock_info': stock_info,
            'total_items': len(stock_info)
        })


class PurchaseReturnItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseReturnItem.objects.all().order_by('-return_date')
    serializer_class = PurchaseReturnItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PurchaseReturnItemFilter

    def perform_create(self, serializer):
        serializer.save(returned_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class ExtraPurchaseViewSet(viewsets.ModelViewSet):
    queryset = ExtraPurchase.objects.all()
    serializer_class = ExtraPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]
