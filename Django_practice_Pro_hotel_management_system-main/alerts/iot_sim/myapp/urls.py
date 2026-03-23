from django.urls import path
from . import views

urlpatterns = [
    path('iot-data/', views.receive_iot_data),
    path('get-iot-data/', views.get_iot_data),
]