from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Region(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='region',
        verbose_name=_('User Account')
    )
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Region Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    logo = models.ImageField(upload_to='regions/logos/', null=True, blank=True, verbose_name=_('Logo'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Date'))

    class Meta:
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        ordering = ['name']

    def __str__(self):
        return self.name
