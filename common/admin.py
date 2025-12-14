from django.contrib import admin
from .models import *



@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    """
    Admin for Tax model.
    Displays tax name, VAT percent, corporate tax percent, and active status.
    """
    list_display = ('name', 'vat_percent', 'corporate_tax_percent', 'active')


@admin.register(ExpenseType)
class ExpenseTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('type', 'amount_aed', 'amount_usd', 'date', 'notes')
    list_filter = ('type', 'date')
    search_fields = ('notes',)
    date_hierarchy = 'date'


@admin.register(ServiceFee)
class ServiceFee(admin.ModelAdmin):
    list_display = ('__str__', 'description', 'amount_aed', 'amount_usd')
    search_fields = ('__str__',)


@admin.register(ExtraCharges)
class ExtraChargesAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount',)
    search_fields = ('description',)


@admin.register(Wage)
class WageChargesAdmin(admin.ModelAdmin):
    list_display = ('amount_aed', 'date', 'notes')
    date_hierarchy = 'date'
