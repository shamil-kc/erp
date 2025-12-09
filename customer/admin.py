from django.contrib import admin

from .models import Party

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'phone', 'email', 'company_name', 'trn', 'created_at', 'modified_at')
    search_fields = ('name', 'company_name', 'trn', 'email', 'phone')
    list_filter = ('type', 'created_at', 'modified_at')
    ordering = ('-created_at',)