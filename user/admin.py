from django.contrib import admin
from user.models import UserActivity


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'content_type', 'object_id', 'timestamp',
                    'ip_address')
    list_filter = ('action', 'content_type', 'timestamp')
    search_fields = ('user__username', 'ip_address', 'user_agent')
    readonly_fields = ('user', 'content_type', 'object_id', 'action',
                       'timestamp', 'changes', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'

