from django.contrib import admin
from .models import *


@admin.register(CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


@admin.register(PaymentEntry)
class PaymentEntryAdmin(admin.ModelAdmin):
    list_display = ('invoice_type', 'invoice_id', 'payment_type', 'amount',
                    'created_at', 'created_by')
