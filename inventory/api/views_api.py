from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from products.api.serializers import ProductItemCreateSerializer
from products.models import ProductItem
from inventory.models import Stock

class AddStockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        product_item_id = request.data.get('product_item_id')
        quantity = request.data.get('quantity')

        # Fetch product item by ID
        try:
            product_item = ProductItem.objects.get(id=product_item_id)
        except ProductItem.DoesNotExist:
            return Response({'error': 'ProductItem not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Create or update stock
        stock, created = Stock.objects.get_or_create(product_item=product_item)
        stock.quantity += int(quantity)
        stock.save()

        return Response({
            'product': product_item.id,
            'quantity': stock.quantity
        }, status=status.HTTP_201_CREATED)
