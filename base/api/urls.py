# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.api.views_api import *
from employee.api.views_api import *
from customer.api.views_api import *
from purchase.api.views_api import *
from sale.api.views_api import *
from report.api.views_api import *
from common.api.views_api import *
from banking.api.views_api import *
from user.api.views_api import *
from inventory.api.views_api import *

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
router.register(r'assets', AssetViewSet)
router.register(r'sale-returns', SaleReturnItemViewSet, basename='sale-return')
router.register(r'purchase-returns', PurchaseReturnItemViewSet, basename='purchase-return')
router.register(r'delivery-notes', DeliveryNoteViewSet)

router.register(r'account-transfer', CashAccountTransferViewSet)

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
    path('check-approve/', CheckApproveAPIView.as_view(), name='check-approve'),
    path('reminders/', RemindersAPIView.as_view(), name='reminders'),
    path('add-stock/', AddStockAPIView.as_view(), name='add-stock'),
    path('edit-stock/', EditStockAPIView.as_view(), name='edit-stock'),
    path('generate-perfoma-invoice-number/', generate_perfoma_invoice_number_api,
         name='generate-perfoma-invoice-number'),


]
