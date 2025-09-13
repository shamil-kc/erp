from rest_framework import serializers
from base.models import *
from rest_framework import permissions


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = '__all__'

class ProductGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGrade
        fields = '__all__'

class ProductItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductItem
        fields = '__all__'

class ProductItemCreateSerializer(serializers.Serializer):
    product = serializers.CharField()
    product_type = serializers.CharField()
    grade = serializers.CharField()
    size = serializers.FloatField()
    unit = serializers.CharField()
    weight_kg_each = serializers.FloatField()

class ProductItemBulkCreateSerializer(serializers.Serializer):
    items = ProductItemCreateSerializer(many=True)

    def create(self, validated_data):
        items_data = validated_data['items']
        created_items = []
        for item_data in items_data:
            prod_obj, _ = Product.objects.get_or_create(name=item_data['product'].strip())
            prodtype_obj, _ = ProductType.objects.get_or_create(product=prod_obj, type_name=item_data['product_type'].strip())
            grade_obj, _ = ProductGrade.objects.get_or_create(product_type=prodtype_obj, grade=item_data['grade'].strip())
            product_item_obj, created = ProductItem.objects.get_or_create(
                grade=grade_obj,
                size=item_data['size'],
                unit=item_data['unit'],
                weight_kg_each=item_data['weight_kg_each'],
            )
            created_items.append(product_item_obj)
        return created_items


class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = '__all__'

class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    purchase_items = PurchaseItemSerializer(many=True, read_only=True)
    class Meta:
        model = PurchaseInvoice
        fields = '__all__'

class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = '__all__'

class SaleInvoiceSerializer(serializers.ModelSerializer):
    sale_items = SaleItemSerializer(many=True, read_only=True)
    class Meta:
        model = SaleInvoice
        fields = '__all__'

class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = '__all__'

class ExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = '__all__'

class ExpenseSerializer(serializers.ModelSerializer):
    type = ExpenseTypeSerializer()
    class Meta:
        model = Expense
        fields = '__all__'

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'

class SalaryEntrySerializer(serializers.ModelSerializer):
    account = AccountSerializer()
    class Meta:
        model = SalaryEntry
        fields = '__all__'
