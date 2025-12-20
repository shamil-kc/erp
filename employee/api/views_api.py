from rest_framework import viewsets
from django.forms.models import model_to_dict
from .serializers import *
from .filters import SalaryEntryFilter, SalaryPaymentFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from base.utils import log_activity
from banking.models import CashAccount
from employee.models import SalaryEntry, Account, Designation, EmployeeLeave
from django.utils import timezone
from rest_framework.decorators import action
from django.db.models import Sum
from rest_framework.response import Response


class SalaryEntryViewSet(viewsets.ModelViewSet):
    queryset = SalaryEntry.objects.all().order_by('-created_at')
    serializer_class = SalaryEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SalaryEntryFilter

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

        # No cash logic on update (only on create)

    @action(detail=False, methods=['get'], url_path='totals')
    def totals(self, request):
        """
        Returns total amounts (AED & USD) for filtered salary entries.
        """
        queryset = self.filter_queryset(self.get_queryset())
        total_aed = queryset.aggregate(total=Sum('amount_aed'))['total'] or 0
        total_usd = queryset.aggregate(total=Sum('amount_usd'))['total'] or 0
        return Response({
            "total_aed": float(total_aed),
            "total_usd": float(total_usd)
        })


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all().order_by('-created_at')
    serializer_class = DesignationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user,
                        modified_at=timezone.now())


class EmployeeLeaveViewSet(viewsets.ModelViewSet):
    queryset = EmployeeLeave.objects.all()
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account', 'leave_type', 'approved', 'start_date', 'end_date']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user, modified_at=timezone.now())


class SalaryPaymentViewSet(viewsets.ModelViewSet):
    queryset = SalaryPayment.objects.all().order_by('-created_at')
    serializer_class = SalaryPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SalaryPaymentFilter

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        # Payment logic: affect cash/bank/check account here as needed
        from banking.models import CashAccount
        cash_account = CashAccount.objects.first()
        if instance.payment_type == 'hand':
            cash_account.withdraw(
                instance.amount_aed, 'cash_in_hand',created_by=self.request.user,
                note='Salary Payment hand invoice ID {}'.format(instance.salary_entry.id))
        elif instance.payment_type == 'bank':
            cash_account.withdraw(
                instance.amount_aed, 'cash_in_bank',
                created_by=self.request.user,
                note='Salary Payment bank invoice ID {}'.format(instance.salary_entry.id))
        elif instance.payment_type == 'check':
            cash_account.deposit(
                instance.amount_aed, 'cash_in_check',
                created_by=self.request.user,
                note='Salary Payment hand invoice ID {}'.format(instance.salary_entry.id))
        # Add logic for bank/check if needed
        log_activity(self.request, 'create', instance)

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user, modified_at=timezone.now())
