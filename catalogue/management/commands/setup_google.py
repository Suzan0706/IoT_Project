from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Force provisions the default Site and Google SocialApp to clear the DoesNotExist crash screen'

    def handle(self, *args, **options):
        try:
            from django.contrib.sites.models import Site
            from allauth.socialaccount.models import SocialApp

            # 1. Setup site with proper local development domain
            site, created = Site.objects.get_or_create(
                id=1,
                defaults={'domain': '127.0.0.1:8000', 'name': 'ARU IoT'}
            )
            if not created and site.domain != '127.0.0.1:8000':
                site.domain = '127.0.0.1:8000'
                site.name = 'ARU IoT'
                site.save()

            # 2. Provision the SocialApp database row
            app, app_created = SocialApp.objects.get_or_create(
                provider='google',
                defaults={
                    'name': 'Google Auth',
                    'client_id': 'placeholder-apps.googleusercontent.com',
                    'secret': 'placeholder-secret-key-string',
                }
            )

            # 3. Associate site to application profile
            if not app.sites.filter(id=site.id).exists():
                app.sites.add(site)

            self.stdout.write(self.style.SUCCESS("Successfully created and mapped Google SocialApp in DB!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Command execution failed: {e}"))
