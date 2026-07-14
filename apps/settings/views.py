from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext_lazy as _
from core.permissions import SuperAdminRequiredMixin
from settings.models import SystemSetting

class SystemSettingListView(SuperAdminRequiredMixin, ListView):
    model = SystemSetting
    template_name = 'settings/setting_list.html'
    context_object_name = 'settings'


class SystemSettingUpdateView(SuperAdminRequiredMixin, View):
    def post(self, request):
        # Update settings by iterating over POST keys
        updated_count = 0
        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken':
                continue
            try:
                setting = SystemSetting.objects.get(key=key)
                # Parse or clean boolean values
                if setting.value_type == SystemSetting.ValueTypes.BOOLEAN:
                    clean_val = 'true' if value in ('on', 'true', '1') else 'false'
                else:
                    clean_val = value.strip()

                if setting.value != clean_val:
                    setting.value = clean_val
                    setting.save(update_fields=['value'])
                    updated_count += 1
            except SystemSetting.DoesNotExist:
                import logging
                logging.getLogger(__name__).warning(f"Attempted to update non-existent SystemSetting key: '{key}'")
                
        # Handle checkboxes that are unchecked (and thus missing from POST)
        boolean_settings = SystemSetting.objects.filter(value_type=SystemSetting.ValueTypes.BOOLEAN)
        for setting in boolean_settings:
            if setting.key not in request.POST:
                if setting.value != 'false':
                    setting.value = 'false'
                    setting.save(update_fields=['value'])
                    updated_count += 1
                    
        messages.success(request, _(f"Updated {updated_count} system settings successfully."))
        return redirect('settings:list')
