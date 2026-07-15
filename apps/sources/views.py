from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from sources.models import LiveSource, Recording, StreamingSetting
from sources.forms import LiveSourceForm

class SourceQuerysetMixin(LoginRequiredMixin):
    """
    Mixin restricting live sources queries to the logged-in user's region (unless Super Admin).
    """
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return LiveSource.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return LiveSource.objects.filter(region=user.region)
        return LiveSource.objects.none()


class LiveSourceListView(SourceQuerysetMixin, ListView):
    model = LiveSource
    template_name = 'sources/source_list.html'
    context_object_name = 'sources'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        request_host = self.request.get_host().split(':')[0]
        request_scheme = 'https' if self.request.is_secure() else 'http'
        is_prod = not getattr(settings, 'DEBUG', False)
        
        def get_dynamic_url(url_str):
            if not url_str:
                return url_str
            # Check if accessed via domain or over secure HTTPS connection
            is_domain = not request_host.replace('.', '').isdigit() and request_host != 'localhost'
            use_proxy_path = self.request.is_secure() or is_prod or is_domain
            
            if use_proxy_path:
                prefix = ''
                if ':8889' in url_str:
                    prefix = '/webrtc'
                elif ':8888' in url_str:
                    prefix = '/hls'
                else:
                    return url_str
                return f"{request_scheme}://{self.request.get_host()}{prefix}"
            else:
                if '127.0.0.1' in url_str or 'localhost' in url_str:
                    return url_str.replace('127.0.0.1', request_host).replace('localhost', request_host)
                return url_str

        db_settings = StreamingSetting.objects.first()
        if db_settings:
            context['mediamtx_webrtc_url'] = get_dynamic_url(db_settings.mediamtx_webrtc_url)
            context['mediamtx_hls_url'] = get_dynamic_url(db_settings.mediamtx_hls_url)
            context['stun_url'] = db_settings.stun_url
            context['turn_url'] = db_settings.turn_url
        else:
            context['mediamtx_webrtc_url'] = get_dynamic_url(getattr(settings, 'MEDIAMTX_WEBRTC_URL', 'http://127.0.0.1:8889'))
            context['mediamtx_hls_url'] = get_dynamic_url(getattr(settings, 'MEDIAMTX_HLS_URL', 'http://127.0.0.1:8888'))
            context['stun_url'] = 'stun:stun.l.google.com:19302'
            context['turn_url'] = 'turn:live.akhu.uz:3478?transport=udp'
            
        return context


class LiveSourceCreateWizardView(SourceQuerysetMixin, CreateView):
    model = LiveSource
    form_class = LiveSourceForm
    template_name = 'sources/source_wizard.html'
    success_url = reverse_lazy('sources:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        source = form.save(commit=False)
        if self.request.user.is_region_admin():
            source.region = self.request.user.region
        
        # Save initially to generate UUID
        source.save()
        
        # Construct and assign the MediaMTX player URL path
        stream_name = f"source_{source.id}"
        
        db_settings = StreamingSetting.objects.first()
        if db_settings:
            webrtc_base = db_settings.mediamtx_webrtc_url
        else:
            webrtc_base = getattr(settings, 'MEDIAMTX_WEBRTC_URL', 'http://127.0.0.1:8889')
            
        source.streaming_url = f"{webrtc_base}/{stream_name}/"
        source.save()

        messages.success(self.request, _(f"Source '{source.name}' successfully registered."))
        return redirect(self.success_url)


class LiveSourceUpdateView(SourceQuerysetMixin, UpdateView):
    model = LiveSource
    form_class = LiveSourceForm
    template_name = 'sources/source_form.html'
    success_url = reverse_lazy('sources:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        source = form.save()
        messages.success(self.request, _(f"Source '{source.name}' updated successfully."))
        return redirect(self.success_url)


class LiveSourceDeleteView(SourceQuerysetMixin, DeleteView):
    model = LiveSource
    template_name = 'sources/source_confirm_delete.html'
    success_url = reverse_lazy('sources:list')

    def post(self, request, *args, **kwargs):
        source = self.get_object()
        source.delete()
        messages.success(request, _(f"Source '{source.name}' deleted successfully."))
        return redirect(self.success_url)
