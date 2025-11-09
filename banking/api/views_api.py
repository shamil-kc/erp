from rest_framework import viewsets, status
from rest_framework.views import APIView
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
from django.db import transaction
from rest_framework.response import Response
from rest_framework import permissions
from .filters import PaymentEntryFilter
from banking.models import CashAccount
from django.utils import timezone



class PaymentEntryViewSet(viewsets.ModelViewSet):
    queryset = PaymentEntry.objects.all()
    serializer_class = PaymentEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentEntryFilter

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        cash_account = CashAccount.objects.first()
        if cash_account:
            # For sale invoices, deposit money into appropriate account
            if instance.invoice_type == 'sale':
                if instance.payment_type == 'hand':
                    cash_account.deposit(instance.amount, 'cash_in_hand')
                elif instance.payment_type == 'bank':
                    cash_account.deposit(instance.amount, 'cash_in_bank')
                elif instance.payment_type == 'check':
                    cash_account.deposit(instance.amount, 'cash_in_check')
            # For purchase invoices, withdraw money from appropriate account
            elif instance.invoice_type == 'purchase':
                if instance.payment_type == 'hand':
                    cash_account.withdraw(instance.amount, 'cash_in_hand')
                elif instance.payment_type == 'bank':
                    cash_account.withdraw(instance.amount, 'cash_in_bank')
                elif instance.payment_type == 'check':
                    cash_account.withdraw(instance.amount, 'cash_in_check')

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
                    # Reverse the previous transaction
                    if old_instance.invoice_type == 'sale':
                        if old_payment_type == 'hand':
                            cash_account.withdraw(old_amount, 'cash_in_hand')
                        elif old_payment_type == 'bank':
                            cash_account.withdraw(old_amount, 'cash_in_bank')
                        elif old_payment_type == 'check':
                            cash_account.withdraw(old_amount, 'cash_in_check')
                    elif old_instance.invoice_type == 'purchase':
                        if old_payment_type == 'hand':
                            cash_account.deposit(old_amount, 'cash_in_hand')
                        elif old_payment_type == 'bank':
                            cash_account.deposit(old_amount, 'cash_in_bank')
                        elif old_payment_type == 'check':
                            cash_account.deposit(old_amount, 'cash_in_check')
                    
                    # Apply the new transaction
                    if instance.invoice_type == 'sale':
                        if instance.payment_type == 'hand':
                            cash_account.deposit(instance.amount, 'cash_in_hand')
                        elif instance.payment_type == 'bank':
                            cash_account.deposit(instance.amount, 'cash_in_bank')
                        elif instance.payment_type == 'check':
                            cash_account.deposit(instance.amount, 'cash_in_check')
                    elif instance.invoice_type == 'purchase':
                        if instance.payment_type == 'hand':
                            cash_account.withdraw(instance.amount, 'cash_in_hand')
                        elif instance.payment_type == 'bank':
                            cash_account.withdraw(instance.amount, 'cash_in_bank')
                        elif instance.payment_type == 'check':
                            cash_account.withdraw(instance.amount, 'cash_in_check')



class CashAccountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        response = {}
        cash_accounts = CashAccount.objects.all()
        if not cash_accounts:
            return Response({"error": "No cash account found."}, status=status.HTTP_404_NOT_FOUND)
        for cash_account in cash_accounts:
            data = {
                "cash_in_hand": float(cash_account.cash_in_hand),
                "cash_in_bank": float(cash_account.cash_in_bank),
                "check_cash": float(cash_account.check_cash),
                "updated_at": cash_account.updated_at,
                "account_type": cash_account.type
            }
            response[cash_account.type] = data
        return Response(response, status=status.HTTP_200_OK)


class CheckApproveAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cash_account = CashAccount.objects.filter(type='main').first()
        if not cash_account:
            return Response({"error": "No main cash account found."}, status=status.HTTP_404_NOT_FOUND)
        check_amount = cash_account.check_cash

        amount = request.data.get('amount')
        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError):
            return Response({"error": "Valid 'amount' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)
        if amount > check_amount:
            return Response({"error": "Amount exceeds available check cash."}, status=status.HTTP_400_BAD_REQUEST)

        # Move specified amount from check to bank
        cash_account.check_cash -= amount
        cash_account.cash_in_bank += amount
        cash_account.save()
        return Response({
            "cash_in_hand": float(cash_account.cash_in_hand),
            "cash_in_bank": float(cash_account.cash_in_bank),
            "check_cash": float(cash_account.check_cash),
            "moved_amount": float(amount),
            "updated_at": cash_account.updated_at,
        }, status=status.HTTP_200_OK)
