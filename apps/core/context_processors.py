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
    except Exception:
        pass
        
    # Get dark/light mode preference from cookie, defaulting to light
    theme = request.COOKIES.get('theme', 'light')
    
    # Get active language
    from django.utils.translation import get_language
    lang = get_language()
    
    # Get regions list for sidebar navigation
    global_regions = []
    try:
        from regions.models import Region
        global_regions = list(Region.objects.all().order_by('name'))
    except Exception:
        pass
    
    return {
        'SYSTEM_NAME': system_name,
        'THEME': theme,
        'CURRENT_LANGUAGE': lang,
        'GLOBAL_REGIONS': global_regions,
    }
