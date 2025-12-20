# filepath: /Users/shamilkc/PersonalProjects/erp/employee/api/filters.py
from django_filters import rest_framework as filters
from employee.models import SalaryEntry, SalaryPayment

class SalaryEntryFilter(filters.FilterSet):
    date__gte = filters.DateFilter(field_name='date', lookup_expr='gte')
    date__lte = filters.DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model = SalaryEntry
        fields = ['date__gte', 'date__lte']

class SalaryPaymentFilter(filters.FilterSet):
    date__gte = filters.DateFilter(field_name='date', lookup_expr='gte')
    date__lte = filters.DateFilter(field_name='date', lookup_expr='lte')
    payment_type = filters.CharFilter(field_name='payment_type', lookup_expr='iexact')
    employee_name = filters.CharFilter(field_name='salary_entry__account__name', lookup_expr='icontains')

    class Meta:
        model = SalaryPayment
        fields = ['employee_name', 'date__gte', 'date__lte', 'payment_type']
