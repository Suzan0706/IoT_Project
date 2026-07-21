from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from catalogue.models import Profile, Domain, Dataset


class Command(BaseCommand):
    help = 'Create demo researcher accounts with different approval statuses'

    def handle(self, *args, **kwargs):
        domains_data = [
            ('Transport', 'transport'),
            ('Air Quality', 'air-quality'),
            ('Water', 'water'),
            ('Heritage', 'heritage'),
            ('Housing', 'housing'),
            ('Agriculture', 'agriculture'),
        ]

        domains = {}
        for name, slug in domains_data:
            d, created = Domain.objects.get_or_create(name=name, slug=slug)
            domains[name] = d
            if created:
                self.stdout.write(f'Created domain: {name}')

        demo_researchers = [
            {
                'username': 'pending_researcher',
                'email': 'pending@aru.ac.ug',
                'first_name': 'Alice',
                'last_name': 'Mrema',
                'institution': 'Ardhi University',
                'department': 'Environmental Science',
                'phone_number': '+255 7xx 000 001',
                'research_interests': 'Air quality monitoring, IoT sensor networks, urban pollution',
                'approval_status': 'pending',
                'dataset_title': 'Dar es Salaam BRT Air Quality Sensor Network',
            },
            {
                'username': 'approved_researcher',
                'email': 'approved@aru.ac.ug',
                'first_name': 'James',
                'last_name': 'Kimaro',
                'institution': 'University of Dar es Salaam',
                'department': 'Civil Engineering',
                'phone_number': '+255 7xx 000 002',
                'research_interests': 'Structural health monitoring, vibration analysis, bridge safety',
                'approval_status': 'approved',
                'dataset_title': 'Kampala Indoor Thermal Comfort IoT Array',
            },
            {
                'username': 'rejected_researcher',
                'email': 'rejected@aru.ac.ug',
                'first_name': 'Grace',
                'last_name': 'Mwakyusa',
                'institution': 'Muhimbili University',
                'department': 'Public Health',
                'phone_number': '+255 7xx 000 003',
                'research_interests': 'Water quality assessment, disease surveillance, environmental health',
                'approval_status': 'rejected',
                'rejection_reason': 'Incomplete profile information. Please provide valid institutional affiliation and research proposal.',
                'dataset_title': 'Lake Victoria Shoreline Water Quality Buoys',
            },
        ]

        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@aru.ac.ug', 'first_name': 'System', 'last_name': 'Admin', 'is_staff': True, 'is_superuser': True}
        )
        if not admin_user.has_usable_password():
            admin_user.set_password('admin1234')
            admin_user.save()
            self.stdout.write('Created/updated admin user: admin / admin1234')

        for data in demo_researchers:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()
                self.stdout.write(f'Created demo user: {user.username} / demo1234')

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.institution = data['institution']
            profile.department = data['department']
            profile.phone_number = data['phone_number']
            profile.research_interests = data['research_interests']
            profile.approval_status = data['approval_status']
            if 'rejection_reason' in data:
                profile.rejection_reason = data['rejection_reason']
            profile.reviewed_by = admin_user
            profile.reviewed_at = timezone.now()
            profile.save()
            self.stdout.write(f'Updated profile for {user.username}: {data["approval_status"]}')

            if data.get('dataset_title'):
                dataset, ds_created = Dataset.objects.get_or_create(
                    title=data['dataset_title'],
                    defaults={
                        'description': f'Sample dataset submitted by {data["first_name"]} {data["last_name"]} for demonstration purposes.',
                        'researcher': user,
                        'domain': list(domains.values())[0],
                        'sensor_type': 'Temperature',
                        'output_format': 'CSV',
                        'location': 'Dar es Salaam, Tanzania',
                        'update_frequency': '5 min',
                        'units_of_measurement': '°C, %RH',
                        'department': data['department'],
                        'license': 'CC BY 4.0',
                        'quality_score': 4.00,
                        'download_count': 0,
                        'status': 'pending',
                    }
                )
                if ds_created:
                    self.stdout.write(f'  Created sample dataset: {data["dataset_title"]}')

        self.stdout.write(self.style.SUCCESS('Demo researcher accounts created successfully.'))