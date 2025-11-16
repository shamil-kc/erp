from rest_framework import viewsets
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from sale.models import SaleInvoice
from purchase.models import PurchaseInvoice
from banking.models import PaymentEntry
from sale.api.serializers import SaleInvoiceSerializer
from purchase.api.serializers import PurchaseInvoiceSerializer
from banking.api.serializers import PaymentEntrySerializer
from rest_framework.decorators import action
from rest_framework.response import Response


class PartyViewSet(viewsets.ModelViewSet):
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type']

    @action(detail=True, methods=['get'], url_path='transactions')
    def customer_transactions(self, request, pk=None):
        party = self.get_object()
        sales = SaleInvoice.objects.filter(party=party)
        purchases = PurchaseInvoice.objects.filter(party=party)
        payments = PaymentEntry.objects.filter(party=party)

        sales_data = SaleInvoiceSerializer(sales, many=True).data
        purchases_data = PurchaseInvoiceSerializer(purchases, many=True).data
        payments_data = PaymentEntrySerializer(payments, many=True).data

        return Response({
            'sales': sales_data,
            'purchases': purchases_data,
            'payments': payments_data
        })
