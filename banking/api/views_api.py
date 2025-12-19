from rest_framework import viewsets, status
from rest_framework.views import APIView
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from django.db import transaction
from rest_framework.response import Response
from rest_framework import permissions
from .filters import PaymentEntryFilter, CashAccountTransferFilter
from banking.models import CashAccount
from django.utils import timezone
from banking.models import PaymentEntry
from django.db.models import Sum
from banking.models import CashAccountTransfer
from .serializers import CashAccountTransferSerializer



class PaymentEntryViewSet(viewsets.ModelViewSet):
    queryset = PaymentEntry.objects.all().order_by('-created_at')
    serializer_class = PaymentEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentEntryFilter

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        cash_account = CashAccount.objects.first()
        if cash_account:
            note = f"PaymentEntry #{instance.id} ({instance.invoice_type})"
            # For sale invoices, deposit money into appropriate account
            if instance.invoice_type == 'sale':
                if instance.payment_type == 'hand':
                    cash_account.deposit(instance.amount, 'cash_in_hand', created_by=self.request.user, note=note)
                elif instance.payment_type == 'bank':
                    cash_account.deposit(instance.amount, 'cash_in_bank', created_by=self.request.user, note=note)
                elif instance.payment_type == 'check':
                    cash_account.deposit(instance.amount, 'cash_in_check', created_by=self.request.user, note=note)
            # For purchase invoices, withdraw money from appropriate account
            elif instance.invoice_type == 'purchase':
                if instance.payment_type == 'hand':
                    cash_account.withdraw(instance.amount, 'cash_in_hand', created_by=self.request.user, note=note)
                elif instance.payment_type == 'bank':
                    cash_account.withdraw(instance.amount, 'cash_in_bank', created_by=self.request.user, note=note)
                elif instance.payment_type == 'check':
                    cash_account.deposit(instance.amount, 'cash_in_check', created_by=self.request.user, note=note)

    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_amount = old_instance.amount
        old_payment_type = old_instance.payment_type
        
        instance = serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())
        
        # Only update cash accounts if amount or payment type changed
        if old_amount != instance.amount or old_payment_type != instance.payment_type:
            cash_account = CashAccount.objects.first()
            if cash_account:
                with transaction.atomic():
                    note = f"PaymentEntry Update #{instance.id} ({instance.invoice_type})"
                    # Reverse the previous transaction
                    if old_instance.invoice_type == 'sale':
                        if old_payment_type == 'hand':
                            cash_account.withdraw(old_amount, 'cash_in_hand', created_by=self.request.user, note=note)
                        elif old_payment_type == 'bank':
                            cash_account.withdraw(old_amount, 'cash_in_bank', created_by=self.request.user, note=note)
                        elif old_payment_type == 'check':
                            cash_account.withdraw(old_amount, 'cash_in_check', created_by=self.request.user, note=note)
                    elif old_instance.invoice_type == 'purchase':
                        if old_payment_type == 'hand':
                            cash_account.deposit(old_amount, 'cash_in_hand', created_by=self.request.user, note=note)
                        elif old_payment_type == 'bank':
                            cash_account.deposit(old_amount, 'cash_in_bank', created_by=self.request.user, note=note)
                        elif old_payment_type == 'check':
                            cash_account.deposit(old_amount, 'cash_in_check', created_by=self.request.user, note=note)

                    # Apply the new transaction
                    if instance.invoice_type == 'sale':
                        if instance.payment_type == 'hand':
                            cash_account.deposit(instance.amount, 'cash_in_hand', created_by=self.request.user, note=note)
                        elif instance.payment_type == 'bank':
                            cash_account.deposit(instance.amount, 'cash_in_bank', created_by=self.request.user, note=note)
                        elif instance.payment_type == 'check':
                            cash_account.deposit(instance.amount, 'cash_in_check', created_by=self.request.user, note=note)
                    elif instance.invoice_type == 'purchase':
                        if instance.payment_type == 'hand':
                            cash_account.withdraw(instance.amount, 'cash_in_hand', created_by=self.request.user, note=note)
                        elif instance.payment_type == 'bank':
                            cash_account.withdraw(instance.amount, 'cash_in_bank', created_by=self.request.user, note=note)
                        elif instance.payment_type == 'check':
                            cash_account.withdraw(instance.amount, 'cash_in_check', created_by=self.request.user, note=note)



class CashAccountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        response = {}
        cash_accounts = CashAccount.objects.all()
        # Calculate pending cheques for sales and purchases
        pending_sales_cheques = PaymentEntry.objects.filter(
            payment_type='check',
            invoice_type='sale',
            is_cheque_cleared=False
        ).aggregate(total=Sum('amount'))['total'] or 0
        pending_purchase_cheques = PaymentEntry.objects.filter(
            payment_type='check',
            invoice_type='purchase',
            is_cheque_cleared=False
        ).aggregate(total=Sum('amount'))['total'] or 0

        if not cash_accounts:
            return Response({"error": "No cash account found."}, status=status.HTTP_404_NOT_FOUND)
        for cash_account in cash_accounts:
            data = {
                "id": cash_account.id,
                "cash_in_hand": float(cash_account.cash_in_hand),
                "cash_in_bank": float(cash_account.cash_in_bank),
                "check_cash": float(cash_account.check_cash),
                "updated_at": cash_account.updated_at,
                "account_type": cash_account.type,
                "pending_sales_cheques": float(pending_sales_cheques),
                "pending_purchase_cheques": float(pending_purchase_cheques),
            }
            response[cash_account.type] = data
        return Response(response, status=status.HTTP_200_OK)


class CheckApproveAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cash_account = CashAccount.objects.filter(type='main').first()
        if not cash_account:
            return Response({"error": "No main cash account found."}, status=status.HTTP_404_NOT_FOUND)

        payment_entry_id = request.data.get('payment_entry_id')
        amount = request.data.get('amount')
        action = request.data.get('action')
        cheque_cleared_date = request.data.get('cheque_cleared_date')

        if not payment_entry_id:
            return Response({"error": "payment_entry_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if action not in ['credit', 'debit']:
            return Response({"error": "action must be 'credit' or 'debit'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError):
            return Response({"error": "Valid 'amount' is required."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"error": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment_entry = PaymentEntry.objects.get(id=payment_entry_id)
        except PaymentEntry.DoesNotExist:
            return Response({"error": "PaymentEntry not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment_entry.is_cheque_cleared:
            return Response({"error": "Cheque already cleared for this payment entry."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if action == 'credit':
                cash_account.check_cash -= amount
                cash_account.cash_in_bank += amount
            elif action == 'debit':
                cash_account.check_cash -= amount
                cash_account.cash_in_bank -= amount
            cash_account.save()
            payment_entry.is_cheque_cleared = True
            payment_entry.cheque_cleared_date = cheque_cleared_date
            payment_entry.save()


        return Response({
            "cash_in_hand": float(cash_account.cash_in_hand),
            "cash_in_bank": float(cash_account.cash_in_bank),
            "check_cash": float(cash_account.check_cash),
            "moved_amount": float(amount),
            "updated_at": cash_account.updated_at,
            "payment_entry_id": payment_entry.id,
            "is_cheque_cleared": payment_entry.is_cheque_cleared,
        }, status=status.HTTP_200_OK)


class CashAccountTransferViewSet(viewsets.ModelViewSet):
    queryset = CashAccountTransfer.objects.all().order_by('-created_at')
    serializer_class = CashAccountTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CashAccountTransferFilter

    def perform_create(self, serializer):
        from_account = serializer.validated_data['from_account']
        to_account = serializer.validated_data['to_account']
        from_type = serializer.validated_data['from_type']
        to_type = serializer.validated_data['to_type']
        amount = serializer.validated_data['amount']
        transfer_date = serializer.validated_data.get('transfer_date')
        note = serializer.validated_data.get('note', '')

        if from_account == to_account:
            if from_type == to_type:
                raise serializers.ValidationError("Cannot transfer to the same account and type.")
            # Use transfer method for same account, which handles both sides
            from_account.transfer(from_type, to_type, amount, created_by=self.request.user, note=note)
        else:
            # Different accounts: withdraw from source, deposit to target
            from_account.withdraw(amount, from_type, created_by=self.request.user, note=note)
            to_account.deposit(amount, to_type, created_by=self.request.user, note=note)
        serializer.save(created_by=self.request.user, transfer_date=transfer_date)
