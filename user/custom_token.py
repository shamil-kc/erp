from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from datetime import timedelta
from django.utils import timezone

TOKEN_TTL_HOURS = 24


class ExpiringTokenAuthentication(TokenAuthentication):

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        # expiry check
        expiry_time = token.created + timedelta(hours=TOKEN_TTL_HOURS)
        if timezone.now() > expiry_time:
            token.delete()
            raise AuthenticationFailed("Token expired. Please log in again.")

        return (user, token)
