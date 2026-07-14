from django.views.generic import ListView
from core.permissions import SuperAdminRequiredMixin
from logs.models import ActivityLog

class ActivityLogListView(SuperAdminRequiredMixin, ListView):
    model = ActivityLog
    template_name = 'logs/activity_log_list.html'
    context_object_name = 'logs'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        search_query = self.request.GET.get('search', '')
        action_filter = self.request.GET.get('action', '')
        
        if search_query:
            queryset = queryset.filter(description__icontains=search_query) | \
                       queryset.filter(user__username__icontains=search_query)
        if action_filter:
            queryset = queryset.filter(action=action_filter)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['action_filter'] = self.request.GET.get('action', '')
        
        # Pull distinct actions for filter dropdown
        context['actions'] = ActivityLog.objects.values_list('action', flat=True).distinct()
        return context
