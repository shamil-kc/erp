from rest_framework import serializers
from base.models import *


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
            'entry_type', 'date', 'notes', 'payment_type'
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
