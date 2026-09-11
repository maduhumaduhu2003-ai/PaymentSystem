from django.db import models


class DecoderType(models.Model):
    """Decoder types - CANAL BI, AZAM BI, etc."""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="e.g., CANAL, AZAM")
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Bootstrap icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Package(models.Model):
    """Packages for each decoder type"""
    
    decoder_type = models.ForeignKey(
        DecoderType,
        on_delete=models.CASCADE,
        related_name='packages',
        null=True,  # Temporary nullable for migration
        blank=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    duration_months = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.decoder_type.name if self.decoder_type else 'N/A'} - {self.name}"