from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from products.models import ProductItem
from purchase.models import PurchaseInvoice, PurchaseItem
from common.models import Tax
from inventory.models import Stock

class AddStockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Required fields for PurchaseItem
        product_item_id = request.data.get('product_item_id')
        qty = request.data.get('qty')
        unit_price_usd = request.data.get('unit_price_usd')
        unit_price_aed = request.data.get('unit_price_aed')
        tax_id = request.data.get('tax_id')
        tax = None

        # Validate required fields
        if not all([product_item_id, qty, unit_price_usd, unit_price_aed]):
            return Response({'error': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_item = ProductItem.objects.get(id=product_item_id)
        except ProductItem.DoesNotExist:
            return Response({'error': 'ProductItem not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            if tax_id:
                tax = Tax.objects.get(id=tax_id)
        except Tax.DoesNotExist:
            return Response({'error': 'Tax not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Create PurchaseItem (stock will update via model logic)
        purchase_item = PurchaseItem.objects.create(
            invoice=None,
            item=product_item,
            qty=int(qty),
            unit_price_usd=unit_price_usd,
            unit_price_aed=unit_price_aed,
            tax=tax,
            created_by=request.user,
            modified_by=request.user,
        )

        return Response({
            'purchase_item_id': purchase_item.id,
            'product_item_id': product_item.id,
            'qty': purchase_item.qty,
            'stock_quantity': purchase_item.item.stock.quantity if hasattr(purchase_item.item, 'stock') else None
        }, status=status.HTTP_201_CREATED)

class EditStockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        product_item_id = request.data.get('product_item_id')
        new_quantity = request.data.get('qty')

        # Validate required fields
        if not all([product_item_id, new_quantity is not None]):
            return Response({'error': 'Missing required fields: product_item_id and quantity.'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            product_item = ProductItem.objects.get(id=product_item_id)
        except ProductItem.DoesNotExist:
            return Response({'error': 'ProductItem not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                return Response({'error': 'Quantity cannot be negative.'},
                              status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid quantity format.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Get or create stock record
        stock, created = Stock.objects.get_or_create(
            product_item=product_item,
            defaults={'quantity': new_quantity}
        )

        if not created:
            old_quantity = stock.quantity
            stock.quantity = new_quantity
            stock.save()
        else:
            old_quantity = 0

        return Response({
            'product_item_id': product_item.id,
            'product_name': str(product_item),
            'old_quantity': old_quantity,
            'new_quantity': stock.quantity,
            'last_updated': stock.last_updated
        }, status=status.HTTP_200_OK)

