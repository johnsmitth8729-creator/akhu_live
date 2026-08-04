from settings.models import SystemSetting

def settings_and_theme(request):
    """
    Context processor that injects system setting defaults and theme cookie
    state into all templates automatically.
    """
    system_name = "AKHU Live Exam Monitor"
    try:
        setting = SystemSetting.objects.get(key='system_name')
        system_name = setting.value
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error loading system_name setting: {e}")
        
    # Get dark/light mode preference from cookie, defaulting to light
    theme = request.COOKIES.get('theme', 'light')
    
    # Get active language
    from django.utils.translation import get_language
    lang = get_language()
    
    # Get regions list for sidebar navigation (cached for 5 minutes to reduce DB load)
    global_regions = []
    try:
        from django.core.cache import cache
        from regions.models import Region
        from django.db.models import Count
        global_regions = cache.get('global_regions_sidebar_v4')
        if global_regions is None:
            regions_qs = Region.objects.filter(is_active=True).annotate(
                cams_cnt=Count('cameras', distinct=True),
                sources_cnt=Count('live_sources', distinct=True)
            ).order_by('name')
            global_regions = []
            for r in regions_qs:
                r.total_stream_count = (r.cams_cnt or 0) + (r.sources_cnt or 0)
                global_regions.append(r)
            cache.set('global_regions_sidebar_v4', global_regions, timeout=300)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error loading global_regions list: {e}")
    
    return {
        'SYSTEM_NAME': system_name,
        'THEME': theme,
        'CURRENT_LANGUAGE': lang,
        'GLOBAL_REGIONS': global_regions,
    }
