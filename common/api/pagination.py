from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            'total': self.page.paginator.count,
            'per_page': self.page_size,
            'current_page_count': len(data),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'data': data
        })
