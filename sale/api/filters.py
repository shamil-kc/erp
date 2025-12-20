import django_filters
from sale.models import SaleInvoice, SaleReturnItem, SaleItem


class SaleInvoiceFilter(django_filters.FilterSet):
    sale_date__gte = django_filters.DateFilter(field_name='sale_date', lookup_expr='gte')
    sale_date__lte = django_filters.DateFilter(field_name='sale_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    party_id = django_filters.NumberFilter(field_name='party_id')
    invoice_no = django_filters.CharFilter(field_name='invoice_no', lookup_expr='icontains')

    class Meta:
        model = SaleInvoice
        fields = ['sale_date__gte', 'sale_date__lte', 'status', 'party_id', 'invoice_no']


class SaleReturnItemFilter(django_filters.FilterSet):
    party_id = django_filters.NumberFilter(field_name='sale_invoice__party_id')

    class Meta:
        model = SaleReturnItem
        fields = ['party_id']


class SaleItemFilter(django_filters.FilterSet):
    purchase_item = django_filters.NumberFilter(field_name='purchase_item_id')

    class Meta:
        model = SaleItem
        fields = ['purchase_item']
