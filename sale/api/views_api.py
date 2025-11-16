from rest_framework import viewsets
from django.forms.models import model_to_dict
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from .filters import SaleInvoiceFilter
from decimal import Decimal
from django.db import transaction
from rest_framework import permissions
from base.utils import log_activity
from sale.api.serializers import SaleReturnItemSerializer
from sale.models import SaleReturnItem, DeliveryNote
from rest_framework.decorators import action
from rest_framework.response import Response


class SaleInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SaleInvoice.objects.all().order_by('-modified_at')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SaleInvoiceFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SaleInvoiceUpdateSerializer
        return SaleInvoiceSerializer  # your existing read serializer

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(created_by=self.request.user)

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

    @action(detail=False, methods=['post'], url_path='set-delivered')
    def delivered(self, request):
        sale_item_ids = request.data.get('sale_item_ids', [])
        sale_invoice_id = request.data.get('sale_invoice_id')
        if not isinstance(sale_item_ids, list) or not sale_invoice_id:
            return Response({'error': 'sale_item_ids (list) and sale_invoice_id are required'}, status=400)

        with transaction.atomic():
            # Update delivery_status for sale items
            updated = SaleItem.objects.filter(id__in=sale_item_ids).update(
                delivery_status=SaleItem.DELIVERY_STATUS_DELIVERED
            )
            # Create DeliveryNote
            sale_invoice = SaleInvoice.objects.get(id=sale_invoice_id)
            delivery_note = DeliveryNote.objects.create(
                sale_invoice=sale_invoice,
                created_by=request.user
            )
            delivery_note.sale_items.set(SaleItem.objects.filter(id__in=sale_item_ids))
            delivery_note.save()

        return Response({
            'status': f'{updated} sale items set to delivered',
            'delivery_note_id': delivery_note.DO_id
        })


class SaleReturnItemViewSet(viewsets.ModelViewSet):
    queryset = SaleReturnItem.objects.all().order_by('-return_date')
    serializer_class = SaleReturnItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(returned_by=self.request.user)
