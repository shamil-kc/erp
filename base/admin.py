"""Admin configuration for product-related models.

This file provides Django admin classes and inlines for managing products,
product types, grades, items, purchases, sales, and taxes.
"""

from django.contrib import admin
from .models import (Product, ProductType, ProductGrade, ProductItem,
                     PurchaseItem, PurchaseInvoice, SaleInvoice, SaleItem, Tax,
                     ExpenseType, Expense, Account, SalaryEntry, Designation,
                     ServiceFee)



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin for Product model.
    Allows searching by product name and inline editing of related types.
    """
    search_fields = ('name',)


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    """
    Admin for ProductType model.
    Allows searching by type name, autocomplete for product, and inline editing of related grades.
    """
    search_fields = ('type_name',)
    autocomplete_fields = ['product']

# --- PRODUCT GRADE ADMIN: mainly for autocomplete ---
@admin.register(ProductGrade)
class ProductGradeAdmin(admin.ModelAdmin):
    """
    Admin for ProductGrade model.
    Allows searching by grade and autocomplete for product type.
    """
    search_fields = ('grade',)
    autocomplete_fields = ['product_type']

# --- ITEM ADMIN: THE MASTER PAGE for all product combinations ---
@admin.register(ProductItem)
class ProductItemAdmin(admin.ModelAdmin):
    """
    Admin for ProductItem model.
    Displays grade, product type, product, size, unit, and weight.
    Allows searching by related product fields and autocomplete for grade.
    """
    list_display = (
        'grade', 'get_product_type', 'get_product', 'size', 'unit', 'weight_kg_each'
    )
    search_fields = (
        'grade__grade',
        'grade__product_type__type_name',
        'grade__product_type__product__name',
        'size'
    )
    autocomplete_fields = ['grade']

    fieldsets = (
        (None, {
            'fields': (
                'grade',  # Expand autocomplete by using raw_id_fields or popups if needed
                'size', 'unit', 'weight_kg_each'
            )
        }),
    )

    def get_product_type(self, obj):
        """
        Returns the type name of the related product type.
        """
        return obj.grade.product_type.type_name
    get_product_type.short_description = 'Product Type'

    def get_product(self, obj):
        """
        Returns the name of the related product.
        """
        return obj.grade.product_type.product.name
    get_product.short_description = 'Product'

# --- PURCHASE ADMIN: ---

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
        'invoice_no', 'supplier', 'purchase_date', 'total_with_vat_usd', 'total_with_vat_aed'
    )
    search_fields = ('invoice_no', 'supplier')
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



# --- SALES ADMIN ---
class SaleItemInline(admin.TabularInline):
    """
    Inline admin for SaleItem in SaleInvoice admin.
    """
    model = SaleItem
    extra = 1
    autocomplete_fields = ['item']

@admin.register(SaleInvoice)
class SaleInvoiceAdmin(admin.ModelAdmin):
    """
    Admin for SaleInvoice model.
    Displays invoice details and allows inline editing of related sale items.
    """
    list_display = ('invoice_no', 'sale_date', 'customer_name', 'created_at')
    inlines = [SaleItemInline]
    search_fields = ('invoice_no', 'customer_name')

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

@admin.register(ServiceFee)
class ServiceFee(admin.ModelAdmin):
    list_display = ('__str__', 'description', 'amount_aed', 'amount_usd')
    search_fields = ('__str__',)

