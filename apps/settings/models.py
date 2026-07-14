from django.db import models
from django.utils.translation import gettext_lazy as _

class SystemSetting(models.Model):
    class ValueTypes(models.TextChoices):
        STRING = 'string', _('String')
        INTEGER = 'integer', _('Integer')
        BOOLEAN = 'boolean', _('Boolean')

    key = models.CharField(max_length=100, unique=True, verbose_name=_('Setting Key'))
    value = models.TextField(verbose_name=_('Setting Value'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    value_type = models.CharField(
        max_length=20,
        choices=ValueTypes.choices,
        default=ValueTypes.STRING,
        verbose_name=_('Value Type')
    )

    class Meta:
        verbose_name = _('System Setting')
        verbose_name_plural = _('System Settings')
        ordering = ['key']

    def __str__(self):
        return self.key

    def get_typed_value(self):
        if self.value_type == self.ValueTypes.INTEGER:
            try:
                return int(self.value)
            except ValueError:
                return 0
        elif self.value_type == self.ValueTypes.BOOLEAN:
            return self.value.lower() in ('true', '1', 'yes', 'on')
        return self.value
