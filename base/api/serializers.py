from rest_framework import serializers
from base.models import *
from rest_framework import permissions
from django.db import transaction
from django.contrib.auth.models import User, Group

class UserCreateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=['Master-Admin','Admin', 'Member'], write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        role_name = validated_data.pop('role')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        group = Group.objects.get(name=role_name)
        user.groups.add(group)
        return user


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
        print("working")
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

class PaymentEntrySerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    modified_by = serializers.ReadOnlyField(source='modified_by.username')

    class Meta:
        model = PaymentEntry
        fields = ['invoice_id','invoice_type','payment_type', 'amount', 'created_by',
                  'modified_by']
        read_only_fields = ['created_by', 'modified_by', 'modified_at']


class PurchaseItemSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    class Meta:
        model = PurchaseItem
        fields = '__all__'

    def get_item(self, obj):
        if obj.item:
            data = {'product_id': obj.item.id,
                    'product_full_name': ProductItemSerializer().get_product_full_name(obj.item)}
            return data
        return None


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = '__all__'

class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    purchase_items = PurchaseItemSerializer(many=True, read_only=True)
    party = PartySerializer(read_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party', write_only=True)
    has_tax = serializers.BooleanField(required=False)  # Add this field
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
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)  # Add this field
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    payments = PaymentEntrySerializer(many=True, write_only=True, required=False)

    def validate(self, data):
        payments = data.get('payments', [])
        for payment in payments:
            if 'amount' not in payment:
                raise serializers.ValidationError(
                    "All payment entries must have an 'amount'.")
            if 'payment_type' not in payment:
                raise serializers.ValidationError(
                    "All payment entries must have a 'payment_type'.")
        total_payment = sum(float(p['amount']) for p in payments)
        total_invoice = float(data.get('total_with_vat_aed', 0)) or float(
            data.get('total_with_vat_usd', 0))
        return data

    class Meta:
        model = PurchaseInvoice
        fields = ['invoice_no', 'party_id', 'purchase_date', 'notes',
                  'items', 'discount_usd', 'discount_aed', 'payments', 'has_tax']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payments_data = validated_data.pop('payments', [])
        has_tax = validated_data.pop('has_tax', True)
        with transaction.atomic():
            try:
                invoice = PurchaseInvoice.objects.create(has_tax=has_tax, **validated_data)
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

            # create payment entries
            for payment in payments_data:
                PaymentEntry.objects.create(invoice_id=invoice.id,
                                            invoice_type='purchase',
                    payment_type=payment['payment_type'],
                    amount=payment['amount'],
                    created_by=self.context['request'].user)
        return invoice

class PurchaseInvoiceUpdateSerializer(serializers.ModelSerializer):
    items = PurchaseItemNestedSerializer(many=True, write_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)  # Add this field
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    class Meta:
        model = PurchaseInvoice
        fields = ['invoice_no', 'party_id', 'purchase_date', 'notes',
                  'items', 'discount_usd', 'discount_aed', 'has_tax', 'status']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        has_tax = validated_data.pop('has_tax', instance.has_tax)
        with transaction.atomic():
            # Update invoice fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.has_tax = has_tax
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
                            shipping_per_unit_usd=item_data.get('shipping_per_unit_usd', 0),
                            shipping_per_unit_aed=item_data.get('shipping_per_unit_aed', 0),
                            factors=item_data.get('factors', ''),
                            tax_id=item_data.get('tax'))

            instance.calculate_totals()

        return instance


class PurchaseItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = '__all__'


class ServiceFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFee
        fields = '__all__'

class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = '__all__'


class ServiceFeeNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFee
        fields = ['id', 'description', 'amount_usd', 'amount_aed']


class SaleItemSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    purchase_item = serializers.SerializerMethodField()

    class Meta:
        model = SaleItem
        fields = '__all__'

    def get_item(self, obj):
        if obj.item:
            data = {'product_id': obj.item.id,
                    'product_full_name': ProductItemSerializer().get_product_full_name(
                        obj.item)}
            return data
        return None

    def get_purchase_item(self, obj):
        if obj.purchase_item:
            return {
                'id': obj.purchase_item.id,
                'item': ProductItemSerializer().get_product_full_name(obj.purchase_item.item),
                'qty': obj.purchase_item.qty,
                'unit_price_usd': obj.purchase_item.unit_price_usd,
                'unit_price_aed': obj.purchase_item.unit_price_aed
            }
        return None

class SaleItemNestedSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    item = serializers.PrimaryKeyRelatedField(queryset=ProductItem.objects.all())
    qty = serializers.IntegerField()
    sale_price_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    sale_price_aed = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping_usd = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    shipping_aed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    # Unified field for both input (ID) and output (details)
    purchase_item = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseItem.objects.all(), required=False, allow_null=True
    )


class SaleInvoiceSerializer(serializers.ModelSerializer):
    sale_items = SaleItemSerializer(many=True, read_only=True)
    party = PartySerializer(read_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party', write_only=True)
    service_fees = ServiceFeeSerializer(many=True, read_only=True)
    commissions = CommissionSerializer(many=True, read_only=True)
    has_tax = serializers.BooleanField(required=False)
    is_sales_approved = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=SaleInvoice.STATUS_CHOICES, required=False)
    class Meta:
        model = SaleInvoice
        fields = '__all__'

class SaleInvoiceCreateSerializer(serializers.ModelSerializer):
    items = SaleItemNestedSerializer(many=True, write_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)  # Add this field
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    has_service_fee = serializers.BooleanField(write_only=True, default=False)
    service_fee = ServiceFeeNestedSerializer(write_only=True, required=False)
    has_commission = serializers.BooleanField(write_only=True, default=False)
    commission = CommissionSerializer(write_only=True, required=False)
    payments = PaymentEntrySerializer(many=True, write_only=True, required=False)
    status = serializers.ChoiceField(choices=SaleInvoice.STATUS_CHOICES, required=False)
    is_sales_approved = serializers.BooleanField(required=False)

    class Meta:
        model = SaleInvoice
        fields = [
            'invoice_no',
            'party_id',
            'sale_date',
            'items',
            'discount_usd',
            'discount_aed',
            'has_service_fee',
            'service_fee',
            'has_commission',
            'commission',
            'payments',
            'has_tax',
            'status',
            'is_sales_approved'
        ]

    def validate(self, data):
        payments = data.get('payments', [])
        for payment in payments:
            if 'amount' not in payment:
                raise serializers.ValidationError(
                    "All payment entries must have an 'amount'.")
            if 'payment_type' not in payment:
                raise serializers.ValidationError(
                    "All payment entries must have a 'payment_type'.")
        total_payment = sum(float(p['amount']) for p in payments)
        total_invoice = float(data.get('total_with_vat_aed', 0)) or float(
            data.get('total_with_vat_usd', 0))
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        has_service_fee = validated_data.pop('has_service_fee', False)
        service_fee_data = validated_data.pop('service_fee', None)
        has_commission = validated_data.pop('has_commission', False)
        commission_data = validated_data.pop('commission', None)
        payments_data = validated_data.pop('payments',[])

        invoice = SaleInvoice.objects.create(**validated_data)
        for item in items_data:
            SaleItem.objects.create(
                invoice=invoice,
                item=item['item'],
                qty=item['qty'],
                sale_price_usd=item['sale_price_usd'],
                sale_price_aed=item['sale_price_aed'],
                shipping_usd=item.get('shipping_usd', 0),
                shipping_aed=item.get('shipping_aed', 0),
                purchase_item=item.get('purchase_item')
            )

        # create service_fee if applicable
        if has_service_fee and service_fee_data:
            ServiceFee.objects.create(sales_invoice=invoice,
                **service_fee_data)
        # create commission if applicable
        if has_commission and commission_data:
            Commission.objects.create(sales_invoice=invoice, **commission_data)

        invoice.calculate_totals()

        # create payment entries
        for payment in payments_data:
            PaymentEntry.objects.create(invoice_id=invoice.id,
                                        invoice_type='sale',
                payment_type=payment['payment_type'], amount=payment['amount'],
                created_by=self.context['request'].user)
        return invoice

class SaleInvoiceUpdateSerializer(serializers.ModelSerializer):
    items = SaleItemNestedSerializer(many=True, write_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)  # Add this field
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    has_service_fee = serializers.BooleanField(write_only=True, default=False)
    service_fee = ServiceFeeNestedSerializer(write_only=True, required=False)
    has_commission = serializers.BooleanField(write_only=True, default=False)
    commission = CommissionSerializer(write_only=True, required=False)
    status = serializers.ChoiceField(choices=SaleInvoice.STATUS_CHOICES, required=False)
    is_sales_approved = serializers.BooleanField(required=False)

    class Meta:
        model = SaleInvoice
        fields = ['invoice_no', 'party_id', 'sale_date', 'discount_usd',
                  'discount_aed', 'items','has_service_fee', 'service_fee',
                  'has_commission', 'commission', 'has_tax', 'status', 'is_sales_approved']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        has_service_fee = validated_data.pop('has_service_fee', False)
        service_fee_data = validated_data.pop('service_fee', None)
        has_commission = validated_data.pop('has_commission', False)
        commission_data = validated_data.pop('commission', None)
        has_tax = validated_data.pop('has_tax', instance.has_tax)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.has_tax = has_tax
            instance.save()

            if items_data is not None:
                existing_ids = [item.id for item in instance.sale_items.all()]
                sent_ids = [item.get('id') for item in items_data if
                            item.get('id')]

                # Delete removed items
                for id in existing_ids:
                    if id not in sent_ids:
                        SaleItem.objects.filter(id=id).delete()

                for item_data in items_data:
                    item_id = item_data.get('id', None)
                    if item_id:
                        item_instance = SaleItem.objects.get(id=item_id, invoice=instance)
                        for attr, value in item_data.items():
                            if attr == 'id':
                                continue
                            if attr == 'item':
                                setattr(item_instance, 'item_id', value.id if hasattr(value, 'id') else value)
                            elif attr == 'purchase_item':
                                setattr(item_instance, 'purchase_item_id', value.id if hasattr(value, 'id') else value)
                            else:
                                setattr(item_instance, attr, value)
                        item_instance.save()
                    else:
                        SaleItem.objects.create(
                            invoice=instance,
                            item=item_data['item'],
                            qty=item_data['qty'],
                            sale_price_usd=item_data['sale_price_usd'],
                            sale_price_aed=item_data['sale_price_aed'],
                            shipping_usd=item_data.get('shipping_usd', 0),
                            shipping_aed=item_data.get('shipping_aed', 0),
                            purchase_item=item_data.get('purchase_item')
                        )
            # Handle service fee
            if has_service_fee and service_fee_data:
                service_fee_qs = ServiceFee.objects.filter(
                    sales_invoice=instance)
                if service_fee_qs.exists():
                    service_fee_obj = service_fee_qs.first()
                    for attr, value in service_fee_data.items():
                        setattr(service_fee_obj, attr, value)
                    service_fee_obj.save()
                else:
                    ServiceFee.objects.create(sales_invoice=instance,
                        **service_fee_data)
            elif not has_service_fee:
                ServiceFee.objects.filter(sales_invoice=instance).delete()

            # Handle commission
            if has_commission and commission_data:
                commission_qs = Commission.objects.filter(sales_invoice=instance)
                if commission_qs.exists():
                    commission_obj = commission_qs.first()
                    for attr, value in commission_data.items():
                        setattr(commission_obj, attr, value)
                    commission_obj.save()
                else:
                    Commission.objects.create(sales_invoice=instance, **commission_data)
            elif not has_commission:
                Commission.objects.filter(sales_invoice=instance).delete()

            instance.calculate_totals()
        return instance

class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = '__all__'

class ExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = '__all__'

class ExpenseSerializer(serializers.ModelSerializer):
    type = ExpenseTypeSerializer(read_only=True)  # nested read for output
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseType.objects.all(), write_only=True, source='type'
        # maps to model field 'type'
    )
    class Meta:
        model = Expense
        fields = ['id', 'type', 'type_id', 'amount_aed', 'amount_usd',
                  'date', 'notes', 'is_reminder_needed' , 'reminder_date',
                  'is_shown']


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = '__all__'

class AccountSerializer(serializers.ModelSerializer):
    designation = DesignationSerializer(read_only=True)
    designation_id = serializers.PrimaryKeyRelatedField(
        queryset=Designation.objects.all(),
        source='designation',
        write_only=True,
        required=False
    )

    class Meta:
        model = Account
        fields = ['id', 'name', 'designation', 'designation_id', 'notes']

class SalaryEntrySerializer(serializers.ModelSerializer):
    account = AccountSerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        source='account',
        write_only=True
    )

    class Meta:
        model = SalaryEntry
        fields = [
            'id', 'account', 'account_id', 'amount_aed', 'amount_usd',
            'entry_type', 'date', 'notes'
        ]

class EmployeeLeaveSerializer(serializers.ModelSerializer):
    account = AccountSerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all(), source='account', write_only=True)

    class Meta:
        model = EmployeeLeave
        fields = [
            'id', 'account', 'account_id', 'leave_type', 'start_date', 'end_date',
            'reason', 'approved', 'created_at', 'created_by', 'modified_at', 'modified_by'
        ]
