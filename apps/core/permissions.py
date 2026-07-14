from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class SuperAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Enforces that the current logged-in user is a Super Admin.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_super_admin()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class RegionAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Enforces that the current logged-in user is a Region Administrator.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_region_admin()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()
