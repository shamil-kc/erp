from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from products.models import ProductItem
from purchase.models import PurchaseInvoice, PurchaseItem
from common.models import Tax

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
