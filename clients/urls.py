from . import views
from django.urls import path
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    path('dashboard/',views.dashboard),
    path('api/register/', views.NodeRegister.as_view()),
    path('api/login/', views.NodeLogin.as_view()),
    path('api/token/refresh/',TokenRefreshView.as_view(),name ='refresh_token'),
    path('api/metrics/', views.MetricsData.as_view()),

]