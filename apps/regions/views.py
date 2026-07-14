from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from core.permissions import SuperAdminRequiredMixin
from regions.models import Region
from regions.forms import RegionCreationForm, RegionUpdateForm

User = get_user_model()

class RegionListView(SuperAdminRequiredMixin, ListView):
    model = Region
    template_name = 'regions/region_list.html'
    context_object_name = 'regions'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')
        
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        if status_filter:
            is_active = status_filter == 'active'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class RegionCreateView(SuperAdminRequiredMixin, CreateView):
    model = Region
    form_class = RegionCreationForm
    template_name = 'regions/region_form.html'
    success_url = reverse_lazy('regions:list')

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        try:
            with transaction.atomic():
                # 1. Create user account
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    role=User.Roles.REGION_ADMIN,
                    is_active=True
                )
                # 2. Create region
                region = form.save(commit=False)
                region.user = user
                region.save()
                
            messages.success(self.request, _(f"Region '{region.name}' and user '{username}' created successfully."))
            return redirect(self.success_url)
        except Exception as e:
            form.add_error(None, f"Error creating region: {e}")
            return self.form_invalid(form)


class RegionUpdateView(SuperAdminRequiredMixin, UpdateView):
    model = Region
    form_class = RegionUpdateForm
    template_name = 'regions/region_form.html'
    success_url = reverse_lazy('regions:list')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                region = form.save()
                # Keep active state synchronized with Django user
                user = region.user
                user.is_active = region.is_active
                user.save(update_fields=['is_active'])
                
            messages.success(self.request, _(f"Region '{region.name}' updated successfully."))
            return redirect(self.success_url)
        except Exception as e:
            form.add_error(None, f"Error updating region: {e}")
            return self.form_invalid(form)


class RegionDeleteView(SuperAdminRequiredMixin, DeleteView):
    model = Region
    template_name = 'regions/region_confirm_delete.html'
    success_url = reverse_lazy('regions:list')

    def post(self, request, *args, **kwargs):
        region = self.get_object()
        user = region.user
        try:
            with transaction.atomic():
                # Deleting the region user will also delete the region due to OneToOne relationship
                # with CASCADE. But we delete the user explicitly to clean up both.
                user.delete()
            messages.success(request, _(f"Region '{region.name}' and its account deleted successfully."))
        except Exception as e:
            messages.error(request, _(f"Error deleting region: {e}"))
        return redirect(self.success_url)


class RegionToggleStatusView(SuperAdminRequiredMixin, View):
    def post(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        region.is_active = not region.is_active
        
        try:
            with transaction.atomic():
                region.save(update_fields=['is_active'])
                user = region.user
                user.is_active = region.is_active
                user.save(update_fields=['is_active'])
                
            status_text = _("activated") if region.is_active else _("deactivated")
            messages.success(request, _(f"Region '{region.name}' has been {status_text}."))
        except Exception as e:
            messages.error(request, _(f"Error toggling region status: {e}"))
            
        return redirect('regions:list')


class RegionPasswordResetView(SuperAdminRequiredMixin, View):
    def post(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        new_password = request.POST.get('password')
        
        if not new_password or len(new_password) < 4:
            messages.error(request, _("Password must be at least 4 characters long."))
            return redirect('regions:list')
            
        try:
            user = region.user
            user.set_password(new_password)
            user.save()
            messages.success(request, _(f"Password reset successfully for region '{region.name}'."))
        except Exception as e:
            messages.error(request, _(f"Error resetting password: {e}"))
            
        return redirect('regions:list')
