from django.db import models
from django.contrib.auth.models import User


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
    grade = models.ForeignKey(ProductGrade, on_delete=models.CASCADE)
    size = models.FloatField()
    unit = models.CharField(max_length=20, default='PCs')
    weight_kg_each = models.FloatField()
    product_code = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='+')

    def __str__(self):
        return f"{self.grade} - Size {self.size}"