from django.contrib import admin
from .models import Product, ProductType, ProductGrade, ProductItem


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
        'grade', 'get_product_type', 'get_product', 'size', 'unit', 'weight_kg_each', 'product_code'
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
        try:
            if obj.grade and obj.grade.product_type:
                return obj.grade.product_type.type_name
            else:
                return None
        except:
            return None

    get_product_type.short_description = 'Product Type'

    def get_product(self, obj):
        """
        Returns the name of the related product.
        """
        return obj.product.name if obj.product else None
    get_product.short_description = 'Product'

