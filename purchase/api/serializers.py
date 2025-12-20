from rest_framework import serializers
from django.db import transaction
from products.api.serializers import ProductItemSerializer
from banking.api.serializers import PaymentEntrySerializer
from customer.api.serializers import PartySerializer
from purchase.models import *
from banking.models import PaymentEntry, CashAccount
from inventory.models import Stock
from common.models import ExtraCharges, ExtraPurchase
from django.contrib.contenttypes.models import ContentType


class PurchaseItemSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    party = serializers.SerializerMethodField()

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

    def get_party(self, obj):
        if obj.invoice and obj.invoice.party:
            return {'party_id':obj.invoice.party.id, 'party_name':obj.invoice.party.name}
        return None


class ExtraChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraCharges
        fields = ['id', 'amount', 'description', 'vat', 'created_at', 'modified_at', 'created_by']


class ExtraPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraPurchase
        fields = ['id', 'amount', 'description', 'vat', 'created_at', 'modified_at', 'created_by']


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    purchase_items = PurchaseItemSerializer(many=True, read_only=True)
    party = PartySerializer(read_only=True)
    party_id = serializers.PrimaryKeyRelatedField(queryset=Party.objects.all(), source='party', write_only=True)
    has_tax = serializers.BooleanField(required=False)  # Add this field
    extra_charges = ExtraChargesSerializer(many=True, read_only=True)
    extra_purchases = ExtraPurchaseSerializer(many=True, read_only=True)
    is_payment_started = serializers.BooleanField(required=False)  # <-- Add this field
    class Meta:
        model = PurchaseInvoice
        fields = '__all__'


class PurchaseItemNestedSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
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
    extra_charges = ExtraChargesSerializer(many=True, write_only=True, required=False)
    extra_purchases = ExtraPurchaseSerializer(many=True, write_only=True, required=False)
    is_payment_started = serializers.BooleanField(required=False, default=False)  # <-- Add this field

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
        fields = [
            'invoice_no', 'party_id', 'purchase_date', 'notes',
            'items', 'discount_usd', 'discount_aed', 'payments', 'has_tax',
            'has_custom_duty', 'custom_duty_usd_enter', 'custom_duty_aed_enter',
            'currency', 'currency_rate', 'status', 'extra_charges', 'extra_purchases', 'is_payment_started'
        ]  # <-- Add extra_purchases

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payments_data = validated_data.pop('payments', [])
        has_tax = validated_data.pop('has_tax', True)
        extra_charges_data = validated_data.pop('extra_charges', [])
        extra_purchases_data = validated_data.pop('extra_purchases', [])
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
                for charge in extra_charges_data:
                    ExtraCharges.objects.create(
                        content_type=ContentType.objects.get_for_model(PurchaseInvoice),
                        object_id=invoice.id,
                        amount=charge.get('amount'),
                        description=charge.get('description', ''),
                        vat=charge.get('vat', 0),
                        created_by=self.context['request'].user
                    )
                # create extra purchases if any
                for purchase in extra_purchases_data:
                    ep = ExtraPurchase.objects.create(
                        purchase_invoice=invoice,
                        amount=purchase.get('amount'),
                        description=purchase.get('description', ''),
                        vat=purchase.get('vat', 0),
                        created_by=self.context['request'].user
                    )
                    invoice.extra_purchases.add(ep)
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
    extra_charges = ExtraChargesSerializer(many=True, write_only=True, required=False)
    extra_purchases = ExtraPurchaseSerializer(many=True, write_only=True, required=False)
    is_payment_started = serializers.BooleanField(required=False, default=False)  # <-- Add this field
    class Meta:
        model = PurchaseInvoice
        fields = [
            'invoice_no', 'party_id', 'purchase_date', 'notes',
            'items', 'discount_usd', 'discount_aed', 'has_tax', 'status',
            'has_custom_duty', 'custom_duty_usd_enter', 'custom_duty_aed_enter',
            'currency', 'currency_rate', 'status', 'extra_charges', 'extra_purchases', 'is_payment_started'
        ]  # <-- Add extra_purchases

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        has_tax = validated_data.pop('has_tax', instance.has_tax)
        extra_charges_data = validated_data.pop('extra_charges', None)
        extra_purchases_data = validated_data.pop('extra_purchases', None)
        with transaction.atomic():
            # Update invoice fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.has_tax = has_tax
            instance.save()

            if items_data is not None:
                # Map existing PurchaseItems by their id
                existing_items = {item.id: item for item in instance.purchase_items.all()}
                sent_item_ids = [item.get("id") for item in items_data if item.get("id")]

                print(existing_items, "existing_items")
                print(sent_item_ids, "sent_item_ids")

                # Delete removed items
                for item_id in existing_items:
                    if item_id not in sent_item_ids:
                        existing_items[item_id].delete()

                # Create or update items
                for item_data in items_data:
                    item_id = item_data.get('id', None)
                    if item_id and item_id in existing_items:
                        # Update existing item by PurchaseItem id
                        item_instance = existing_items[item_id]
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
                # Map existing ExtraCharges by their id
                from common.models import ExtraCharges
                existing_charges = {ec.id: ec for ec in ExtraCharges.objects.filter(
                    content_type=ContentType.objects.get_for_model(PurchaseInvoice),
                    object_id=instance.id
                )}
                sent_charge_ids = [ec.get("id") for ec in extra_charges_data if ec.get("id")]

                # Delete removed extra charges
                for ec_id in existing_charges:
                    if ec_id not in sent_charge_ids:
                        existing_charges[ec_id].delete()

                # Create or update extra charges
                for charge in extra_charges_data:
                    ec_id = charge.get('id', None)
                    if ec_id and ec_id in existing_charges:
                        ec_instance = existing_charges[ec_id]
                        for attr, value in charge.items():
                            if attr == 'id':
                                continue
                            setattr(ec_instance, attr, value)
                        ec_instance.save()
                        # No need to re-add for GenericRelation
                    else:
                        ExtraCharges.objects.create(
                            content_type=ContentType.objects.get_for_model(PurchaseInvoice),
                            object_id=instance.id,
                            amount=charge.get('amount'),
                            description=charge.get('description', ''),
                            vat=charge.get('vat', 0),
                            created_by=self.context['request'].user
                        )

        if extra_purchases_data is not None:
            existing_purchases = {ep.id: ep for ep in instance.extra_purchases.all()}
            sent_purchase_ids = [ep.get("id") for ep in extra_purchases_data if ep.get("id")]

            # Delete removed extra purchases
            for ep_id in existing_purchases:
                if ep_id not in sent_purchase_ids:
                    ep = existing_purchases[ep_id]
                    instance.extra_purchases.remove(ep)
                    ep.delete()

            # Create or update extra purchases
            for purchase_data in extra_purchases_data:
                ep_id = purchase_data.get('id', None)
                if ep_id and ep_id in existing_purchases:
                    ep_instance = existing_purchases[ep_id]
                    for attr, value in purchase_data.items():
                        if attr == 'id':
                            continue
                        setattr(ep_instance, attr, value)
                    ep_instance.save()
                    # Ensure the updated instance is still in the M2M relation
                    if ep_instance not in instance.extra_purchases.all():
                        instance.extra_purchases.add(ep_instance)
                else:
                    ep = ExtraPurchase.objects.create(
                        purchase_invoice=instance,
                        amount=purchase_data.get('amount'),
                        description=purchase_data.get('description', ''),
                        vat=purchase_data.get('vat', 0),
                        created_by=self.context['request'].user
                    )
                    instance.extra_purchases.add(ep)

        instance.calculate_totals()

        return instance


class PurchaseItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = '__all__'


from purchase.models import PurchaseReturnItem, PurchaseItem

class PurchaseReturnItemEntrySerializer(serializers.ModelSerializer):
    purchase_item = serializers.PrimaryKeyRelatedField(queryset=PurchaseItem.objects.all())
    qty = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PurchaseReturnItemEntry
        fields = ['id', 'purchase_item', 'qty', 'remarks']

class PurchaseReturnItemSerializer(serializers.ModelSerializer):
    items = PurchaseReturnItemEntrySerializer(many=True, write_only=True)
    purchase_invoice = serializers.PrimaryKeyRelatedField(queryset=PurchaseInvoice.objects.all())
    returned_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PurchaseReturnItem
        fields = ['id', 'purchase_invoice', 'items', 'returned_by',
                  'return_date', 'remarks', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        validated_data['returned_by'] = self.context['request'].user
        instance = super().create(validated_data)
        total_returned_qty = 0
        total_returned_amount = 0
        for entry in items_data:
            PurchaseReturnItemEntry.objects.create(
                purchase_return=instance,
                purchase_item=entry['purchase_item'],
                qty=entry['qty'],
                remarks=entry.get('remarks', '')
            )
            total_returned_qty += entry['qty']
            amount = entry['purchase_item'].unit_price_aed * entry['qty']
            total_returned_amount += amount
        # --- Cash Transaction for Purchase Return ---
        try:
            purchase_invoice = instance.purchase_invoice
            cash_account = CashAccount.objects.first()
            if cash_account and purchase_invoice:
                # Deposit the returned amount to the cash account
                amount = total_returned_amount
                if amount:
                    cash_account.deposit(
                        amount,
                        'cash_in_bank',
                        created_by=self.context['request'].user,
                        note=f"Purchase Return #{instance.id} for Invoice #{purchase_invoice.id}"
                    )
        except Exception as e:
            pass
        return instance

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            # Remove entries not in update
            sent_entry_ids = [entry.get('id') for entry in items_data if entry.get('id')]
            for entry in instance.entries.all():
                if entry.id not in sent_entry_ids:
                    entry.delete()
            # Update or create entries
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
                    PurchaseReturnItemEntry.objects.create(
                        purchase_return=instance,
                        purchase_item=entry_data['purchase_item'],
                        qty=entry_data['qty'],
                        remarks=entry_data.get('remarks', '')
                    )
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'] = PurchaseReturnItemEntrySerializer(instance.entries.all(), many=True).data
        return data
