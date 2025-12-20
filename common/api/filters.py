from django_filters import rest_framework as filters
from common.models import Expense

class ExpenseFilter(filters.FilterSet):
    date__gte = filters.DateFilter(
        field_name='date', lookup_expr='gte')
    date__lte = filters.DateFilter(
        field_name='date', lookup_expr='lte')
    expense_type = filters.NumberFilter(field_name='type')
    category = filters.CharFilter(field_name='type__category')

    class Meta:
        model = Expense
        fields = ['date__gte', 'date__lte', 'expense_type', 'category']

