from django.db import models
from django.contrib.auth.models import User
from products.models import ProductItem


class Stock(models.Model):
    product_item = models.OneToOneField(ProductItem, on_delete=models.CASCADE, related_name='stock')
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stock for {self.product_item}: {self.quantity}"
