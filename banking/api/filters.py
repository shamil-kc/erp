import django_filters
from base.models import PaymentEntry


class PaymentEntryFilter(django_filters.FilterSet):
    invoice_type = django_filters.CharFilter(field_name='invoice_type', lookup_expr='iexact')
    invoice_id = django_filters.NumberFilter(field_name='invoice_id')
    payment_type = django_filters.CharFilter(field_name='payment_type', lookup_expr='iexact')
    created_at__gte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at__lte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = PaymentEntry
        fields = ['invoice_type', 'invoice_id', 'payment_type', 'created_at__gte', 'created_at__lte']