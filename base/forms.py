from django import forms
from .models import Product, ProductType, ProductGrade, ProductItem

class ProductItemForm(forms.Form):
    product = forms.CharField(label='Product', max_length=100)
    product_type = forms.CharField(label='Product Type', max_length=100)
    grade = forms.CharField(label='Grade', max_length=20)
    size = forms.FloatField(label='Size')
    unit = forms.CharField(label='Unit', max_length=20)
    weight_kg_each = forms.FloatField(label='Unit Weight (kg)')
