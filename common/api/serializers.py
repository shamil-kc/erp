from rest_framework import serializers
from common.models import *
from customer.models import Party


class ServiceFeeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    sales_invoice = serializers.SerializerMethodField()

    class Meta:
        model = ServiceFee
        fields = '__all__'

    def get_sales_invoice(self, obj):
        id = obj.sales_invoice.id if obj.sales_invoice else None
        invoice_no = obj.sales_invoice.invoice_no if obj.sales_invoice else None
        return {'id': id, 'invoice_no': invoice_no} if id and invoice_no else None

class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = '__all__'


class ServiceFeeNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFee
        fields = ['id', 'description', 'amount_usd', 'amount_aed']


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
                  'is_shown', 'payment_type']

class WageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wage
        fields = ['id', 'amount_aed',
                  'date', 'notes',  'payment_type']

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'

class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = ['id', 'name', 'type']

class AssetSaleSerializer(serializers.ModelSerializer):
    asset = AssetSerializer(read_only=True)
    asset_id = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.all(), write_only=True, source='asset'
    )
    party = PartySerializer(read_only=True)
    party_id = serializers.PrimaryKeyRelatedField(
        queryset=Party.objects.all(), write_only=True, source='party', required=False, allow_null=True
    )

    class Meta:
        model = AssetSale
        fields = [
            'id', 'asset', 'asset_id', 'sale_price', 'sale_date', 'notes',
            'payment_type', 'vat', 'party', 'party_id'
        ]
