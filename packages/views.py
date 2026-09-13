from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Package, DecoderType


@login_required
def decoder_selection(request):
    """Step 1: Choose decoder type"""
    
    decoder_types = DecoderType.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'packages/decoder_selection.html', {
        'decoder_types': decoder_types
    })


@login_required
def packages_by_decoder(request, decoder_type_id):
    """Step 2: View packages for selected decoder type"""
    
    decoder_type = get_object_or_404(DecoderType, id=decoder_type_id, is_active=True)
    packages = Package.objects.filter(
        decoder_type=decoder_type,
        is_active=True
    ).order_by('price')
    
    return render(request, 'packages/dashboard.html', {
        'decoder_type': decoder_type,
        'packages': packages,
    })