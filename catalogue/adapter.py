from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated and not sociallogin.is_existing:
            if request.user.email == sociallogin.account.extra_data.get('email'):
                sociallogin.connect(request, request.user)

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
        user.save()
        Profile.objects.get_or_create(user=user)
        return user

    def get_connect_redirect_url(self, request):
        return '/'
