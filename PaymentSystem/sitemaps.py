from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """
    Sitemap for public pages that should be discoverable by Google.
    """

    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "welcome",
            "login",
            "register",
        ]

    def location(self, item):
        return reverse(item)