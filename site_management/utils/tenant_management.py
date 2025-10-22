#!/usr/bin/env python3
"""
Tenant Management Scripts for Caddy WAF System
Provides command-line interface for managing sites with comprehensive logging
"""
import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

# Add the parent directory to the path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "site_management"))

try:
    from enhanced_caddy_manager import EnhancedCaddyManager, CaddyConfig
    from caddy_logger import caddy_logger
    # Assuming Django integration
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
    import django
    django.setup()
    from your_app.models import Site  # Replace with your actual app name
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed and Django is configured")
    sys.exit(1)


class TenantManager:
    """Command-line interface for tenant management"""

    def __init__(self):
        self.caddy_manager = EnhancedCaddyManager()

    def add_tenant(self, domain: str, force: bool = False) -> bool:
        """Add a new tenant from Django model"""
        try:
            print(f"🚀 Adding tenant: {domain}")

            # Get site from Django model
            try:
                site = Site.objects.get(domain=domain)
            except Site.DoesNotExist:
                print(f"❌ Site '{domain}' not found in database")
                return False

            # Check if site already exists
            existing_config = self.caddy_manager._get_existing_config(domain)
            if existing_config and not force:
                print(f"⚠️  Site '{domain}' already exists. Use --force to overwrite")
                return False

            # Convert Django model to CaddyConfig
            config = self._site_model_to_config(site)

            # Add site
            result = self.caddy_manager.add_site(config)

            if result["success"]:
                print(f"✅ Successfully added tenant: {domain}")
                print(f"   SSL Strategy: {result['ssl_strategy']['type']}")
                print(f"   Duration: {result['duration']:.2f}s")
                if 'cert_path' in result['ssl_strategy']:
                    print(f"   Certificate: {result['ssl_strategy']['cert_path']}")
                return True
            else:
                print(f"❌ Failed to add tenant: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Error adding tenant: {e}")
            return False

    def remove_tenant(self, domain: str, confirm: bool = False) -> bool:
        """Remove a tenant and cleanup files"""
        try:
            if not confirm:
                response = input(f"⚠️  Are you sure you want to remove '{domain}'? This will delete all configurations and certificates. (y/N): ")
                if response.lower() != 'y':
                    print("❌ Operation cancelled")
                    return False

            print(f"🗑️  Removing tenant: {domain}")

            result = self.caddy_manager.remove_site(domain)

            if result["success"]:
                print(f"✅ Successfully removed tenant: {domain}")
                print(f"   Duration: {result['duration']:.2f}s")
                print(f"   Files removed: {len(result['files_removed'])}")
                return True
            else:
                print(f"❌ Failed to remove tenant: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Error removing tenant: {e}")
            return False

    def update_tenant(self, domain: str) -> bool:
        """Update existing tenant configuration"""
        try:
            print(f"🔄 Updating tenant: {domain}")

            # Get site from Django model
            try:
                site = Site.objects.get(domain=domain)
            except Site.DoesNotExist:
                print(f"❌ Site '{domain}' not found in database")
                return False

            # Convert Django model to CaddyConfig
            config = self._site_model_to_config(site)

            # Update site
            result = self.caddy_manager.update_site(config)

            if result["success"]:
                print(f"✅ Successfully updated tenant: {domain}")
                print(f"   SSL Strategy: {result['ssl_strategy']['type']}")
                print(f"   Duration: {result['duration']:.2f}s")
                return True
            else:
                print(f"❌ Failed to update tenant: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Error updating tenant: {e}")
            return False

    def list_tenants(self, detailed: bool = False) -> bool:
        """List all managed tenants"""
        try:
            print("📋 Listing all tenants:")
            sites = self.caddy_manager.list_sites()

            if not sites:
                print("   No tenants found")
                return True

            for site in sites:
                domain = site["domain"]
                status = "✅" if site["config_exists"] else "❌"

                if detailed:
                    print(f"\n{status} {domain}")
                    print(f"   Config: {site.get('config_file', 'N/A')}")
                    print(f"   Modified: {site.get('config_modified', 'N/A')}")

                    # Certificate info
                    if site["certificates"]:
                        print("   Certificates:")
                        for cert_name, cert_info in site["certificates"].items():
                            if "error" not in cert_info:
                                expires = cert_info.get("expires", "Unknown")
                                print(f"     - {cert_name}: expires {expires}")
                            else:
                                print(f"     - {cert_name}: ❌ {cert_info['error']}")

                    # Recent operations
                    if site.get("last_operations"):
                        print("   Recent operations:")
                        for op in site["last_operations"][-3:]:
                            op_status = "✅" if op["success"] else "❌"
                            print(f"     {op_status} {op['operation']} ({op['timestamp']})")
                else:
                    cert_count = len(site["certificates"])
                    error_count = site.get("error_count", 0)
                    print(f"   {status} {domain} (certs: {cert_count}, errors: {error_count})")

            return True

        except Exception as e:
            print(f"❌ Error listing tenants: {e}")
            return False

    def status_tenant(self, domain: str) -> bool:
        """Show detailed status for a specific tenant"""
        try:
            print(f"📊 Status for tenant: {domain}")

            status = self.caddy_manager.get_site_status(domain)

            # Basic info
            config_status = "✅ Exists" if status["config_exists"] else "❌ Missing"
            print(f"   Configuration: {config_status}")

            if status["config_exists"]:
                print(f"   Config file: {status.get('config_file', 'N/A')}")
                print(f"   Last modified: {status.get('config_modified', 'N/A')}")

            # Certificate info
            print(f"   Certificates: {len(status['certificates'])}")
            for cert_name, cert_info in status["certificates"].items():
                if "error" not in cert_info:
                    cn = cert_info.get("common_name", "N/A")
                    expires = cert_info.get("expires", "Unknown")
                    expired = cert_info.get("is_expired", False)
                    exp_status = "❌ EXPIRED" if expired else "✅ Valid"
                    print(f"     - {cert_name}: CN={cn}, {exp_status}, expires {expires}")

                    # Show SAN domains
                    if cert_info.get("san_domains"):
                        print(f"       SAN: {', '.join(cert_info['san_domains'])}")

                    # Show wildcard domains
                    if cert_info.get("wildcard_domains"):
                        print(f"       Wildcard: {', '.join(cert_info['wildcard_domains'])}")
                else:
                    print(f"     - {cert_name}: ❌ {cert_info['error']}")

            # Operations history
            if status.get("last_operations"):
                print("   Recent operations:")
                for op in status["last_operations"][-5:]:
                    op_status = "✅" if op["success"] else "❌"
                    timestamp = op["timestamp"][:19]  # Remove microseconds
                    print(f"     {op_status} {op['operation']} ({timestamp})")

            # Errors
            error_count = status.get("error_count", 0)
            if error_count > 0:
                print(f"   ⚠️  Errors: {error_count}")
                if status.get("last_error"):
                    last_error = status["last_error"]
                    print(f"     Last error: {last_error['error_type']} - {last_error['message']}")
            else:
                print("   ✅ No errors")

            return True

        except Exception as e:
            print(f"❌ Error getting tenant status: {e}")
            return False

    def validate_tenant(self, domain: str) -> bool:
        """Validate tenant configuration"""
        try:
            print(f"🔍 Validating tenant: {domain}")

            validation = self.caddy_manager.validate_configuration(domain)

            if validation["valid"]:
                print("   ✅ Configuration is valid")
            else:
                print("   ❌ Configuration has errors:")
                for error in validation["errors"]:
                    print(f"     - {error}")

            if validation["warnings"]:
                print("   ⚠️  Warnings:")
                for warning in validation["warnings"]:
                    print(f"     - {warning}")

            # Certificate validation
            if validation["certificate_status"]:
                print("   Certificate validation:")
                for cert_name, cert_status in validation["certificate_status"].items():
                    if cert_status["matches"]:
                        print(f"     ✅ {cert_name}: covers domain ({cert_status['type']} match)")
                    else:
                        print(f"     ❌ {cert_name}: {cert_status['reason']}")

            return validation["valid"]

        except Exception as e:
            print(f"❌ Error validating tenant: {e}")
            return False

    def sync_all_tenants(self, dry_run: bool = False) -> bool:
        """Sync all tenants from Django model"""
        try:
            print("🔄 Syncing all tenants from database...")

            sites = Site.objects.filter(is_active=True)  # Assuming you have an is_active field

            if dry_run:
                print("   DRY RUN - No changes will be made")

            success_count = 0
            error_count = 0

            for site in sites:
                domain = site.domain
                print(f"\n   Processing: {domain}")

                if dry_run:
                    print(f"     Would sync configuration for {domain}")
                    continue

                try:
                    config = self._site_model_to_config(site)
                    result = self.caddy_manager.update_site(config)

                    if result["success"]:
                        print(f"     ✅ Synced successfully")
                        success_count += 1
                    else:
                        print(f"     ❌ Failed: {result.get('error', 'Unknown error')}")
                        error_count += 1

                except Exception as e:
                    print(f"     ❌ Error: {e}")
                    error_count += 1

            print(f"\n📊 Sync complete: {success_count} succeeded, {error_count} failed")
            return error_count == 0

        except Exception as e:
            print(f"❌ Error syncing tenants: {e}")
            return False

    def _site_model_to_config(self, site) -> CaddyConfig:
        """Convert Django Site model to CaddyConfig"""
        # Convert addresses from your model format
        addresses = []
        for addr in site.addresses.filter(is_active=True):  # Assuming related model
            addresses.append({
                'ip_address': addr.ip_address,
                'port': addr.port,
                'is_allowed': addr.is_allowed
            })

        return CaddyConfig(
            host=site.domain,
            addresses=addresses,
            protocol='https' if site.use_ssl else 'http',
            auto_ssl=site.auto_ssl,
            ssl_cert_path=site.ssl_cert_path,
            ssl_key_path=site.ssl_key_path,
            load_balancer_algorithm=site.load_balancer_algorithm or 'round_robin',
            auto_https_redirect=site.auto_https_redirect,
            health_check_path=site.health_check_path or '/health'
        )


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Tenant Management for Caddy WAF System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add example.com                    # Add tenant
  %(prog)s add example.com --force            # Add tenant (overwrite existing)
  %(prog)s remove example.com                 # Remove tenant (with confirmation)
  %(prog)s remove example.com --yes           # Remove tenant (no confirmation)
  %(prog)s update example.com                 # Update tenant configuration
  %(prog)s list                               # List all tenants
  %(prog)s list --detailed                    # List with detailed information
  %(prog)s status example.com                 # Show tenant status
  %(prog)s validate example.com               # Validate tenant configuration
  %(prog)s sync                               # Sync all tenants from database
  %(prog)s sync --dry-run                     # Show what would be synced
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Add tenant
    add_parser = subparsers.add_parser('add', help='Add a new tenant')
    add_parser.add_argument('domain', help='Domain name')
    add_parser.add_argument('--force', action='store_true', help='Overwrite existing configuration')

    # Remove tenant
    remove_parser = subparsers.add_parser('remove', help='Remove a tenant')
    remove_parser.add_argument('domain', help='Domain name')
    remove_parser.add_argument('--yes', action='store_true', help='Skip confirmation')

    # Update tenant
    update_parser = subparsers.add_parser('update', help='Update tenant configuration')
    update_parser.add_argument('domain', help='Domain name')

    # List tenants
    list_parser = subparsers.add_parser('list', help='List all tenants')
    list_parser.add_argument('--detailed', action='store_true', help='Show detailed information')

    # Tenant status
    status_parser = subparsers.add_parser('status', help='Show tenant status')
    status_parser.add_argument('domain', help='Domain name')

    # Validate tenant
    validate_parser = subparsers.add_parser('validate', help='Validate tenant configuration')
    validate_parser.add_argument('domain', help='Domain name')

    # Sync all tenants
    sync_parser = subparsers.add_parser('sync', help='Sync all tenants from database')
    sync_parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without making changes')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize tenant manager
    try:
        tenant_manager = TenantManager()
    except Exception as e:
        print(f"❌ Failed to initialize tenant manager: {e}")
        return 1

    # Execute command
    success = False

    if args.command == 'add':
        success = tenant_manager.add_tenant(args.domain, args.force)
    elif args.command == 'remove':
        success = tenant_manager.remove_tenant(args.domain, args.yes)
    elif args.command == 'update':
        success = tenant_manager.update_tenant(args.domain)
    elif args.command == 'list':
        success = tenant_manager.list_tenants(args.detailed)
    elif args.command == 'status':
        success = tenant_manager.status_tenant(args.domain)
    elif args.command == 'validate':
        success = tenant_manager.validate_tenant(args.domain)
    elif args.command == 'sync':
        success = tenant_manager.sync_all_tenants(args.dry_run)
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
