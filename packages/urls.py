from django.urls import path
from . import views

urlpatterns = [
    # Step 1: Decoder selection
    path('', views.decoder_selection, name='decoder_selection'),
    
    # Step 2: Packages for decoder
    path('decoder/<int:decoder_type_id>/', views.packages_by_decoder, name='packages_by_decoder'),
]