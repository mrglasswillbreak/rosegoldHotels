from django.urls import path

from . import views


urlpatterns = [
    path("iot-data/", views.receive_iot_data, name="receive_iot_data"),
    path("get-iot-data/", views.get_iot_data, name="get_iot_data"),
    path("monitoring/iot/", views.iot_monitoring_dashboard, name="iot_monitoring_dashboard"),
    path("monitoring/iot/feed/", views.iot_monitoring_feed, name="iot_monitoring_feed"),
    path("monitoring/iot/simulate/", views.force_simulation_cycle, name="force_simulation_cycle"),
    path("monitoring/alerts/", views.iot_alert_center, name="iot_alert_center"),
    path("monitoring/alerts/<int:alert_id>/acknowledge/", views.acknowledge_iot_alert, name="acknowledge_iot_alert"),
    path("monitoring/alerts/<int:alert_id>/resolve/", views.resolve_iot_alert, name="resolve_iot_alert"),
]
