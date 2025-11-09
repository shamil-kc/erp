from .serializers import *
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import generics, permissions
from django.contrib.auth.models import User


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        roles = list(user.groups.values_list('name', flat=True))  # example with Groups as roles
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'roles': roles
        })


class UserCreateAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]  # or restrict as needed


class IsAdminUser(permissions.BasePermission):
    """Allow only admin users (is_staff=True)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsEmployeeUser(permissions.BasePermission):
    """Allow only employee users (is_staff=False)."""
    def has_permission(self, request, view):
        return request.user and not request.user.is_staff
