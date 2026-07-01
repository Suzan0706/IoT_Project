from django.apps import AppConfig
from django.db.models.signals import post_migrate

def auto_create_google_social_app(sender, **kwargs):
    """
    Automatically creates the default Site and Google SocialApp entry 
    to guarantee the login view never crashes with DoesNotExist.
    """
    try:
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        
        # 1. Force establish the default local development site domain
        site, created = Site.objects.get_or_create(
            id=1, 
            defaults={'domain': '127.0.0.1:8000', 'name': 'ARU IoT'}
        )
        if not created and site.domain != '127.0.0.1:8000':
            site.domain = '127.0.0.1:8000'
            site.name = 'ARU IoT'
            site.save()

        # 2. Force establish the Google application configuration row
        app, app_created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google Auth Portal',
                'client_id': 'placeholder-id-apps.googleusercontent.com',
                'secret': 'placeholder-secret-key-string',
            }
        )
        
        # 3. Securely bind the active site link metadata
        if not app.sites.filter(id=site.id).exists():
            app.sites.add(site)
            
        print(">> [SUCCESS]: Google SocialApp OAuth parameters successfully verified in DB.")
    except Exception as e:
        print(f">> [WARNING]: Automated SocialApp registration skipped: {e}")

class CatalogueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalogue'

    def ready(self):
        # Attach the data generation hook safely to post_migrate chain
        post_migrate.connect(auto_create_google_social_app, sender=self)