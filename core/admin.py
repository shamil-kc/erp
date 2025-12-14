from django.contrib import admin
from .models import CapitalAccount


@admin.register(CapitalAccount)
class CapitalAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'created_at', 'modified_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'modified_at')
