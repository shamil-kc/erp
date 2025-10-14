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
router.register('salary-entries', SalaryEntryViewSet)
router.register('accounts', AccountViewSet)
router.register('designations', DesignationViewSet)
router.register(r'servicefees', ServiceFeeViewSet)
router.register(r'due-payments', PaymentEntryViewSet)
router.register(r'commissions', CommissionViewSet)
router.register(r'parties', PartyViewSet)
router.register(r'employee-leaves', EmployeeLeaveViewSet)
router.register(r'wage', WageViewSet)

# For reports:
from .views_api import InventoryReportAPIView

urlpatterns = [
    path('', include(router.urls)),
    path('inventory-report/', InventoryReportAPIView.as_view()),
    path('api-token-auth/', CustomAuthToken.as_view()),
    path('api-token-auth/users/', UserCreateAPIView.as_view(), name='user-create'),
    path('product/bulk-create/', ProductItemBulkCreateAPIView.as_view(),
         name='productitem-bulk-create'),
    path('purchase-sales-report/', PurchaseSalesReportAPIView.as_view(),
         name='purchase-sales-report'),
    path('product-batch-sales-report/', ProductBatchSalesReportAPIView.as_view(), name='product-batch-sales-report'),
    path('tax-summary/', TaxSummaryAPIView.as_view(), name='tax-summary'),
    # path('reminders/', RemindersAPIView.as_view(), name='reminders'),
    path('cash-account/', CashAccountAPIView.as_view(), name='cash-account'),
]
