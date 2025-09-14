from rest_framework import serializers
from base.models import *
from rest_framework import permissions
from django.db import transaction


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
        product = obj.grade.product_type.product
        return ProductSerializer(product).data if product else None

    def get_product_type(self, obj):
        product_type = obj.grade.product_type
        return ProductTypeSerializer(product_type).data if product_type else None

    def get_product_full_name(self, obj):
        tree = obj.grade
        product_name = tree.product_type.product.name if tree and tree.product_type and tree.product_type.product else ''
        product_type_name = tree.product_type.type_name if tree and tree.product_type else ''
        grade_name = tree.grade if tree else ''
        size = obj.size
        return f"{product_name} - {product_type_name} - {grade_name} - Size {size}"

class ProductItemCreateSerializer(serializers.Serializer):
    product = serializers.CharField()
    product_type = serializers.CharField()
    grade = serializers.CharField()
    size = serializers.FloatField()
    unit = serializers.CharField()
    weight_kg_each = serializers.FloatField()


class ProductItemUpdateSerializer(serializers.ModelSerializer):
    product = serializers.CharField(write_only=True, required=False)
    product_type = serializers.CharField(write_only=True, required=False)
    grade = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ProductItem
        fields = [
            'id', 'product', 'product_type', 'grade',
            'size', 'unit', 'weight_kg_each', 'grade'  # keep original FK for backward compatibility
        ]

    def update(self, instance, validated_data):
        # Related model edits
        grade_obj = instance.grade  # ProductGrade object
        prodtype_obj = grade_obj.product_type  # ProductType object
        prod_obj = prodtype_obj.product  # Product object

        # Update Product name if provided
        product_name = validated_data.pop('product', None)
        if product_name:
            product_name = product_name.strip()
            if prod_obj.name != product_name:
                # Check if name already exists; you could also enforce unique here
                prod_obj.name = product_name
                prod_obj.save()

        # Update ProductType name if provided
        product_type_name = validated_data.pop('product_type', None)
        if product_type_name:
            product_type_name = product_type_name.strip()
            if prodtype_obj.type_name != product_type_name:
                prodtype_obj.type_name = product_type_name
                prodtype_obj.save()

        # Update Grade if provided
        grade_name = validated_data.pop('grade', None)
        if grade_name:
            grade_name = grade_name.strip()
            if grade_obj.grade != grade_name:
                grade_obj.grade = grade_name
                grade_obj.save()

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


class PurchaseItemNestedSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    qty = serializers.IntegerField()
    unit_price_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_price_aed = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping_per_unit_usd = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    shipping_per_unit_aed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    factors = serializers.CharField(allow_blank=True, required=False)
    tax = serializers.IntegerField(required=False)


class PurchaseInvoiceCreateSerializer(serializers.ModelSerializer):
    items = PurchaseItemNestedSerializer(many=True, write_only=True)

    class Meta:
        model = PurchaseInvoice
        fields = ['invoice_no', 'supplier', 'purchase_date', 'notes', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            try:
                invoice = PurchaseInvoice.objects.create(**validated_data)
                for item in items_data:
                    PurchaseItem.objects.create(
                        invoice=invoice,
                        item_id=item['item'],
                        qty=item['qty'],
                        unit_price_usd=item['unit_price_usd'],
                        unit_price_aed=item['unit_price_aed'],
                        shipping_per_unit_usd=item.get('shipping_per_unit_usd', 0),
                        shipping_per_unit_aed=item.get('shipping_per_unit_aed', 0),
                        factors=item.get('factors', ''),
                        tax_id=item.get('tax')
                    )
                invoice.calculate_totals()
            except Exception as e:
                transaction.set_rollback(True)
                raise e
        return invoice

class PurchaseInvoiceUpdateSerializer(serializers.ModelSerializer):
    items = PurchaseItemNestedSerializer(many=True, write_only=True)

    class Meta:
        model = PurchaseInvoice
        fields = ['invoice_no', 'supplier', 'purchase_date', 'notes', 'items']

    from django.db import transaction

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items',
                                        None)  # match nested field name 'items'

        with transaction.atomic():
            # Update invoice fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if items_data is not None:
                # Use correct related_name 'purchase_items'
                existing_item_ids = [item.id for item in
                                     instance.purchase_items.all()]
                sent_item_ids = [item.get('id') for item in items_data if
                                 item.get('id')]

                # Delete removed items
                for item_id in existing_item_ids:
                    if item_id not in sent_item_ids:
                        PurchaseItem.objects.filter(id=item_id).delete()

                # Create or update items
                for item_data in items_data:
                    item_id = item_data.get('id', None)
                    if item_id:
                        # Update existing item
                        item_instance = PurchaseItem.objects.get(id=item_id,
                                                                 invoice=instance)
                        for attr, value in item_data.items():
                            if attr == 'id':
                                continue
                            if attr == 'item':
                                setattr(item_instance, 'item_id', value)
                            elif attr == 'tax':
                                setattr(item_instance, 'tax_id', value)
                            else:
                                setattr(item_instance, attr, value)
                        item_instance.save()
                    else:
                        # Create new item
                        PurchaseItem.objects.create(invoice=instance,
                            item_id=item_data.get('item'),
                            qty=item_data.get('qty'),
                            unit_price_usd=item_data.get('unit_price_usd'),
                            unit_price_aed=item_data.get('unit_price_aed'),
                            shipping_per_unit_usd=item_data.get(
                                'shipping_per_unit_usd', 0),
                            shipping_per_unit_aed=item_data.get(
                                'shipping_per_unit_aed', 0),
                            factors=item_data.get('factors', ''),
                            tax_id=item_data.get('tax'))

            instance.calculate_totals()

        return instance


class PurchaseItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
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
