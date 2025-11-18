import django_filters
from django.db import models
from products.models import ProductItem

class ProductItemFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            models.Q(product_code__icontains=value) |
            models.Q(grade__grade__icontains=value) |
            models.Q(grade__product_type__type_name__icontains=value) |
            models.Q(grade__product_type__product__name__icontains=value)
        )

    class Meta:
        model = ProductItem
        fields = ['search']
