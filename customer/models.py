from django.db import models
from django.contrib.auth.models import User


class Party(models.Model):
    TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    trn = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.name} ({self.type})"
