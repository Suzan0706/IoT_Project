from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib.sites.models import Site
from django.contrib import messages
from .models import Profile

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def get_callback_url(self, request, app):
        protocol = getattr(settings, 'ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'http')
        domain = Site.objects.get_current().domain
        return f"{protocol}://{domain}/accounts/google/login/callback/"

    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated and not sociallogin.is_existing:
            if request.user.email == sociallogin.account.extra_data.get('email'):
                sociallogin.connect(request, request.user)
                return redirect('home')

        if sociallogin.is_existing:
            user = sociallogin.user
            try:
                profile = user.profile
                if profile.approval_status == 'pending':
                    messages.error(request, 'Your account is pending administrator approval.')
                    return redirect('login')
                elif profile.approval_status == 'rejected':
                    messages.error(request, 'Your registration request was not approved. Please contact the system administrator.')
                    return redirect('login')
            except Profile.DoesNotExist:
                pass
            return

        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            sociallogin.connect(request, existing_user)

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        extra_data = sociallogin.account.extra_data or {}
        user.set_unusable_password()
        if not user.first_name:
            user.first_name = extra_data.get('given_name', '') or extra_data.get('name', '').split(' ')[0] if extra_data.get('name') else ''
        if not user.last_name:
            user.last_name = extra_data.get('family_name', '') or ' '.join(extra_data.get('name', '').split(' ')[1:]) if extra_data.get('name') else ''
        if not user.email:
            user.email = extra_data.get('email', '')
        if not user.username:
            base_username = user.email.split('@')[0] if user.email else 'user'
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user.username = username
        user.is_staff = False
        user.is_superuser = False
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.approval_status = 'pending'
        profile.save()
        return user

    def get_connect_redirect_url(self, request):
        return '/'

    def get_signup_redirect_url(self, request, sociallogin):
        return '/role-redirect/'

    def get_login_redirect_url(self, request, sociallogin):
        return '/role-redirect/'
