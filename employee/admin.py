from django.contrib import admin
from .models import *


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'notes')
    search_fields = ('name', 'designation__title')
    list_filter = ('designation',)

@admin.register(SalaryEntry)
class SalaryEntryAdmin(admin.ModelAdmin):
    list_display = ('account', 'entry_type', 'amount_aed', 'amount_usd', 'date', 'notes')
    list_filter = ('entry_type', 'date', 'account')
    search_fields = ('account__name', 'notes')
    date_hierarchy = 'date'


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('salary_entry', 'payment_type', 'amount_aed', 'amount_usd', 'date', 'notes')
    list_filter = ('payment_type', 'date')
    search_fields = ('salary_entry__account__name', 'notes')
    date_hierarchy = 'date'