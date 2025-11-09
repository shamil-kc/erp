import django_filters
from base.models import PurchaseInvoice

class PurchaseInvoiceFilter(django_filters.FilterSet):
    purchase_date__gte = django_filters.DateFilter(field_name='purchase_date', lookup_expr='gte')
    purchase_date__lte = django_filters.DateFilter(field_name='purchase_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = PurchaseInvoice
        fields = ['purchase_date__gte', 'purchase_date__lte', 'status']