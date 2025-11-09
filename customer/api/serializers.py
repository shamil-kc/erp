from rest_framework import serializers
from base.models import *


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = '__all__'