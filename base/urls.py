from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/', include('base.api.urls')),
    path('products/', views.product_list, name='product-list'),
    path('inventory/', views.inventory_report, name='inventory-report'),
    path('sales/', views.sales_report, name='sales-report'),
    path('invoice/<int:invoice_id>/', views.generate_invoice, name='generate-invoice'),
    path('reports/profit-tax/', views.profit_and_corporate_tax_report, name='profit-tax-report'),
    path('products/add/', views.product_item_add, name='product-item-add'),
    path('purchases/', views.purchase_report, name='purchase-report'),
    path('products/api/get_or_create/', views.get_or_create_product_related, name='erp-get-or-create-product-related'),
    path('products/delete/<int:pk>/', views.product_item_delete, name='product-item-delete'),
    path('purchase/add/', views.purchase_invoice_add, name='purchase-add'),
    path('sales/add/', views.sales_add, name='sales-add'),
    path('expense/add/', views.expense_add, name='expense-add'),
    path('expense/list/', views.expense_list, name='expense-list'),
    path('salary/add/', views.salary_add, name='salary-add'),
    path('salary/list/', views.salary_list, name='salary-list'),


]
