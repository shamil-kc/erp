import django_filters
from purchase.models import PurchaseInvoice, PurchaseItem

class PurchaseInvoiceFilter(django_filters.FilterSet):
    purchase_date__gte = django_filters.DateFilter(field_name='purchase_date', lookup_expr='gte')
    purchase_date__lte = django_filters.DateFilter(field_name='purchase_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = PurchaseInvoice
        fields = ['purchase_date__gte', 'purchase_date__lte', 'status']

class PurchaseItemFilter(django_filters.FilterSet):
    product_id = django_filters.NumberFilter(field_name='item__id')
    has_invoice = django_filters.BooleanFilter(method='filter_has_invoice')

    class Meta:
        model = PurchaseItem
        fields = ['product_id', 'has_invoice']

    def filter_has_invoice(self, queryset, name, value):
        if value is True:
            return queryset.filter(invoice__isnull=False)
        elif value is False:
            return queryset.filter(invoice__isnull=True)
        return queryset
