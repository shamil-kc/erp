from django.contrib import admin
from .models import *

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product_item', 'quantity', 'last_updated')
