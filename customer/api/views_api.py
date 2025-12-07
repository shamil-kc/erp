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
from .filters import PartyFilter
from django.db import models


class PartyViewSet(viewsets.ModelViewSet):
    queryset = Party.objects.all().order_by('-created_at')
    serializer_class = PartySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PartyFilter

    @action(detail=True, methods=['get'], url_path='transactions')
    def customer_transactions(self, request, pk=None):
        party = self.get_object()
        sales = SaleInvoice.objects.filter(party=party)
        purchases = PurchaseInvoice.objects.filter(party=party)
        payments = PaymentEntry.objects.filter(party=party)

        # Total sale and purchase count
        total_sale_count = sales.count()
        total_purchase_count = purchases.count()

        # Total sale and purchase amount
        total_sale_amount = sales.aggregate(total=models.Sum('total_with_vat_aed'))['total'] or 0
        total_purchase_amount = purchases.aggregate(total=models.Sum('total_with_vat_aed'))['total'] or 0

        # Payments by type and totals
        payment_types = payments.values_list('payment_type', flat=True).distinct()
        payments_by_type = {}
        total_payments = 0
        for p_type in payment_types:
            type_payments = payments.filter(payment_type=p_type)
            type_total = type_payments.aggregate(total=models.Sum('amount'))['total'] or 0
            payments_by_type[p_type] = {
                'entries': PaymentEntrySerializer(type_payments, many=True).data,
                'total': type_total
            }
            total_payments += type_total

        # Cheque due and paid (fixed field names)
        cheque_payments = payments.filter(payment_type='cheque')
        cheque_due = cheque_payments.filter(is_cheque_cleared=False)
        cheque_paid = cheque_payments.filter(is_cheque_cleared=True)
        cheque_due_total = cheque_due.aggregate(total=models.Sum('amount'))['total'] or 0
        cheque_paid_total = cheque_paid.aggregate(total=models.Sum('amount'))['total'] or 0

        # Balance amount owed by customer
        # Assuming: balance = total_sale_amount - total_payments
        balance_amount = total_sale_amount - total_payments

        return Response({
            'total_sale_count': total_sale_count,
            'total_purchase_count': total_purchase_count,
            'total_sale_amount': total_sale_amount,
            'total_purchase_amount': total_purchase_amount,
            'payments_by_type': payments_by_type,
            'total_payments': total_payments,
            'balance_amount': balance_amount,
            'cheque_due_total': cheque_due_total,
            'cheque_paid_total': cheque_paid_total,
            'cheque_due': PaymentEntrySerializer(cheque_due, many=True).data,
            'cheque_paid': PaymentEntrySerializer(cheque_paid, many=True).data,
        })
