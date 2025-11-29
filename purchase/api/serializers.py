from rest_framework import serializers
from django.db import transaction
from products.api.serializers import ProductItemSerializer
from banking.api.serializers import PaymentEntrySerializer
from customer.api.serializers import PartySerializer
from purchase.models import *
from banking.models import PaymentEntry
from inventory.models import Stock
from common.models import ExtraCharges
from django.contrib.contenttypes.models import ContentType


class PurchaseItemSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    class Meta:
        model = PurchaseItem
        fields = '__all__'

    def get_item(self, obj):
        if obj.item:
            data = {'product_id': obj.item.id,
                    'product_full_name': ProductItemSerializer().get_product_full_name(obj.item)}
            return data
        return None

    def get_invoice_id(self, obj):
        if obj.invoice:
            return obj.invoice.id
        return None


class ExtraChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraCharges
        fields = ['id', 'amount', 'created_at', 'modified_at', 'created_by']


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    purchase_items = PurchaseItemSerializer(many=True, read_only=True)
    party = PartySerializer(read_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party', write_only=True)
    has_tax = serializers.BooleanField(required=False)  # Add this field
    extra_charges = ExtraChargesSerializer(many=True, read_only=True)
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
    shipping_total_usd = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    shipping_total_aed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    factors = serializers.CharField(allow_blank=True, required=False)
    tax = serializers.IntegerField(required=False)
    amount_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_aed = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    custom_duty_usd_enter = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    custom_duty_aed_enter = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)


class PurchaseInvoiceCreateSerializer(serializers.ModelSerializer):
    items = PurchaseItemNestedSerializer(many=True, write_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)
    has_custom_duty = serializers.BooleanField(required=False, default=False)
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    custom_duty_usd_enter = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    custom_duty_aed_enter = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    payments = PaymentEntrySerializer(many=True, write_only=True, required=False)
    currency = serializers.CharField(required=False, allow_blank=True)
    currency_rate = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    status = serializers.ChoiceField(choices=PurchaseInvoice.STATUS_CHOICES, required=False)
    extra_charges = serializers.ListField(child=serializers.DecimalField(max_digits=14, decimal_places=2), required=False)

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
                  'items', 'discount_usd', 'discount_aed', 'payments', 'has_tax',
                  'has_custom_duty', 'custom_duty_usd_enter', 'custom_duty_aed_enter',
                  'currency', 'currency_rate', 'status', 'extra_charges']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payments_data = validated_data.pop('payments', [])
        has_tax = validated_data.pop('has_tax', True)
        extra_charges_data = validated_data.pop('extra_charges', [])
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
                        shipping_total_usd=item.get('shipping_total_usd', 0),
                        shipping_total_aed=item.get('shipping_total_aed', 0),
                        factors=item.get('factors', ''),
                        tax_id=item.get('tax'),
                        amount_usd=item.get('amount_usd'),
                        amount_aed=item.get('amount_aed'),
                        vat_amount=item.get('vat_amount'),
                        custom_duty_usd_enter=item.get('custom_duty_usd_enter', 0),
                        custom_duty_aed_enter=item.get('custom_duty_aed_enter', 0)
                    )
                # create extra charges if any
                for amount in extra_charges_data:
                    ExtraCharges.objects.create(
                        content_type=ContentType.objects.get_for_model(PurchaseInvoice),
                        object_id=invoice.id,
                        amount=amount,
                        created_by=self.context['request'].user
                    )
                invoice.calculate_totals()
            except Exception as e:
                transaction.set_rollback(True)
                raise e

        return invoice

class PurchaseInvoiceUpdateSerializer(serializers.ModelSerializer):
    items = PurchaseItemNestedSerializer(many=True, write_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)
    has_custom_duty = serializers.BooleanField(required=False, default=False)
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            required=False, default=0)
    custom_duty_usd_enter = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    custom_duty_aed_enter = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(required=False, allow_blank=True)
    currency_rate = serializers.DecimalField(max_digits=12, decimal_places=2,
                                             required=False)
    status = serializers.ChoiceField(choices=PurchaseInvoice.STATUS_CHOICES,
                                     required=False)
    extra_charges = serializers.ListField(child=serializers.DecimalField(max_digits=14, decimal_places=2), required=False)
    class Meta:
        model = PurchaseInvoice
        fields = ['invoice_no', 'party_id', 'purchase_date', 'notes',
                  'items', 'discount_usd', 'discount_aed', 'has_tax', 'status',
                  'has_custom_duty', 'custom_duty_usd_enter', 'custom_duty_aed_enter',
                  'currency', 'currency_rate', 'status', 'extra_charges']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        has_tax = validated_data.pop('has_tax', instance.has_tax)
        extra_charges_data = validated_data.pop('extra_charges', None)
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
                        PurchaseItem.objects.create(
                            invoice=instance,
                            item_id=item_data.get('item'),
                            qty=item_data.get('qty'),
                            unit_price_usd=item_data.get('unit_price_usd'),
                            unit_price_aed=item_data.get('unit_price_aed'),
                            shipping_per_unit_usd=item_data.get('shipping_per_unit_usd', 0),
                            shipping_per_unit_aed=item_data.get('shipping_per_unit_aed', 0),
                            shipping_total_usd=item_data.get('shipping_total_usd', 0),
                            shipping_total_aed=item_data.get('shipping_total_aed', 0),
                            factors=item_data.get('factors', ''),
                            tax_id=item_data.get('tax'),
                            amount_usd=item_data.get('amount_usd'),
                            amount_aed=item_data.get('amount_aed'),
                            vat_amount=item_data.get('vat_amount'),
                            custom_duty_usd_enter=item_data.get('custom_duty_usd_enter', 0),
                            custom_duty_aed_enter=item_data.get('custom_duty_aed_enter', 0)
                        )

            if extra_charges_data is not None:
                ExtraCharges.objects.filter(
                    content_type=ContentType.objects.get_for_model(PurchaseInvoice),
                    object_id=instance.id
                ).delete()
                for amount in extra_charges_data:
                    ExtraCharges.objects.create(
                        content_type=ContentType.objects.get_for_model(PurchaseInvoice),
                        object_id=instance.id,
                        amount=amount,
                        created_by=self.context['request'].user
                    )

            instance.calculate_totals()

        return instance


class PurchaseItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = '__all__'


from purchase.models import PurchaseReturnItem, PurchaseItem

class PurchaseReturnItemSerializer(serializers.ModelSerializer):
    purchase_item = serializers.PrimaryKeyRelatedField(queryset=PurchaseItem.objects.all())

    class Meta:
        model = PurchaseReturnItem
        fields = ['id', 'purchase_item', 'purchase_invoice', 'qty', 'returned_by',
                  'return_date', 'remarks', 'created_at']

    def create(self, validated_data):
        validated_data['returned_by'] = self.context['request'].user
        return super().create(validated_data)
