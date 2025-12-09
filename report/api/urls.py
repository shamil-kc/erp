from django.urls import path
from .views_api import *

urlpatterns = [
    path('productwise/', ProductWiseReportAPIView.as_view() ),
    path('monthly-report/', YearlySummaryReportAPIView.as_view() ),


]
