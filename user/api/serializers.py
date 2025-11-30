from rest_framework import serializers
from django.contrib.auth.models import User, Group

class UserCreateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=['Master-Admin','Admin', 'Member', 'Sale'], write_only=True)

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

