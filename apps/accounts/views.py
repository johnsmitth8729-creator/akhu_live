from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.utils.translation import gettext_lazy as _

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        if user.is_super_admin():
            return reverse('dashboard:admin_dashboard')
        elif user.is_region_admin():
            return reverse('dashboard:region_dashboard')
        return reverse('dashboard:home')


class CustomLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('accounts:login')

    def post(self, request):
        logout(request)
        return redirect('accounts:login')
