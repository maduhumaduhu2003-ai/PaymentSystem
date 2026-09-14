from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.http import HttpResponse

from .sitemaps import StaticViewSitemap


def robots_txt(request):
    content = """User-agent: *
Allow: /

Sitemap: https://satpay.onrender.com/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")

sitemaps = {
    "static": StaticViewSitemap,
}


urlpatterns = [
    path("admin/", admin.site.urls),

    # Public / account pages
    path("", include("accounts.urls")),

    # Application sections
    path("packages/", include("packages.urls")),
    path("payments/", include("payments.urls")),
    path("business/", include("business.urls")),
    path("subscriptions/", include("subscriptions.urls")),

    # Google Sitemap
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django-sitemap",
    ),
    path("robots.txt", robots_txt, name="robots-txt"),
]