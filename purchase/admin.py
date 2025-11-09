from django.contrib import admin
from .models import PurchaseInvoice, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    autocomplete_fields = ['item']
    fields = (
        'item', 'qty', 'unit_price_usd', 'unit_price_aed',
        'shipping_per_unit_usd', 'shipping_per_unit_aed', 'factors',
        'amount_usd', 'amount_aed',
    )
    readonly_fields = ('amount_usd', 'amount_aed')

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_no', 'purchase_date', 'total_with_vat_usd', 'total_with_vat_aed'
    )
    search_fields = ('invoice_no',)
    date_hierarchy = 'purchase_date'
    inlines = [PurchaseItemInline]
    autocomplete_fields = []


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = (
        'invoice', 'item', 'qty', 'unit_price_usd','unit_price_aed',
        'shipping_per_unit_usd', 'shipping_per_unit_aed',
        'amount_usd', 'amount_aed'
    )
    search_fields = ('item__grade__product_type__product__name', 'item__size', 'invoice__invoice_no')
    autocomplete_fields = ['item', 'invoice']
    readonly_fields = ('amount_usd', 'amount_aed')
