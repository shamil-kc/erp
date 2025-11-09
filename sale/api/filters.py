import django_filters
from base.models import SaleInvoice


class SaleInvoiceFilter(django_filters.FilterSet):
    sale_date__gte = django_filters.DateFilter(field_name='sale_date', lookup_expr='gte')
    sale_date__lte = django_filters.DateFilter(field_name='sale_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = SaleInvoice
        fields = ['sale_date__gte', 'sale_date__lte', 'status']