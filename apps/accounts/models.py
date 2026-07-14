from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Roles(models.TextChoices):
        SUPER_ADMIN = 'super_admin', _('Super Admin')
        REGION_ADMIN = 'region_admin', _('Region Administrator')

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.SUPER_ADMIN,
        verbose_name=_('Role')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def is_super_admin(self):
        return self.role == self.Roles.SUPER_ADMIN or self.is_superuser

    def is_region_admin(self):
        return self.role == self.Roles.REGION_ADMIN
