# filepath: /Users/shamilkc/PersonalProjects/erp/employee/api/filters.py
from django_filters import rest_framework as filters
from employee.models import SalaryEntry

class SalaryEntryFilter(filters.FilterSet):
    date__gte = filters.DateFilter(field_name='date', lookup_expr='gte')
    date__lte = filters.DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model = SalaryEntry
        fields = ['date__gte', 'date__lte']

