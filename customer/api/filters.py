import django_filters
from customer.models import Party

class PartyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    company_name = django_filters.CharFilter(field_name='company_name', lookup_expr='icontains')

    class Meta:
        model = Party
        fields = ['type', 'name', 'company_name']

