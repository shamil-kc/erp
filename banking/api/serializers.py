from rest_framework import serializers
from banking.models import PaymentEntry


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
        ]
        read_only_fields = ['created_by', 'modified_by', 'modified_at']