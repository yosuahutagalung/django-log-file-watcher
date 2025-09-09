from django.urls import path

from app import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('log/<int:log_id>', views.LogDetailView.as_view(), name='log_detail'),
]