from django.utils import timezone as django_timezone


def user_timezone_auto_detected(request):
    auto_detected = False
    if request.user.is_authenticated:
        try:
            auto_detected = getattr(request.user.profile, 'time_zone_auto_detected', False)
        except Exception:
            auto_detected = False
    return {
        'user_timezone_auto_detected': auto_detected,
    }


def user_theme_preference(request):
    theme = 'system'
    admin_theme = 'system'
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            theme = getattr(profile, 'theme_preference', 'system') or 'system'
            admin_theme = getattr(profile, 'admin_theme_preference', 'system') or 'system'
        except Exception:
            theme = 'system'
            admin_theme = 'system'
    
    path = getattr(request, 'path', '')
    is_admin_path = any(path.startswith(prefix) for prefix in [
        '/dashboard/',
        '/analytics/',
        '/profile/',
        '/governance/',
        '/feedback-management/',
        '/portal-admin/',
    ])
    
    current_theme = admin_theme if is_admin_path else theme
    
    return {
        'user_theme_preference': theme,
        'user_admin_theme_preference': admin_theme,
        'current_theme': current_theme,
    }


def general_settings(request):
    from catalogue.models import SystemSetting
    settings_qs = SystemSetting.objects.filter(category='general')
    settings_map = {s.key: s.value for s in settings_qs}
    return {
        'general_settings': settings_map,
    }
