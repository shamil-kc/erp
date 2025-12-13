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
        date_gte = request.query_params.get('start_date')
        date_lte = request.query_params.get('end_date')

        sales = SaleInvoice.objects.filter(party=party)
        purchases = PurchaseInvoice.objects.filter(party=party)
        payments = PaymentEntry.objects.filter(party=party)

        if date_gte:
            sales = sales.filter(sale_date__gte=date_gte)
            purchases = purchases.filter(purchase_date__gte=date_gte)
            payments = payments.filter(payment_date__gte=date_gte)
        if date_lte:
            sales = sales.filter(sale_date__lte=date_lte)
            purchases = purchases.filter(purchase_date__lte=date_lte)
            payments = payments.filter(payment_date__lte=date_lte)

        # Total sale and purchase count
        total_sale_count = sales.count()
        total_purchase_count = purchases.count()

        # Total sale and purchase amount
        total_sale_amount = sales.aggregate(total=models.Sum('total_with_vat_aed'))['total'] or 0
        total_purchase_amount = purchases.aggregate(total=models.Sum('total_with_vat_aed'))['total'] or 0

        # Payments by type and totals (only totals, no entries)
        payment_types = payments.values_list('payment_type', flat=True).distinct()
        payments_by_type = {}
        total_payments = 0
        for p_type in payment_types:
            type_payments = payments.filter(payment_type=p_type)
            type_total = type_payments.aggregate(total=models.Sum('amount'))['total'] or 0
            payments_by_type[p_type] = type_total
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
            'cheque_paid_total': cheque_paid_total
        })

    @action(detail=True, methods=['get'], url_path='datewise-transactions')
    def datewise_transactions(self, request, pk=None):
        """
        Returns date-wise grouped transactions (sale, purchase, payment) for a customer,
        with running balance tally.
        """
        party = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Get sales
        sales = SaleInvoice.objects.filter(party=party)
        if start_date:
            sales = sales.filter(sale_date__gte=start_date)
        if end_date:
            sales = sales.filter(sale_date__lte=end_date)

        # Get purchases
        purchases = PurchaseInvoice.objects.filter(party=party)
        if start_date:
            purchases = purchases.filter(purchase_date__gte=start_date)
        if end_date:
            purchases = purchases.filter(purchase_date__lte=end_date)

        # Get payments
        from banking.models import PaymentEntry
        payments = PaymentEntry.objects.filter(party=party)
        if start_date:
            payments = payments.filter(payment_date__gte=start_date)
        if end_date:
            payments = payments.filter(payment_date__lte=end_date)

        # Prepare unified transaction list
        transactions = []
        for sale in sales:
            transactions.append({
                'date': sale.sale_date,
                'type': 'sale',
                'ref': sale.invoice_no,
                'amount': float(sale.total_with_vat_aed),
                'direction': 'credit',  # sale increases balance
            })
        for purchase in purchases:
            transactions.append({
                'date': purchase.purchase_date,
                'type': 'purchase',
                'ref': purchase.invoice_no,
                'amount': float(purchase.total_with_vat_aed),
                'direction': 'debit',  # purchase decreases balance
            })
        for payment in payments:
            transactions.append({
                'date': payment.payment_date,
                'type': 'payment',
                'ref': payment.id,
                'amount': float(payment.amount),
                'direction': 'debit',  # payment decreases balance
            })

        # Filter out transactions with null date to avoid TypeError
        transactions = [tx for tx in transactions if tx['date'] is not None]

        # Sort by date, then by type for consistency
        transactions.sort(key=lambda x: (x['date'], x['type']))

        # Group by date
        from collections import OrderedDict, defaultdict
        grouped = OrderedDict()
        balance = 0
        for tx in transactions:
            date_key = tx['date'].isoformat() if hasattr(tx['date'], 'isoformat') else str(tx['date'])
            if date_key not in grouped:
                grouped[date_key] = {
                    'date': date_key,
                    'transactions': [],
                }
            # Calculate balance after this transaction
            if tx['type'] == 'sale':
                balance += tx['amount']
            else:
                balance -= tx['amount']
            tx_with_balance = dict(tx)
            tx_with_balance['balance'] = balance
            grouped[date_key]['transactions'].append(tx_with_balance)

        # Prepare final result as a list
        result = list(grouped.values())
        total_balance = balance

        return Response({
            'datewise': result,
            'total_balance': total_balance
        })

    @action(detail=False, methods=['get'], url_path='all-transactions')
    def all_transactions(self, request):
        """
        Returns summary of transactions for all parties, similar to customer_transactions.
        Supports ?has_balance=true|false to filter by balance.
        Supports ?type=customer|supplier to filter by party type.
        """
        has_balance = request.query_params.get('has_balance')
        party_type = request.query_params.get('type')
        parties = self.get_queryset()
        if party_type:
            parties = parties.filter(type=party_type)
        results = []
        for party in parties:
            sales = SaleInvoice.objects.filter(party=party)
            purchases = PurchaseInvoice.objects.filter(party=party)
            payments = PaymentEntry.objects.filter(party=party)

            total_sale_count = sales.count()
            total_purchase_count = purchases.count()
            total_sale_amount = sales.aggregate(total=models.Sum('total_with_vat_aed'))['total'] or 0
            total_purchase_amount = purchases.aggregate(total=models.Sum('total_with_vat_aed'))['total'] or 0

            payment_types = payments.values_list('payment_type', flat=True).distinct()
            payments_by_type = {}
            total_payments = 0
            for p_type in payment_types:
                type_payments = payments.filter(payment_type=p_type)
                type_total = type_payments.aggregate(total=models.Sum('amount'))['total'] or 0
                payments_by_type[p_type] = type_total
                total_payments += type_total

            cheque_payments = payments.filter(payment_type='cheque')
            cheque_due = cheque_payments.filter(is_cheque_cleared=False)
            cheque_paid = cheque_payments.filter(is_cheque_cleared=True)
            cheque_due_total = cheque_due.aggregate(total=models.Sum('amount'))['total'] or 0
            cheque_paid_total = cheque_paid.aggregate(total=models.Sum('amount'))['total'] or 0

            balance_amount = total_sale_amount - total_payments

            # Apply has_balance filter
            if has_balance is not None:
                if has_balance.lower() == 'true' and balance_amount == 0:
                    continue
                if has_balance.lower() == 'false' and balance_amount != 0:
                    continue

            results.append({
                'party_id': party.id,
                'party_name': party.name,
                'total_sale_count': total_sale_count,
                'total_purchase_count': total_purchase_count,
                'total_sale_amount': total_sale_amount,
                'total_purchase_amount': total_purchase_amount,
                'payments_by_type': payments_by_type,
                'total_payments': total_payments,
                'balance_amount': balance_amount,
                'cheque_due_total': cheque_due_total,
                'cheque_paid_total': cheque_paid_total
            })
        return Response(results)
