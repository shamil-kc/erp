from django.contrib import admin
from .models import PurchaseInvoice, PurchaseItem, PurchaseReturnItem, PurchaseReturnItemEntry


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


class PurchaseReturnItemEntryInline(admin.TabularInline):
    model = PurchaseReturnItemEntry
    extra = 0
    autocomplete_fields = ['purchase_item']
    fields = ('purchase_item', 'qty', 'remarks')
    readonly_fields = ()

@admin.register(PurchaseReturnItem)
class PurchaseReturnItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_invoice', 'returned_by', 'return_date', 'remarks', 'created_at')
    search_fields = ('purchase_invoice__invoice_no', 'returned_by__username')
    date_hierarchy = 'return_date'
    inlines = [PurchaseReturnItemEntryInline]
    autocomplete_fields = ['purchase_invoice', 'returned_by']
