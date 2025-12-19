from django.contrib import admin
from .models import *


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'created_at', 'created_by')

@admin.register(CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


@admin.register(PaymentEntry)
class PaymentEntryAdmin(admin.ModelAdmin):
    list_display = ('invoice_type', 'invoice_id', 'payment_type', 'amount',
                    'created_at', 'created_by')


@admin.register(CashAccountTransfer)
class CashAccountTransferAdmin(admin.ModelAdmin):
    list_display = ('from_account', 'to_account', 'from_type', 'to_type',
                    'amount', 'created_at')
