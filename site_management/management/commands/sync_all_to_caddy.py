"""
Management command to sync all sites to Caddy
Demonstrates using custom signals
"""

from django.core.management.base import BaseCommand
from django.dispatch import receiver
from site_management.models import Site
from site_management.signals import caddy_sync_required


class Command(BaseCommand):
    help = 'Sync all sites to Caddy server using signals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No actual changes will be made'))

        sites = Site.objects.filter(status='active')

        if not sites.exists():
            self.stdout.write(self.style.WARNING('No active sites found'))
            return

        self.stdout.write(f'Found {sites.count()} active sites')

        # Set up signal listener for this command
        synced_count = [0]  # Use list to allow modification in nested function

        @receiver(caddy_sync_required)
        def track_sync(sender, site, action, **kwargs):
            synced_count[0] += 1
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Triggered sync signal for: {site.host} (action: {action})')
            )

        # Trigger sync for all sites
        for site in sites:
            if not dry_run:
                caddy_sync_required.send(
                    sender=self.__class__,
                    site=site,
                    action='sync_all'
                )
            else:
                self.stdout.write(f'  Would sync: {site.host}')

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully triggered sync for {synced_count[0]} sites')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'\nDry run complete. Would have synced {sites.count()} sites')
            )
