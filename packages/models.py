from django.db import models

class Package(models.Model):

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    duration_months = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return self.name