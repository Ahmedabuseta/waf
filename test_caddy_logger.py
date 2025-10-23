#!/usr/bin/env python
"""
Test Caddy Logger with Separator Lines
Demonstrates the ###### separator logs for add/remove/update operations
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waf_app.settings')
django.setup()

from site_management.utils.enhanced_caddy_manager import EnhancedCaddyManager, CaddyConfig
from site_management.models import Site


def test_caddy_logger_separators():
    """
    Test Caddy operations and verify logger separators are working
    """
    print("=" * 80)
    print("TESTING CADDY LOGGER WITH SEPARATORS")
    print("=" * 80)

    # Initialize Caddy Manager
    caddy = EnhancedCaddyManager(
        api_url="http://localhost:2019",
        enable_logging=True,
        enable_validation=True
    )

    print("\n✓ Caddy Manager initialized with logging enabled")
    print(f"✓ Log directory: {caddy.logger.log_dir if caddy.logger else 'Not available'}")

    # Test domain
    test_domain = "test-logger.example.com"

    print("\n" + "─" * 80)
    print("TEST 1: Add Site Operation")
    print("─" * 80)

    # Create test configuration
    config = CaddyConfig(
        host=test_domain,
        addresses=["http://127.0.0.1:8080"],
        protocol="https",
        auto_ssl=False,  # Disable auto SSL for testing
        support_subdomains=False,
        ssl_cert_path=None,
        ssl_key_path=None,
        ssl_chain_path=None
    )

    print(f"\n📝 Configuration:")
    print(f"   Host: {config.host}")
    print(f"   Protocol: {config.protocol}")
    print(f"   Addresses: {config.addresses}")
    print(f"   Auto SSL: {config.auto_ssl}")

    print("\n🔄 Adding site to Caddy...")
    result = caddy.add_site(config)

    if result.get('success'):
        print(f"✅ Site added successfully!")
        print(f"   Duration: {result.get('duration', 0):.2f}s")
        print(f"   SSL Strategy: {result.get('ssl_strategy', {}).get('type', 'unknown')}")
        print("\n✓ Check logs for ###### separator lines!")
    else:
        print(f"❌ Failed to add site: {result.get('error')}")
        print(f"   Validation errors: {result.get('validation_errors', [])}")
        print("\n✓ Check error logs for ###### separator lines!")

    print("\n" + "─" * 80)
    print("TEST 2: Update Site Operation")
    print("─" * 80)

    # Modify configuration
    config.addresses = ["http://127.0.0.1:8081"]

    print(f"\n📝 Updated Configuration:")
    print(f"   Host: {config.host}")
    print(f"   New Addresses: {config.addresses}")

    print("\n🔄 Updating site in Caddy...")
    result = caddy.update_site(config)

    if result.get('success'):
        print(f"✅ Site updated successfully!")
        print(f"   Duration: {result.get('duration', 0):.2f}s")
        print("\n✓ Check logs for UPDATE ###### separator lines!")
    else:
        print(f"❌ Failed to update site: {result.get('error')}")
        print("\n✓ Check error logs for ###### separator lines!")

    print("\n" + "─" * 80)
    print("TEST 3: Remove Site Operation")
    print("─" * 80)

    print(f"\n🔄 Removing site from Caddy...")
    result = caddy.remove_site(test_domain)

    if result.get('success'):
        print(f"✅ Site removed successfully!")
        print(f"   Duration: {result.get('duration', 0):.2f}s")
        print(f"   Files removed: {len(result.get('files_removed', []))}")
        print("\n✓ Check logs for REMOVE ###### separator lines!")
    else:
        print(f"❌ Failed to remove site: {result.get('error')}")
        print("\n✓ Check error logs for ###### separator lines!")

    # Show log file locations
    print("\n" + "=" * 80)
    print("LOG FILE LOCATIONS")
    print("=" * 80)

    if caddy.logger:
        print(f"\n📁 Main Operations Log:")
        print(f"   {caddy.logger.operations_log_dir / 'caddy_operations.log'}")

        print(f"\n📁 Site-Specific Log:")
        print(f"   {caddy.logger.sites_log_dir / f'{test_domain}.log'}")

        print(f"\n📁 All Logs Directory:")
        print(f"   {caddy.logger.log_dir}")

        # Display recent log entries
        print("\n" + "=" * 80)
        print("RECENT LOG ENTRIES (with separators)")
        print("=" * 80)

        operations_log = caddy.logger.operations_log_dir / 'caddy_operations.log'
        if operations_log.exists():
            print("\n📄 Main Operations Log (last 30 lines):\n")
            with open(operations_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-30:]:
                    # Highlight separator lines
                    if '######' in line:
                        print(f"\033[1;32m{line.rstrip()}\033[0m")  # Green bold
                    elif 'ERROR' in line:
                        print(f"\033[1;31m{line.rstrip()}\033[0m")  # Red bold
                    elif 'COMPLETE' in line or 'SUCCESS' in line:
                        print(f"\033[1;34m{line.rstrip()}\033[0m")  # Blue bold
                    else:
                        print(line.rstrip())

        site_log = caddy.logger.sites_log_dir / f'{test_domain}.log'
        if site_log.exists():
            print(f"\n📄 Site-Specific Log ({test_domain}):\n")
            with open(site_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    if 'ERROR' in line:
                        print(f"\033[1;31m{line.rstrip()}\033[0m")
                    elif 'SUCCESS' in line:
                        print(f"\033[1;32m{line.rstrip()}\033[0m")
                    else:
                        print(line.rstrip())

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE!")
    print("=" * 80)
    print("\n📊 Summary:")
    print("   - Logger separators (#######) added to all operations")
    print("   - Check log files above for visual separation")
    print("   - Separators appear at:")
    print("     • Add Site Complete")
    print("     • Add Site Failed")
    print("     • Add Site Error")
    print("     • Update Site Start")
    print("     • Remove Site Complete")
    print("     • Remove Site Failed")
    print("     • Remove Site Error")
    print("\n")


def view_logs_only():
    """
    Just view existing logs without running tests
    """
    print("=" * 80)
    print("VIEWING CADDY LOGS")
    print("=" * 80)

    caddy = EnhancedCaddyManager(enable_logging=True)

    if not caddy.logger:
        print("\n❌ Logger not available!")
        return

    operations_log = caddy.logger.operations_log_dir / 'caddy_operations.log'

    if not operations_log.exists():
        print("\n⚠️  No operations log found yet.")
        print(f"   Expected location: {operations_log}")
        print("\n   Run the test first: python test_caddy_logger.py")
        return

    print(f"\n📄 Operations Log: {operations_log}")
    print("\n" + "─" * 80)

    with open(operations_log, 'r') as f:
        for line in f:
            # Highlight separator lines
            if '######' in line:
                print(f"\033[1;32m{line.rstrip()}\033[0m")  # Green bold
            elif 'ERROR' in line:
                print(f"\033[1;31m{line.rstrip()}\033[0m")  # Red bold
            elif 'COMPLETE' in line or 'SUCCESS' in line:
                print(f"\033[1;34m{line.rstrip()}\033[0m")  # Blue bold
            else:
                print(line.rstrip())

    print("\n" + "─" * 80)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'view':
        view_logs_only()
    else:
        print("\n💡 TIP: This test will attempt to connect to Caddy at localhost:2019")
        print("   If Caddy is not running, you'll still see the logger output.\n")

        try:
            test_caddy_logger_separators()
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
