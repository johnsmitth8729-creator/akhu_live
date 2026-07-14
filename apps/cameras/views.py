from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from cameras.models import Camera, CameraStatus
from cameras.forms import CameraForm
from cameras.services import update_camera_status
from streaming.services import MediaMTXService
from streaming.models import StreamingLog

class CameraQuerysetMixin(LoginRequiredMixin):
    """
    Mixin that restricts the camera list to the user's region unless they are a Super Admin.
    """
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return Camera.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return Camera.objects.filter(region=user.region)
        return Camera.objects.none()


class CameraListView(CameraQuerysetMixin, ListView):
    model = Camera
    template_name = 'cameras/camera_list.html'
    context_object_name = 'cameras'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        region_filter = self.request.GET.get('region', '')
        status_filter = self.request.GET.get('status', '')

        if search_query:
            queryset = queryset.filter(name__icontains=search_query) | \
                       queryset.filter(building__icontains=search_query) | \
                       queryset.filter(room__icontains=search_query)
        if region_filter and self.request.user.is_super_admin():
            queryset = queryset.filter(region_id=region_filter)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        
        if self.request.user.is_super_admin():
            from regions.models import Region
            context['regions'] = Region.objects.all()
            context['region_filter'] = self.request.GET.get('region', '')
            
        return context


class CameraCreateView(CameraQuerysetMixin, CreateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cameras/camera_form.html'
    success_url = reverse_lazy('cameras:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        camera = form.save(commit=False)
        
        # If user is a Region Admin, force association to their region
        if self.request.user.is_region_admin():
            camera.region = self.request.user.region
            
        camera.save()
        
        # Automatically register camera with MediaMTX
        MediaMTXService.add_camera_path(camera)
        
        messages.success(self.request, _(f"Camera '{camera.name}' added successfully."))
        return redirect(self.success_url)


class CameraUpdateView(CameraQuerysetMixin, UpdateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cameras/camera_form.html'
    success_url = reverse_lazy('cameras:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        camera = form.save()
        
        # Update connection configuration in MediaMTX
        MediaMTXService.add_camera_path(camera)
        
        messages.success(self.request, _(f"Camera '{camera.name}' updated successfully."))
        return redirect(self.success_url)


class CameraDeleteView(CameraQuerysetMixin, DeleteView):
    model = Camera
    template_name = 'cameras/camera_confirm_delete.html'
    success_url = reverse_lazy('cameras:list')

    def post(self, request, *args, **kwargs):
        camera = self.get_object()
        
        # De-register path from MediaMTX
        MediaMTXService.remove_camera_path(camera)
        
        camera.delete()
        messages.success(request, _(f"Camera '{camera.name}' deleted successfully."))
        return redirect(self.success_url)


class CameraStartStreamView(CameraQuerysetMixin, View):
    def post(self, request, pk):
        camera = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Call service to register/refresh path in MediaMTX
        success = MediaMTXService.add_camera_path(camera)
        if success:
            StreamingLog.objects.create(
                camera=camera,
                action=StreamingLog.Actions.STARTED
            )
            messages.success(request, _(f"Stream for camera '{camera.name}' started successfully."))
        else:
            messages.error(request, _(f"Failed to start stream for camera '{camera.name}' in MediaMTX. Verify MediaMTX is running."))
            
        return redirect('cameras:list')


class CameraStopStreamView(CameraQuerysetMixin, View):
    def post(self, request, pk):
        camera = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Call service to remove path in MediaMTX
        success = MediaMTXService.remove_camera_path(camera)
        if success:
            # Calculate duration of the last active stream if possible
            last_start = StreamingLog.objects.filter(
                camera=camera, 
                action=StreamingLog.Actions.STARTED
            ).order_by('-timestamp').first()
            
            duration = None
            if last_start:
                duration = timezone.now() - last_start.timestamp

            StreamingLog.objects.create(
                camera=camera,
                action=StreamingLog.Actions.STOPPED,
                duration=duration
            )
            messages.success(request, _(f"Stream for camera '{camera.name}' stopped successfully."))
        else:
            messages.error(request, _(f"Failed to stop stream for camera '{camera.name}' in MediaMTX."))
            
        return redirect('cameras:list')


class CameraCheckStatusView(View):
    """
    Triggers an instant health check on the camera and returns the result as JSON.
    Accessible to everyone (including anonymous viewers) for public dashboard status checks.
    """
    def get(self, request, pk):
        return self._check_status(pk)

    def post(self, request, pk):
        return self._check_status(pk)

    def _check_status(self, pk):
        camera = get_object_or_404(Camera.objects.filter(region__is_active=True), pk=pk)
        is_online = update_camera_status(camera)
        
        return JsonResponse({
            'status': camera.status,
            'is_online': is_online,
            'last_seen': camera.last_seen.strftime('%Y-%m-%d %H:%M:%S') if camera.last_seen else None
        })

