from . import views
from django.urls import path

urlpatterns = [
    path('dashboard/',views.dashboard),
    path('api/register/', views.NodeRegister.as_view()),
    path('api/login/', views.NodeLogin.as_view()),
    path('api/metrics/', views.Metrics.as_view()),

]