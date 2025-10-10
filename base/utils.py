from django.utils import timezone
from .models import CashAccount, UserActivity
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


def log_activity(request, action, instance, changes=None):
    def convert_decimal(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    if changes:
        changes = {k: {'old': convert_decimal(v['old']),
                       'new': convert_decimal(v['new'])} for k, v in
                   changes.items()}

    content_type = ContentType.objects.get_for_model(instance)
    UserActivity.objects.create(user=request.user, content_type=content_type,
        object_id=instance.id, action=action, changes=changes,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'))


