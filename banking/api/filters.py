import django_filters
from banking.models import PaymentEntry, CashAccountTransfer


class PaymentEntryFilter(django_filters.FilterSet):
    invoice_type = django_filters.CharFilter(field_name='invoice_type', lookup_expr='iexact')
    invoice_id = django_filters.NumberFilter(field_name='invoice_id')
    payment_type = django_filters.CharFilter(field_name='payment_type', lookup_expr='iexact')
    created_at__gte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at__lte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    is_cheque_cleared = django_filters.BooleanFilter(field_name='is_cheque_cleared')
    party_id = django_filters.NumberFilter(field_name='party_id')

    class Meta:
        model = PaymentEntry
        fields = [
            'invoice_type', 'invoice_id', 'payment_type',
            'created_at__gte', 'created_at__lte', 'is_cheque_cleared', 'party_id'
        ]

class CashAccountTransferFilter(django_filters.FilterSet):
    from_account = django_filters.NumberFilter(field_name='from_account__id')
    to_account = django_filters.NumberFilter(field_name='to_account__id')
    from_type = django_filters.CharFilter(field_name='from_type')
    to_type = django_filters.CharFilter(field_name='to_type')
    created_by = django_filters.CharFilter(field_name='created_by__username')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    transfer_date__gte = django_filters.DateFilter(field_name='transfer_date', lookup_expr='gte')
    transfer_date__lte = django_filters.DateFilter(field_name='transfer_date', lookup_expr='lte')

    class Meta:
        model = CashAccountTransfer
        fields = ['from_account', 'to_account', 'from_type', 'to_type', 'created_by', 'min_amount', 'max_amount', 'transfer_date__gte', 'transfer_date__lte']
