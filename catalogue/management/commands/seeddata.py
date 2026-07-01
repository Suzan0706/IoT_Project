from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from catalogue.models import Domain, Dataset


class Command(BaseCommand):
    help = 'Seed demo data: domains, users, and live datasets'

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

        user, created = User.objects.get_or_create(
            username='demo_researcher',
            defaults={'email': 'demo@aru.ac.ug', 'first_name': 'Demo', 'last_name': 'Researcher'}
        )
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write('Created demo user: demo_researcher / demo1234')

        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@aru.ac.ug', 'first_name': 'System', 'last_name': 'Admin', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('admin1234')
            admin_user.save()
            self.stdout.write('Created admin user: admin / admin1234')

        datasets = [
            {
                'title': 'Dar es Salaam BRT Air Quality Sensor Network',
                'description': 'Continuous PM2.5 and NO2 measurements from 12 fixed sensor nodes along the Dar es Salaam Bus Rapid Transit corridor, capturing traffic-related pollution patterns during peak and off-peak hours.',
                'domain': domains['Transport'],
                'location': 'Dar es Salaam, Tanzania',
                'start_date': '2024-01-15',
                'end_date': '2025-01-15',
                'sampling_interval': '10 s',
                'quality_score': 4.50,
                'download_count': 142,
                'status': 'live',
            },
            {
                'title': 'Kampala Indoor Thermal Comfort IoT Array',
                'description': 'Low-cost DHT22 and SHT30 sensors deployed across 24 informal housing units in Kawempe division, measuring temperature, humidity, and apparent temperature at 5-minute intervals.',
                'domain': domains['Housing'],
                'location': 'Kampala, Uganda',
                'start_date': '2024-03-01',
                'end_date': '2025-03-01',
                'sampling_interval': '5 min',
                'quality_score': 3.80,
                'download_count': 87,
                'status': 'live',
            },
            {
                'title': 'Lake Victoria Shoreline Water Quality Buoys',
                'description': 'Autonomous buoy network monitoring dissolved oxygen, pH, turbidity, and chlorophyll-a on Lake Victoria near Jinja. Data supports fisheries management and pollution tracking.',
                'domain': domains['Water'],
                'location': 'Jinja, Uganda',
                'start_date': '2023-06-01',
                'end_date': '2024-12-01',
                'sampling_interval': '15 min',
                'quality_score': 4.20,
                'download_count': 203,
                'status': 'live',
            },
            {
                'title': 'Stone Town Heritage Site Microclimate Sensors',
                'description': 'Temperature, humidity, and CO2 sensors installed inside and outside three UNESCO heritage buildings in Stone Town, Zanzibar, to monitor corrosion risk for stone carvings.',
                'domain': domains['Heritage'],
                'location': 'Zanzibar City, Tanzania',
                'start_date': '2024-05-10',
                'end_date': '2025-05-10',
                'sampling_interval': '1 min',
                'quality_score': 4.80,
                'download_count': 56,
                'status': 'live',
            },
            {
                'title': 'Arusha Precision Agriculture Soil Moisture Grid',
                'description': 'Capacitive soil moisture sensors with LoRaWAN telemetry across a 5-hectare maize farm in Arusha, tracking irrigation scheduling and drought stress.',
                'domain': domains['Agriculture'],
                'location': 'Arusha, Tanzania',
                'start_date': '2024-02-01',
                'end_date': '2024-11-30',
                'sampling_interval': '30 min',
                'quality_score': 3.50,
                'download_count': 41,
                'status': 'live',
            },
            {
                'title': 'Kigali Urban Air Quality & Noise Monitoring',
                'description': 'Dual air quality and acoustic sensors deployed at 8 traffic intersections in Kigali, capturing PM2.5, PM10, CO, and equivalent continuous sound levels.',
                'domain': domains['Air Quality'],
                'location': 'Kigali, Rwanda',
                'start_date': '2024-04-01',
                'end_date': '2025-04-01',
                'sampling_interval': '1 min',
                'quality_score': 4.10,
                'download_count': 118,
                'status': 'live',
            },
        ]

        for d in datasets:
            obj, created = Dataset.objects.get_or_create(
                title=d['title'],
                defaults={
                    'description': d['description'],
                    'researcher': user,
                    'domain': d['domain'],
                    'location': d['location'],
                    'start_date': d['start_date'],
                    'end_date': d['end_date'],
                    'sampling_interval': d['sampling_interval'],
                    'quality_score': d['quality_score'],
                    'download_count': d['download_count'],
                    'status': d['status'],
                }
            )
            if created:
                self.stdout.write(f'Created dataset: {d["title"]}')

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
