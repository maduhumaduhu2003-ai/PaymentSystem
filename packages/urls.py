from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('', views.decoder_selection, name='decoder_selection'),
    path('decoder/<int:decoder_type_id>/', views.dashboard, name='dashboard'),
    path('decoder/<int:decoder_type_id>/packages/', views.dashboard, name='packages_by_decoder'),
]