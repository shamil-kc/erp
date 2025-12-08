from rest_framework import serializers
from banking.models import PaymentEntry, CashAccountTransfer


class PaymentEntrySerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    modified_by = serializers.ReadOnlyField(source='modified_by.username')

    class Meta:
        model = PaymentEntry
        fields = [
            'id',
            'invoice_id',
            'invoice_type',
            'payment_type',
            'amount',
            'created_by',
            'modified_by',
            'charges',
            'party',
            'cheque_number',
            'payment_date',
            'cheque_cleared_date'
        ]
        read_only_fields = ['created_by', 'modified_by', 'modified_at']


class CashAccountTransferSerializer(serializers.ModelSerializer):
    from_account_type = serializers.ReadOnlyField(source='from_account.type')
    to_account_type = serializers.ReadOnlyField(source='to_account.type')
    created_by = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = CashAccountTransfer
        fields = [
            'id', 'from_account', 'from_account_type', 'from_type',
            'to_account', 'to_account_type', 'to_type',
            'amount', 'created_by', 'created_at', 'note', "transfer_date"
        ]
        read_only_fields = ['created_by', 'created_at']
