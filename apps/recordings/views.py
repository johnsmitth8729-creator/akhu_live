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

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        try:
            obj.sync_disk_info()
        except Exception:
            pass
        return obj


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
    Secure download and streaming view for recorded video files.
    """
    def get(self, request, pk):
        recording = get_object_or_404(RecordingSession, pk=pk)
        try:
            recording.sync_disk_info()
        except Exception:
            pass

        target_file = None
        stream_id = ""
        if recording.live_session and recording.live_session.stream_id:
            stream_id = recording.live_session.stream_id
        elif recording.source:
            stream_id = f"source_{recording.source.id}"
        elif recording.camera:
            stream_id = f"camera_{recording.camera.id}"

        search_dirs = [
            f"/opt/mediamtx/recordings/{stream_id}",
            os.path.join(settings.MEDIA_ROOT, 'recordings', stream_id),
            settings.MEDIA_ROOT
        ]

        if recording.file_path and os.path.exists(os.path.join(settings.MEDIA_ROOT, recording.file_path)):
            target_file = os.path.join(settings.MEDIA_ROOT, recording.file_path)
        else:
            for s_dir in search_dirs:
                if os.path.exists(s_dir):
                    mp4_files = []
                    for root, _, files in os.walk(s_dir):
                        for f in files:
                            if f.endswith('.mp4'):
                                mp4_files.append(os.path.join(root, f))
                    if mp4_files:
                        mp4_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
                        target_file = mp4_files[0]
                        break

        if not target_file or not os.path.exists(target_file):
            raise Http404(_("Recording file not found on server."))

        as_attachment = request.GET.get('download', 'false').lower() == 'true'
        download_name = recording.filename if recording.filename.endswith('.mp4') else f"{recording.filename}.mp4"
        return FileResponse(open(target_file, 'rb'), as_attachment=as_attachment, filename=download_name)
