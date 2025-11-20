from django.db import models
from django.contrib.auth.models import User
from django.db.models import Max
import re


class Product(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return self.name



class ProductType(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    type_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.product.name} - {self.type_name}"

class ProductGrade(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    grade = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.product_type} - {self.grade}"

class ProductItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL,
                                     null=True, blank=True)
    grade = models.ForeignKey(ProductGrade, on_delete=models.SET_NULL, null=True, blank=True)
    size = models.CharField(max_length=20, null=True, blank=True)
    unit = models.CharField(max_length=20, default='PCs')
    weight_kg_each = models.FloatField(null=True, blank=True)
    product_code = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def generate_product_code(self):
        """Generate a unique product code with format 'AJM-<number>'"""
        prefix = "AJM"

        # Get all existing AJM codes and extract the highest number
        existing_codes = ProductItem.objects.filter(
            product_code__startswith=f"{prefix}-"
        ).exclude(pk=self.pk).values_list('product_code', flat=True)

        max_number = 0
        for code in existing_codes:
            try:
                # Extract number after AJM-
                number_part = code.replace(f"{prefix}-", "")
                if number_part.isdigit():
                    max_number = max(max_number, int(number_part))
            except (ValueError, AttributeError):
                continue

        return f"{prefix}-{max_number + 1}"

    def save(self, *args, **kwargs):
        if not self.product_code:
            self.product_code = self.generate_product_code()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.grade:
            return f"{self.grade} - Size {self.size}"
        elif self.product_type:
            return f"{self.product_type} - Size {self.size}"
        else:
            return f"{self.product} - Size {self.size}"
