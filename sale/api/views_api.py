from rest_framework import viewsets
from django.forms.models import model_to_dict
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from .filters import SaleInvoiceFilter, SaleReturnItemFilter
from decimal import Decimal
from django.db import transaction
from rest_framework import permissions
from base.utils import log_activity
from sale.api.serializers import SaleReturnItemSerializer, DeliveryNoteSerializer
from sale.models import SaleReturnItem, DeliveryNote, SaleInvoice
from rest_framework.decorators import action
from rest_framework.response import Response
from inventory.models import Stock
from django.utils import timezone
from rest_framework.decorators import api_view
from sale.utils import generate_perfoma_invoice_number
from django.db.models import Sum


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
        with transaction.atomic():
            old_instance = self.get_object()
            old_data = model_to_dict(old_instance)

            instance = serializer.save(modified_by=self.request.user, modified_at=timezone.now())

            new_data = model_to_dict(instance)

            # Create changes dict with proper handling of non-serializable fields
            changes = {}
            for k, v in new_data.items():
                if k in old_data and old_data[k] != v:
                    changes[k] = {
                        'old': old_data[k],
                        'new': v
                    }

            log_activity(self.request, 'update', instance, changes)

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleInvoiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SaleInvoiceUpdateSerializer
        return SaleInvoiceSerializer  # your existing read serializer

    @action(detail=False, methods=['get'], url_path='totals')
    def totals(self, request):
        """
        Returns total amounts (AED & USD) for filtered sale invoices.
        """
        queryset = self.filter_queryset(self.get_queryset())
        total_aed = queryset.aggregate(total=Sum('total_with_vat_aed'))['total'] or 0
        total_usd = queryset.aggregate(total=Sum('total_with_vat_usd'))['total'] or 0
        return Response({
            "total_aed": float(total_aed),
            "total_usd": float(total_usd)
        })


class SaleItemViewSet(viewsets.ModelViewSet):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())

    @action(detail=False, methods=['post'], url_path='stock-info')
    def get_stock_info(self, request):
        sale_item_ids = request.data.get('sale_item_ids', [])

        if not isinstance(sale_item_ids, list) or not sale_item_ids:
            return Response({'error': 'sale_item_ids (list) is required'}, status=400)

        # Get sale items with their product items
        sale_items = SaleItem.objects.filter(id__in=sale_item_ids).select_related('item', 'item__stock')

        if not sale_items.exists():
            return Response({'error': 'No sale items found for the provided IDs'}, status=404)

        stock_info = []
        for sale_item in sale_items:
            try:
                stock = Stock.objects.get(product_item=sale_item.item)
                stock_data = {
                    'sale_item_id': sale_item.id,
                    'product_item': {
                        'product_id': sale_item.item.id,
                        'name': str(sale_item.item),
                    },
                    'current_stock': stock.quantity,
                    'sale_item_qty': sale_item.qty,
                }
            except Stock.DoesNotExist:
                stock_data = {
                    'sale_item_id': sale_item.id,
                    'product_item': {
                        'product_id': sale_item.item.id,
                        'name': str(sale_item.item),
                    },
                    'current_stock': 0,
                    'sale_item_qty': sale_item.qty,
                }

            stock_info.append(stock_data)

        return Response({
            'stock_info': stock_info,
            'total_items': len(stock_info)
        })

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
    filter_backends = [DjangoFilterBackend]
    filterset_class = SaleReturnItemFilter

    def perform_create(self, serializer):
        serializer.save(returned_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class DeliveryNoteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryNote.objects.all().order_by('-created_at')
    serializer_class = DeliveryNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def by_invoice_query(self, request):
        """
        Get all delivery notes for a specific sale invoice.
        Usage: /api/delivery-notes/by-invoice-query/?invoice_id={invoice_id}
        """
        invoice_id = request.query_params.get('invoice_id')

        if not invoice_id:
            return Response({'error': 'invoice_id query parameter is required'}, status=400)

        try:
            sale_invoice = SaleInvoice.objects.get(id=invoice_id)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'Sale invoice not found'}, status=404)

        delivery_notes = DeliveryNote.objects.filter(sale_invoice=sale_invoice).order_by('-created_at')
        serializer = self.get_serializer(delivery_notes, many=True)

        return Response({
            'delivery_notes': serializer.data,
            'invoice': {
                'id': sale_invoice.id,
                'invoice_no': sale_invoice.invoice_no,
                'party': sale_invoice.party.name if sale_invoice.party else None
            },
            'total_count': delivery_notes.count()
        })


@api_view(['POST'])
def generate_perfoma_invoice_number_api(request):
    """
    Generate and assign a new perfoma invoice number to a sale invoice.
    Expects: {"sale_invoice_id": <id>}
    """
    sale_invoice_id = request.data.get('sale_invoice_id')
    if not sale_invoice_id:
        return Response({'error': 'sale_invoice_id is required'}, status=400)
    try:
        sale_invoice = SaleInvoice.objects.get(id=sale_invoice_id)
    except SaleInvoice.DoesNotExist:
        return Response({'error': 'Sale invoice not found'}, status=404)

    number = generate_perfoma_invoice_number(sale_invoice)
    return Response({'perfoma_invoice_number': number})
