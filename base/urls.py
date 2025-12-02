from django.urls import path, include
from . import views

urlpatterns = [
    path('api/report/', include('report.api.urls')),
    path('api/', include('base.api.urls')),


]
