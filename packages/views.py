from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Package, DecoderType


@login_required
def decoder_selection(request):
    """Step 1: Choose decoder type (CANAL BI / AZAM BI)"""
    
    decoder_types = DecoderType.objects.filter(is_active=True)
    
    return render(request, 'packages/decoder_selection.html', {
        'decoder_types': decoder_types
    })


@login_required
def dashboard(request, decoder_type_id=None):
    """Step 2: Choose package for specific decoder type"""
    
    if decoder_type_id:
        decoder_type = get_object_or_404(DecoderType, id=decoder_type_id, is_active=True)
        packages = Package.objects.filter(
            decoder_type=decoder_type,
            is_active=True
        ).order_by('price')
    else:
        decoder_type = None
        packages = Package.objects.filter(is_active=True).order_by('price')
    
    return render(request, 'packages/dashboard.html', {
        'packages': packages,
        'decoder_type': decoder_type,
        'decoder_types': DecoderType.objects.filter(is_active=True),
    })