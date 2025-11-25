import json
from decimal import Decimal
from datetime import date, datetime
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from user.models import UserActivity


class DjangoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Django model fields"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return super().default(obj)


def log_activity(request, action, instance, changes=None):
    content_type = ContentType.objects.get_for_model(instance)

    # Convert changes to JSON-serializable format if provided
    serializable_changes = None
    if changes:
        try:
            # Convert changes to JSON using custom encoder
            serializable_changes = json.loads(json.dumps(changes, cls=DjangoJSONEncoder))
        except (TypeError, ValueError):
            # If serialization fails, convert to string representation
            serializable_changes = {k: {'old': str(v.get('old', '')), 'new': str(v.get('new', ''))}
                                  for k, v in changes.items() if isinstance(v, dict)}

    UserActivity.objects.create(
        user=request.user,
        content_type=content_type,
        object_id=instance.id,
        action=action,
        changes=serializable_changes,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
