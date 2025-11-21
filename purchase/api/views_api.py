from rest_framework import viewsets
from django.forms.models import model_to_dict
from .serializers import *
from django_filters.rest_framework import DjangoFilterBackend
from .filters import PurchaseInvoiceFilter, PurchaseItemFilter
from django.db import transaction
from rest_framework import permissions
from base.utils import log_activity
from purchase.models import PurchaseReturnItem
from purchase.api.serializers import PurchaseReturnItemSerializer


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


class PurchaseReturnItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseReturnItem.objects.all().order_by('-return_date')
    serializer_class = PurchaseReturnItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(returned_by=self.request.user)
