"""
Management command to generate demo analytics data for testing
Usage: python manage.py generate_demo_analytics
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from site_management.models import Site, RequestAnalytics, ThreatAlert


class Command(BaseCommand):
    help = 'Generate demo analytics data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of analytics records to generate'
        )

    def handle(self, *args, **options):
        count = options['count']

        # Ensure we have at least one site
        site, created = Site.objects.get_or_create(
            host='demo.example.com',
            defaults={
                'protocol': 'https',
                'status': 'active',
                'slug': 'demo-example-com'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created demo site: {site.host}"))

        # Sample data for realistic generation
        countries = [
            ('United States', 'US', 'New York', 40.7128, -74.0060),
            ('United Kingdom', 'GB', 'London', 51.5074, -0.1278),
            ('Germany', 'DE', 'Berlin', 52.5200, 13.4050),
            ('France', 'FR', 'Paris', 48.8566, 2.3522),
            ('Japan', 'JP', 'Tokyo', 35.6762, 139.6503),
            ('Australia', 'AU', 'Sydney', -33.8688, 151.2093),
            ('Brazil', 'BR', 'São Paulo', -23.5505, -46.6333),
            ('India', 'IN', 'Mumbai', 19.0760, 72.8777),
            ('China', 'CN', 'Beijing', 39.9042, 116.4074),
            ('Canada', 'CA', 'Toronto', 43.6532, -79.3832),
        ]

        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        paths = ['/api/users', '/api/products', '/api/orders', '/dashboard', '/login', '/admin', '/api/search']
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]

        self.stdout.write(f"Generating {count} analytics records...")

        created_count = 0
        threat_count = 0

        for i in range(count):
            # Random timestamp within last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            timestamp = timezone.now() - timedelta(days=days_ago, hours=hours_ago)

            # Random country
            country, country_code, city, lat, lng = random.choice(countries)

            # Random IP
            ip_address = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

            # Random request details
            method = random.choice(methods)
            path = random.choice(paths)

            # 80% allowed, 20% blocked
            action_taken = 'blocked' if random.random() < 0.2 else 'allowed'

            # Threat level (higher for blocked requests)
            if action_taken == 'blocked':
                threat_level = random.choices(
                    ['low', 'medium', 'high', 'critical'],
                    weights=[10, 40, 35, 15]
                )[0]
            else:
                threat_level = random.choices(
                    ['none', 'low'],
                    weights=[90, 10]
                )[0]

            # Status code
            if action_taken == 'blocked':
                status_code = random.choice([403, 429, 444])
            else:
                status_code = random.choices(
                    [200, 201, 204, 301, 302, 400, 404, 500],
                    weights=[60, 10, 5, 5, 5, 5, 5, 5]
                )[0]

            # Response time (blocked requests are faster)
            response_time = random.uniform(10, 50) if action_taken == 'blocked' else random.uniform(50, 500)

            # Create analytics record
            analytics = RequestAnalytics.objects.create(
                site=site,
                timestamp=timestamp,
                ip_address=ip_address,
                country=country,
                country_code=country_code,
                city=city,
                region=city,
                latitude=lat + random.uniform(-0.5, 0.5),  # Add some variation
                longitude=lng + random.uniform(-0.5, 0.5),
                request_method=method,
                request_url=f"https://{site.host}{path}",
                request_path=path,
                user_agent=random.choice(user_agents),
                status_code=status_code,
                response_time=response_time,
                action_taken=action_taken,
                threat_level=threat_level,
            )

            created_count += 1

            # Create threat alerts for high/critical threats
            if threat_level in ['high', 'critical'] and random.random() < 0.3:
                alert_types = ['high_volume', 'repeated_blocks', 'new_threat']

                alert = ThreatAlert.objects.create(
                    site=site,
                    timestamp=timestamp,
                    alert_type=random.choice(alert_types),
                    severity=threat_level,
                    ip_address=ip_address,
                    country_code=country_code,
                    description=f"Detected {threat_level} threat from {ip_address} ({country})",
                    request_count=random.randint(5, 50),
                    is_resolved=random.random() < 0.3,
                )
                alert.analytics.add(analytics)
                threat_count += 1

            if (i + 1) % 50 == 0:
                self.stdout.write(f"  Generated {i + 1}/{count} records...")

        self.stdout.write(self.style.SUCCESS(f"\n✓ Successfully created {created_count} analytics records"))
        self.stdout.write(self.style.SUCCESS(f"✓ Created {threat_count} threat alerts"))
        self.stdout.write(f"\nYou can now view the analytics dashboard at: /analytics/{site.slug}/")
