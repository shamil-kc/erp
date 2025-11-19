from rest_framework import serializers
from products.models import *


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
    product = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    grade = ProductGradeSerializer(read_only=True)

    product_full_name = serializers.SerializerMethodField()
    class Meta:
        model = ProductItem
        fields = '__all__'

    def get_product(self, obj):
        # First try to get from direct product field
        if obj.product:
            return ProductSerializer(obj.product).data
        # Fallback to grade hierarchy for backward compatibility
        elif obj.grade and obj.grade.product_type and obj.grade.product_type.product:
            return ProductSerializer(obj.grade.product_type.product).data
        return None

    def get_product_type(self, obj):
        # First try direct product_type field
        if obj.product_type:
            return ProductTypeSerializer(obj.product_type).data
        # Fallback to grade hierarchy for backward compatibility
        elif obj.grade and obj.grade.product_type:
            return ProductTypeSerializer(obj.grade.product_type).data
        return None

    def get_product_full_name(self, obj):
        # Build name based on available data
        product_name = ''
        product_type_name = ''
        grade_name = ''

        # Get product name
        if obj.product:
            product_name = obj.product.name
        elif obj.grade and obj.grade.product_type and obj.grade.product_type.product:
            product_name = obj.grade.product_type.product.name

        # Get product type name
        if obj.product_type:
            product_type_name = obj.product_type.type_name
        elif obj.grade and obj.grade.product_type:
            product_type_name = obj.grade.product_type.type_name

        # Get grade name
        if obj.grade:
            grade_name = obj.grade.grade

        # Build full name
        parts = [product_name, product_type_name, grade_name, f"Size {obj.size}"]
        return " - ".join([part for part in parts if part])

class ProductItemCreateSerializer(serializers.Serializer):
    product = serializers.CharField()
    product_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    grade = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    size = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    unit = serializers.CharField()
    weight_kg_each = serializers.FloatField(required=False, allow_null=True)
    product_code = serializers.CharField(required=False)

class ProductItemUpdateSerializer(serializers.ModelSerializer):
    product = serializers.CharField(write_only=True, required=False)
    product_type = serializers.CharField(write_only=True, required=False)
    grade = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ProductItem
        fields = [
            'id', 'product', 'product_type', 'grade',
            'size', 'unit', 'weight_kg_each', 'product_code'
        ]

    def update(self, instance, validated_data):
        print("working")

        # Handle product update
        product_name = validated_data.pop('product', None)
        if product_name:
            product_name = product_name.strip()
            product_obj, _ = Product.objects.get_or_create(name=product_name)
            instance.product = product_obj

        # Handle product_type update
        product_type_name = validated_data.pop('product_type', None)
        if product_type_name:
            product_type_name = product_type_name.strip()
            if product_type_name:
                product_type_obj, _ = ProductType.objects.get_or_create(
                    product=instance.product,
                    type_name=product_type_name
                )
                instance.product_type = product_type_obj
            else:
                instance.product_type = None

        # Handle grade update
        grade_name = validated_data.pop('grade', None)
        if grade_name:
            grade_name = grade_name.strip()
            if grade_name and instance.product_type:
                grade_obj, _ = ProductGrade.objects.get_or_create(
                    product_type=instance.product_type,
                    grade=grade_name
                )
                instance.grade = grade_obj
            else:
                instance.grade = None

        # Update ProductItem fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class ProductItemBulkCreateSerializer(serializers.Serializer):
    items = ProductItemCreateSerializer(many=True)

    def create(self, validated_data):
        items_data = validated_data['items']
        created_items = []
        for item_data in items_data:
            # Create/get product (required)
            prod_obj, _ = Product.objects.get_or_create(name=item_data['product'].strip())

            # Create/get product type (optional)
            prodtype_obj = None
            if item_data.get('product_type') and item_data['product_type'].strip():
                prodtype_obj, _ = ProductType.objects.get_or_create(
                    product=prod_obj,
                    type_name=item_data['product_type'].strip()
                )

            # Create/get grade (optional)
            grade_obj = None
            if item_data.get('grade') and item_data['grade'].strip() and prodtype_obj:
                grade_obj, _ = ProductGrade.objects.get_or_create(
                    product_type=prodtype_obj,
                    grade=item_data['grade'].strip()
                )

            product_item_obj, created = ProductItem.objects.get_or_create(
                product=prod_obj,
                product_type=prodtype_obj,
                grade=grade_obj,
                size=item_data.get('size'),
                defaults={
                    'unit': item_data['unit'],
                    'weight_kg_each': item_data.get('weight_kg_each'),
                    'product_code': item_data.get('product_code', '').strip() or None
                }
            )
            created_items.append(product_item_obj)
        return created_items
