from django.db import models
from django.contrib.auth.models import User


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey('contenttypes.ContentType',
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=[('create', 'Created'),
        ('update', 'Updated'), ('delete', 'Deleted')])
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} {self.action} {self.content_type} at {self.timestamp}"

