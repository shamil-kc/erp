from rest_framework import viewsets
from django.forms.models import model_to_dict
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from .filters import SaleInvoiceFilter
from decimal import Decimal
from django.db import transaction
from rest_framework import permissions
from base.utils import log_activity


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
