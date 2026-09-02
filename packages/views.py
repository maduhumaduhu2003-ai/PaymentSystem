from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Package


@login_required
def dashboard(request):

    packages = Package.objects.filter(is_active=True).order_by('price')

    return render(request, 'packages/dashboard.html', {
        'packages': packages
    })