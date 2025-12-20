from rest_framework import serializers
from django.db import transaction
from products.api.serializers import ProductItemSerializer
from customer.api.serializers import PartySerializer
from common.api.serializers import (ServiceFeeSerializer,
    ServiceFeeNestedSerializer, CommissionSerializer)
from banking.api.serializers import PaymentEntrySerializer
from sale.models import *
from purchase.models import PurchaseItem
from banking.models import PaymentEntry, CashAccount
from common.models import ServiceFee,Commission, ExtraCharges
from django.contrib.contenttypes.models import ContentType


class SaleItemSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    purchase_item = serializers.SerializerMethodField()
    delivery_status = serializers.CharField()

    class Meta:
        model = SaleItem
        fields = '__all__'

    def get_item(self, obj):
        if obj.item:
            data = {'product_id': obj.item.id,
                    'product_full_name': ProductItemSerializer().get_product_full_name(
                        obj.item),
                    'product_unit': obj.item.unit}
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
    delivery_status = serializers.ChoiceField(
        choices=SaleItem.DELIVERY_STATUS_CHOICES,
        required=False,
        default=SaleItem.DELIVERY_STATUS_NOT_DELIVERED
    ),
    amount_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_aed = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class ExtraChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraCharges
        fields = ['id', 'amount', 'description', 'vat', 'created_at', 'modified_at', 'created_by']

class SaleInvoiceSerializer(serializers.ModelSerializer):
    sale_items = SaleItemSerializer(many=True, read_only=True)
    party = PartySerializer(read_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party', write_only=True)
    service_fees = ServiceFeeSerializer(many=True, read_only=True)
    commissions = CommissionSerializer(many=True, read_only=True)
    has_tax = serializers.BooleanField(required=False)
    is_sales_approved = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=SaleInvoice.STATUS_CHOICES, required=False)
    is_payment_started = serializers.BooleanField(required=False)  # <-- Add this field
    # Fix: Use .all() for GenericRelation
    extra_charges = serializers.SerializerMethodField()
    sale_note = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.CharField(required=False, allow_blank=True)  # <-- Added field

    class Meta:
        model = SaleInvoice
        fields = '__all__'

    def get_extra_charges(self, obj):
        return ExtraChargesSerializer(obj.extra_charges.all(), many=True).data

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
    extra_charges = ExtraChargesSerializer(many=True, write_only=True, required=False)
    status = serializers.ChoiceField(choices=SaleInvoice.STATUS_CHOICES, required=False)
    is_sales_approved = serializers.BooleanField(required=False)
    biller_name = serializers.CharField(required=False, allow_blank=True)
    is_payment_started = serializers.BooleanField(required=False, default=False)  # <-- Add this field
    sale_note = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.CharField(required=False, allow_blank=True)  # <-- Added field

    class Meta:
        model = SaleInvoice
        fields = [
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
            'is_sales_approved',
            'biller_name',
            'purchase_order_number',
            'invoice_no',
            'extra_charges',
            'is_payment_started',  # <-- Add here
            'sale_note',  # <-- Add here
            'payment_method',  # <-- Add here
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
        extra_charges_data = validated_data.pop('extra_charges', [])

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
                purchase_item=item.get('purchase_item'),
                amount_usd=item.get('amount_usd'),
                amount_aed=item.get('amount_aed'),
                vat_amount=item.get('vat_amount')
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

        # create extra charges if any
        for charge in extra_charges_data:
            ExtraCharges.objects.create(
                content_type=ContentType.objects.get_for_model(SaleInvoice),
                object_id=invoice.id,
                amount=charge.get('amount'),
                description=charge.get('description', ''),
                vat=charge.get('vat', 0),
                created_by=self.context['request'].user
            )
        return invoice

class SaleInvoiceUpdateSerializer(serializers.ModelSerializer):
    items = SaleItemNestedSerializer(many=True, write_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party')
    has_tax = serializers.BooleanField(required=False, default=True)
    discount_usd = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    discount_aed = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    has_service_fee = serializers.BooleanField(write_only=True, default=False)
    service_fee = ServiceFeeNestedSerializer(write_only=True, required=False)
    has_commission = serializers.BooleanField(write_only=True, default=False)
    commission = CommissionSerializer(write_only=True, required=False)
    # Fix: Use correct serializer for extra_charges
    extra_charges = ExtraChargesSerializer(many=True, required=False)
    status = serializers.ChoiceField(choices=SaleInvoice.STATUS_CHOICES, required=False)
    is_sales_approved = serializers.BooleanField(required=False)
    biller_name = serializers.CharField(required=False, allow_blank=True)
    is_payment_started = serializers.BooleanField(required=False, default=False)  # <-- Add this field
    sale_note = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.CharField(required=False, allow_blank=True)  # <-- Added field

    class Meta:
        model = SaleInvoice
        fields = ['party_id', 'sale_date', 'discount_usd',
                  'discount_aed', 'items','has_service_fee', 'service_fee',
                  'has_commission', 'commission', 'has_tax', 'status',
                  'is_sales_approved', 'biller_name', 'purchase_order_number',
                  'invoice_no', 'extra_charges', 'is_payment_started',
                  'sale_note',  # <-- Add here
                  'payment_method',  # <-- Add here
        ]

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        has_service_fee = validated_data.pop('has_service_fee', False)
        service_fee_data = validated_data.pop('service_fee', None)
        has_commission = validated_data.pop('has_commission', False)
        commission_data = validated_data.pop('commission', None)
        has_tax = validated_data.pop('has_tax', instance.has_tax)
        extra_charges_data = validated_data.pop('extra_charges', None)
        is_payment_started = validated_data.pop('is_payment_started', False)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.has_tax = has_tax
            instance.is_payment_started = is_payment_started  # <-- Update this field
            instance.save()

            if items_data is not None:
                existing_ids = [item.id for item in instance.sale_items.all()]
                sent_ids = [item.get('id') for item in items_data if item.get('id')]

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
                            purchase_item=item_data.get('purchase_item'),
                            amount_usd=item_data.get('amount_usd'),
                            amount_aed=item_data.get('amount_aed'),
                            vat_amount=item_data.get('vat_amount')
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

            if extra_charges_data is not None:
                # Remove old, add new
                ExtraCharges.objects.filter(
                    content_type=ContentType.objects.get_for_model(SaleInvoice),
                    object_id=instance.id
                ).delete()
                for charge in extra_charges_data:
                    ExtraCharges.objects.create(
                        content_type=ContentType.objects.get_for_model(SaleInvoice),
                        object_id=instance.id,
                        amount=charge.get('amount'),
                        description=charge.get('description', ''),
                        vat=charge.get('vat', 0),
                        created_by=self.context['request'].user
                    )

            instance.calculate_totals()
        return instance


class SaleReturnItemEntrySerializer(serializers.ModelSerializer):
    sale_item = serializers.PrimaryKeyRelatedField(queryset=SaleItem.objects.all())
    qty = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = SaleReturnItemEntry
        fields = ['id', 'sale_item', 'qty', 'remarks']

class SaleReturnItemSerializer(serializers.ModelSerializer):
    items = SaleReturnItemEntrySerializer(many=True, write_only=True)
    sale_invoice = serializers.PrimaryKeyRelatedField(queryset=SaleInvoice.objects.all())
    returned_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SaleReturnItem
        fields = ['id', 'sale_invoice', 'items', 'returned_by',
                  'return_date', 'remarks', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        validated_data['returned_by'] = self.context['request'].user
        instance = super().create(validated_data)
        total_return_amount = 0
        for entry in items_data:
            SaleReturnItemEntry.objects.create(
                sale_return=instance,
                sale_item=entry['sale_item'],
                qty=entry['qty'],
                remarks=entry.get('remarks', '')
            )
            total_return_amount += entry['sale_item'].sale_price_aed * entry['qty']
        # --- Cash Transaction for Sale Return ---
        try:
            sale_invoice = instance.sale_invoice
            # Use the first/main cash account
            cash_account = CashAccount.objects.first()
            if cash_account and sale_invoice:
                # Withdraw the returned amount from the cash account
                # You may want to use sale_invoice.total_with_vat_aed or similar
                amount = total_return_amount
                if amount:
                    cash_account.withdraw(
                        amount,
                        'cash_in_bank',
                        # account_type
                        created_by=self.context['request'].user,
                        note=f"Sale Return #{instance.id} for Invoice #{sale_invoice.id}"
                    )
        except Exception as e:
            print(f"Error processing cash transaction for sale return: {e}")
        # --- End Cash Transaction ---
        return instance

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            sent_entry_ids = [entry.get('id') for entry in items_data if entry.get('id')]
            for entry in instance.entries.all():
                if entry.id not in sent_entry_ids:
                    entry.delete()
            for entry_data in items_data:
                entry_id = entry_data.get('id')
                if entry_id:
                    entry_instance = instance.entries.get(id=entry_id)
                    for attr, value in entry_data.items():
                        if attr == 'id':
                            continue
                        setattr(entry_instance, attr, value)
                    entry_instance.save()
                else:
                    SaleReturnItemEntry.objects.create(
                        sale_return=instance,
                        sale_item=entry_data['sale_item'],
                        qty=entry_data['qty'],
                        remarks=entry_data.get('remarks', '')
                    )
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'] = SaleReturnItemEntrySerializer(instance.entries.all(), many=True).data
        return data


class DeliveryNoteSerializer(serializers.ModelSerializer):
    sale_items = SaleItemSerializer(many=True, read_only=True)
    sale_invoice = SaleInvoiceSerializer(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DeliveryNote
        fields = ['id', 'DO_id', 'sale_items', 'sale_invoice', 'created_at', 'created_by']
