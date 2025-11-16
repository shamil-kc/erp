from django.db.models import Sum
from purchase.models import PurchaseInvoice, PurchaseItem
from sale.models import SaleInvoice, SaleItem


def get_opening_stock(item, start_date):
    purchased = PurchaseItem.objects.filter(
        item=item,
        invoice__status=PurchaseInvoice.STATUS_APPROVED,
        invoice__purchase_date__lt=start_date
    ).aggregate(total=Sum('qty'))['total'] or 0

    sold = SaleItem.objects.filter(
        item=item,
        invoice__status=SaleInvoice.STATUS_APPROVED,
        invoice__sale_date__lt=start_date
    ).aggregate(total=Sum('qty'))['total'] or 0

    return purchased - sold

def get_closing_stock(item, end_date):
    purchased = PurchaseItem.objects.filter(
        item=item,
        invoice__status=PurchaseInvoice.STATUS_APPROVED,
        invoice__purchase_date__lte=end_date
    ).aggregate(total=Sum('qty'))['total'] or 0

    sold = SaleItem.objects.filter(
        item=item,
        invoice__status=SaleInvoice.STATUS_APPROVED,
        invoice__sale_date__lte=end_date
    ).aggregate(total=Sum('qty'))['total'] or 0

    return purchased - sold
