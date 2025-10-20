"""
Management command to sync all sites to Caddy server
"""
from django.core.management.base import BaseCommand
from site_mangement.caddy_utils import sync_all_sites_to_caddy, sync_site_to_caddy
from site_mangement.models import Site


class Command(BaseCommand):
    help = 'Sync all active sites to Caddy server'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--site',
            type=str,
            help='Sync only a specific site by slug',
        )
    
    def handle(self, *args, **options):
        site_slug = options.get('site')
        
        if site_slug:
            # Sync specific site
            try:
                site = Site.objects.get(slug=site_slug)
                self.stdout.write(f'Syncing site: {site.host}...')
                
                if sync_site_to_caddy(site):
                    self.stdout.write(self.style.SUCCESS(f'✅ Successfully synced {site.host}'))
                else:
                    self.stdout.write(self.style.ERROR(f'❌ Failed to sync {site.host}'))
            except Site.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Site not found: {site_slug}'))
        else:
            # Sync all sites
            self.stdout.write('Syncing all active sites to Caddy...')
            results = sync_all_sites_to_caddy()
            
            self.stdout.write('')
            self.stdout.write('=' * 60)
            self.stdout.write(f'Results:')
            self.stdout.write(f'  Synced: {results["synced"]}')
            self.stdout.write(f'  Failed: {results["failed"]}')
            self.stdout.write(f'  Skipped: {results["skipped"]}')
            self.stdout.write('=' * 60)
            
            if results['synced'] > 0:
                self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully synced {results["synced"]} site(s)'))
            if results['failed'] > 0:
                self.stdout.write(self.style.ERROR(f'\n❌ Failed to sync {results["failed"]} site(s)'))







