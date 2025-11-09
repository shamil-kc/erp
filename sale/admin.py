from django.contrib import admin
from .models import SaleInvoice, SaleItem
from common.models import ServiceFee


class SaleItemInline(admin.TabularInline):
    """
    Inline admin for SaleItem in SaleInvoice admin.
    """
    model = SaleItem
    extra = 1
    autocomplete_fields = ['item']

class ServiceFeeInline(admin.TabularInline):
    """
    Inline admin for ServiceFee in SaleInvoice admin.
    """
    model = ServiceFee
    extra = 0
    fields = ('description', 'amount_usd', 'amount_aed')
    readonly_fields = ()  # Keep empty if editable


@admin.register(SaleInvoice)
class SaleInvoiceAdmin(admin.ModelAdmin):
    """
    Admin for SaleInvoice model.
    Displays invoice details and allows inline editing of related sale items.
    """
    list_display = ('invoice_no', 'sale_date', 'created_at', 'status')
    inlines = [SaleItemInline, ServiceFeeInline]
    search_fields = ('invoice_no',)
    list_filter = ('status',)

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    """
    Admin for SaleItem model.
    Displays invoice, item, quantity, sale price, and amount.
    Allows searching by related fields and autocomplete for item/invoice.
    """
    list_display = (
        'invoice', 'item', 'qty', 'sale_price_usd', 'amount_usd'
    )
    autocomplete_fields = ['item', 'invoice']
    search_fields = (
        'invoice__invoice_no',
        'item__grade__product_type__product__name', 'item__size'
    )