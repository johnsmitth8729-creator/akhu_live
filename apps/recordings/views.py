import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from recordings.models import RecordingSession, LiveSession, StoragePolicy
from regions.models import Region

class RecordingQuerysetMixin(LoginRequiredMixin):
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return RecordingSession.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return RecordingSession.objects.filter(region=user.region)
        return RecordingSession.objects.none()


class RecordingListView(RecordingQuerysetMixin, ListView):
    model = RecordingSession
    template_name = 'recordings/recording_list.html'
    context_object_name = 'recordings'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        region_id = self.request.GET.get('region', '')
        status_filter = self.request.GET.get('status', '')

        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(filename__icontains=search)
        if region_id and self.request.user.is_super_admin():
            queryset = queryset.filter(region_id=region_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-started_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        
        # Calculate total storage usage
        total_bytes = RecordingSession.objects.aggregate(total=Sum('filesize_bytes'))['total'] or 0
        context['total_storage_gb'] = round(total_bytes / (1024 * 1024 * 1024), 2)
        
        policy = StoragePolicy.objects.first()
        context['max_storage_gb'] = policy.max_storage_gb if policy else 500
        context['storage_percent'] = min(100, int((context['total_storage_gb'] / context['max_storage_gb']) * 100)) if context['max_storage_gb'] else 0

        if self.request.user.is_super_admin():
            context['regions'] = Region.objects.all()
            context['region_filter'] = self.request.GET.get('region', '')

        return context


class RecordingDetailView(RecordingQuerysetMixin, DetailView):
    model = RecordingSession
    template_name = 'recordings/recording_detail.html'
    context_object_name = 'recording'


class RecordingUpdateView(RecordingQuerysetMixin, UpdateView):
    model = RecordingSession
    template_name = 'recordings/recording_form.html'
    fields = ['title', 'description', 'retention_policy']
    success_url = reverse_lazy('recordings:list')

    def form_valid(self, form):
        messages.success(self.request, _("Recording updated successfully."))
        return super().form_valid(form)


class RecordingDeleteView(RecordingQuerysetMixin, DeleteView):
    model = RecordingSession
    template_name = 'recordings/recording_confirm_delete.html'
    success_url = reverse_lazy('recordings:list')

    def delete(self, request, *args, **kwargs):
        recording = self.get_object()
        messages.success(request, _(f"Recording '{recording.title}' deleted successfully."))
        return super().delete(request, *args, **kwargs)


from django.http import FileResponse, HttpResponseForbidden, Http404
from django.views import View
from django.conf import settings

class RecordingDownloadView(LoginRequiredMixin, View):
    """
    Secure download view. Returns HTTP 403 Forbidden for regular users attempting direct downloads.
    """
    def get(self, request, pk):
        user = request.user
        if not (user.is_super_admin() or user.is_region_admin()):
            return HttpResponseForbidden(_("Access Denied: Permission Required to Download Recordings."))
        
        recording = get_object_or_404(RecordingSession, pk=pk)
        full_path = os.path.join(settings.MEDIA_ROOT, recording.file_path)
        if not os.path.exists(full_path):
            raise Http404(_("Recording file not found on server."))
            
        return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=recording.filename)
