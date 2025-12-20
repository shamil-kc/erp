import django_filters
from sale.models import SaleInvoice, SaleReturnItem, SaleItem


class SaleInvoiceFilter(django_filters.FilterSet):
    sale_date__gte = django_filters.DateFilter(field_name='sale_date', lookup_expr='gte')
    sale_date__lte = django_filters.DateFilter(field_name='sale_date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    party_id = django_filters.NumberFilter(field_name='party_id')
    invoice_no = django_filters.CharFilter(field_name='invoice_no', lookup_expr='icontains')
    has_purchase_item = django_filters.BooleanFilter(method='filter_has_purchase_item')
    purchase_item_ids = django_filters.BaseInFilter(
        field_name='sale_items__purchase_item_id', method='filter_by_purchase_item_ids'
    )

    class Meta:
        model = SaleInvoice
        fields = [
            'sale_date__gte', 'sale_date__lte', 'status', 'party_id',
            'invoice_no', 'has_purchase_item', 'purchase_item_ids'
        ]

    def filter_has_purchase_item(self, queryset, name, value):
        if value:
            # Only invoices where at least one sale item has a purchase_item set
            return queryset.filter(sale_items__purchase_item__isnull=False).distinct()
        else:
            # Only invoices where all sale items have no purchase_item
            return queryset.filter(sale_items__purchase_item__isnull=True).distinct()

    def filter_by_purchase_item_ids(self, queryset, name, value):
        if value:
            return queryset.filter(sale_items__purchase_item_id__in=value).distinct()
        return queryset


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
