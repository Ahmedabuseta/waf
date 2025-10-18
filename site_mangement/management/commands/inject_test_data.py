from django.core.management.base import BaseCommand
from django.utils import timezone
from site_mangement.models import Site, RequestAnalytics
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Inject test data for analytics dashboard demonstration'

    def add_arguments(self, parser):
        parser.add_argument('--site-slug', type=str, default='demo-example-com', help='Site slug to add data to')
        parser.add_argument('--count', type=int, default=100, help='Number of test records to create')

    def handle(self, *args, **options):
        site_slug = options['site_slug']
        count = options['count']
        
        try:
            site = Site.objects.get(slug=site_slug)
        except Site.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Site {site_slug} not found'))
            return

        # Test data with various countries and threat levels
        test_data = [
            # High threat countries
            {'country': 'United States', 'country_code': 'US', 'city': 'New York', 'lat': 40.7128, 'lng': -74.0060, 'requests': 150, 'blocked': 25, 'threats': 5},
            {'country': 'China', 'country_code': 'CN', 'city': 'Beijing', 'lat': 39.9042, 'lng': 116.4074, 'requests': 200, 'blocked': 50, 'threats': 10},
            {'country': 'Russia', 'country_code': 'RU', 'city': 'Moscow', 'lat': 55.7558, 'lng': 37.6176, 'requests': 80, 'blocked': 30, 'threats': 8},
            
            # Medium threat countries
            {'country': 'Germany', 'country_code': 'DE', 'city': 'Berlin', 'lat': 52.5200, 'lng': 13.4050, 'requests': 120, 'blocked': 15, 'threats': 3},
            {'country': 'United Kingdom', 'country_code': 'GB', 'city': 'London', 'lat': 51.5074, 'lng': -0.1278, 'requests': 90, 'blocked': 10, 'threats': 2},
            {'country': 'France', 'country_code': 'FR', 'city': 'Paris', 'lat': 48.8566, 'lng': 2.3522, 'requests': 75, 'blocked': 8, 'threats': 1},
            
            # Low threat countries
            {'country': 'Canada', 'country_code': 'CA', 'city': 'Toronto', 'lat': 43.6532, 'lng': -79.3832, 'requests': 60, 'blocked': 2, 'threats': 0},
            {'country': 'Australia', 'country_code': 'AU', 'city': 'Sydney', 'lat': -33.8688, 'lng': 151.2093, 'requests': 45, 'blocked': 1, 'threats': 0},
            {'country': 'Japan', 'country_code': 'JP', 'city': 'Tokyo', 'lat': 35.6762, 'lng': 139.6503, 'requests': 55, 'blocked': 3, 'threats': 1},
            
            # Critical threat countries
            {'country': 'North Korea', 'country_code': 'KP', 'city': 'Pyongyang', 'lat': 39.0392, 'lng': 125.7625, 'requests': 30, 'blocked': 25, 'threats': 15},
            {'country': 'Iran', 'country_code': 'IR', 'city': 'Tehran', 'lat': 35.6892, 'lng': 51.3890, 'requests': 40, 'blocked': 20, 'threats': 12},
        ]

        # Clear existing test data
        RequestAnalytics.objects.filter(site=site, ip_address__startswith='test_').delete()
        self.stdout.write(f'Cleared existing test data for {site.host}')

        # Create test records
        created_count = 0
        for i in range(count):
            # Pick random country data
            country_data = random.choice(test_data)
            
            # Add some randomness to the data
            base_requests = country_data['requests']
            base_blocked = country_data['blocked']
            base_threats = country_data['threats']
            
            # Randomize the numbers slightly
            requests = max(1, base_requests + random.randint(-20, 20))
            blocked = max(0, min(requests, base_blocked + random.randint(-5, 5)))
            threats = max(0, min(blocked, base_threats + random.randint(-2, 2)))
            
            # Determine threat level
            if threats >= 10:
                threat_level = 'critical'
            elif threats >= 5:
                threat_level = 'high'
            elif threats >= 1:
                threat_level = 'medium'
            else:
                threat_level = 'low'
            
            # Determine action taken
            if blocked > 0:
                action_taken = 'blocked'
            else:
                action_taken = 'allowed'
            
            # Create the record
            RequestAnalytics.objects.create(
                site=site,
                ip_address=f'test_{country_data["country_code"].lower()}_{i}',
                country=country_data['country'],
                country_code=country_data['country_code'],
                city=country_data['city'],
                latitude=country_data['lat'] + random.uniform(-0.5, 0.5),
                longitude=country_data['lng'] + random.uniform(-0.5, 0.5),
                request_method=random.choice(['GET', 'POST', 'PUT', 'DELETE']),
                request_path=f'/test/path/{i}',
                user_agent=f'Test Browser {i}',
                threat_level=threat_level,
                action_taken=action_taken,
                response_time=random.uniform(50, 500),
                status_code=random.choice([200, 200, 200, 200, 404, 403, 500]),  # Mostly 200s, some errors
                timestamp=timezone.now() - timedelta(days=random.randint(0, 7))
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} test records for {site.host}\n'
                f'Countries with data: {", ".join(set([d["country"] for d in test_data]))}\n'
                f'Visit /analytics/{site_slug}/ to see the country highlighting!'
            )
        )
