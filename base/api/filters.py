import django_filters
from base.models import PurchaseInvoice, SaleInvoice

class PurchaseInvoiceFilter(django_filters.FilterSet):
    purchase_date__gte = django_filters.DateFilter(field_name='purchase_date', lookup_expr='gte')
    purchase_date__lte = django_filters.DateFilter(field_name='purchase_date', lookup_expr='lte')

    class Meta:
        model = PurchaseInvoice
        fields = ['purchase_date__gte', 'purchase_date__lte']

class SaleInvoiceFilter(django_filters.FilterSet):
    sale_date__gte = django_filters.DateFilter(field_name='sale_date', lookup_expr='gte')
    sale_date__lte = django_filters.DateFilter(field_name='sale_date', lookup_expr='lte')

    class Meta:
        model = SaleInvoice
        fields = ['sale_date__gte', 'sale_date__lte']
