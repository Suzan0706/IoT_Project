from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation, timezone as django_timezone


class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Vary'] = 'Cookie, Authorization'
        return response


class AdminAccessMiddleware:
    ADMIN_PATH_PREFIXES = (
        '/dashboard/',
        '/analytics/',
        '/profile/',
        '/governance/',
        '/feedback-management/',
        '/portal-admin/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = getattr(request, 'user', None)

        is_admin_path = any(path.startswith(prefix) for prefix in self.ADMIN_PATH_PREFIXES)
        is_admin_user = bool(
            user and user.is_authenticated and (user.is_staff or user.is_superuser)
        )

        if is_admin_path and not is_admin_user:
            if not user or not user.is_authenticated:
                return redirect('custom_admin_login')
            return redirect('user_dashboard')

        return self.get_response(request)


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            try:
                profile = user.profile
                if profile and profile.preferred_language:
                    current_session_lang = request.session.get('django_language')
                    if current_session_lang != profile.preferred_language:
                        request.session['django_language'] = profile.preferred_language
                    if translation.get_language() != profile.preferred_language:
                        translation.activate(profile.preferred_language)
            except Exception:
                pass

        response = self.get_response(request)
        return response


class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            try:
                profile = user.profile
                if profile and profile.time_zone:
                    django_timezone.activate(profile.time_zone)
                else:
                    django_timezone.deactivate()
            except Exception:
                django_timezone.deactivate()
        else:
            django_timezone.deactivate()

        response = self.get_response(request)
        return response
