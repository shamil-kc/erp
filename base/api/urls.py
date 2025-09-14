# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import *
from rest_framework.authtoken import views

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'product-types', ProductTypeViewSet)
router.register(r'product-grades', ProductGradeViewSet)
router.register(r'product-items', ProductItemViewSet)
router.register(r'purchase-invoices', PurchaseInvoiceViewSet)
router.register(r'purchase-items', PurchaseItemViewSet)
router.register(r'sale-invoices', SaleInvoiceViewSet)
router.register(r'sale-items', SaleItemViewSet)
router.register(r'taxes', TaxViewSet)
router.register(r'expense-types', ExpenseTypeViewSet)
router.register(r'expenses', ExpenseViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'salary-entries', SalaryEntryViewSet)

# For reports:
from .views_api import InventoryReportAPIView

urlpatterns = [
    path('', include(router.urls)),
    path('inventory-report/', InventoryReportAPIView.as_view()),
    path('api-token-auth/', CustomAuthToken.as_view()),
    path('api-token-auth/users/', UserCreateAPIView.as_view(), name='user-create'),
    path('product/bulk-create/', ProductItemBulkCreateAPIView.as_view(),
         name='productitem-bulk-create'),
]
