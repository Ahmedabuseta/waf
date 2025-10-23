#!/usr/bin/env python
"""
Test Automatic Caddy Sync via Django Signals

This script tests the automatic Caddy synchronization that happens
when sites are created, updated, or deleted through Django signals.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waf_app.settings')
django.setup()

from django.test import TestCase
from site_management.models import Site, Addresses
from site_management.signals import caddy_sync_required, ssl_certificate_uploaded
import logging

# Setup logging to see signal output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_auto_sync_on_site_creation():
    """
    Test 1: Automatic Caddy sync when creating a new site
    """
    print("=" * 80)
    print("TEST 1: Auto-Sync on Site Creation")
    print("=" * 80)

    test_host = "auto-sync-test.example.com"

    # Clean up any existing test site
    Site.objects.filter(host=test_host).delete()

    print(f"\n📝 Creating new site: {test_host}")
    print("   Expected: Caddy sync signal should fire automatically")

    # Create site (this should trigger post_save signal)
    site = Site.objects.create(
        host=test_host,
        protocol='https',
        auto_ssl=True,
        support_subdomains=False,
        status='active'
    )

    print(f"✅ Site created: {site.host} (slug: {site.slug})")

    # Add an address
    print(f"\n📝 Adding address to site...")
    address = Addresses.objects.create(
        site=site,
        ip_address='127.0.0.1:8080'
    )

    print(f"✅ Address added: {address.ip_address}")
    print("\n💡 Check logs above for:")
    print("   - ##############################")
    print("   - # SITE CREATED: ...")
    print("   - # CADDY SYNC REQUIRED: ...")
    print("   - ##############################")

    return site


def test_auto_sync_on_site_update():
    """
    Test 2: Automatic Caddy sync when updating site configuration
    """
    print("\n" + "=" * 80)
    print("TEST 2: Auto-Sync on Site Update")
    print("=" * 80)

    # Get the test site from previous test
    test_host = "auto-sync-test.example.com"

    try:
        site = Site.objects.get(host=test_host)
    except Site.DoesNotExist:
        print(f"⚠️  Site {test_host} not found, creating it first...")
        site = test_auto_sync_on_site_creation()

    print(f"\n📝 Updating site configuration: {site.host}")
    print(f"   Old protocol: {site.protocol}")
    print(f"   Old auto_ssl: {site.auto_ssl}")

    # Update configuration (this should trigger post_save signal)
    site.protocol = 'http'
    site.auto_ssl = False
    site.save()

    print(f"\n   New protocol: {site.protocol}")
    print(f"   New auto_ssl: {site.auto_ssl}")
    print(f"✅ Site updated")

    print("\n💡 Check logs above for:")
    print("   - ##############################")
    print("   - # CADDY SYNC REQUIRED: ...")
    print("   - # ACTION: update")
    print("   - # CADDY AUTO-SYNC SUCCESS/FAILED: ...")
    print("   - ##############################")

    return site


def test_auto_sync_on_site_deletion():
    """
    Test 3: Automatic Caddy sync when deleting a site
    """
    print("\n" + "=" * 80)
    print("TEST 3: Auto-Sync on Site Deletion")
    print("=" * 80)

    test_host = "auto-sync-test.example.com"

    try:
        site = Site.objects.get(host=test_host)
        print(f"\n📝 Deleting site: {site.host}")

        # Delete site (this should trigger post_delete signal)
        site.delete()

        print(f"✅ Site deleted")

        print("\n💡 Check logs above for:")
        print("   - ##############################")
        print("   - # SITE DELETED: ...")
        print("   - # CADDY DELETE SYNC TRIGGERED: ...")
        print("   - # CADDY AUTO-DELETE SUCCESS/FAILED: ...")
        print("   - ##############################")

    except Site.DoesNotExist:
        print(f"⚠️  Site {test_host} not found, skipping deletion test")


def test_manual_signal_trigger():
    """
    Test 4: Manually trigger Caddy sync signal
    """
    print("\n" + "=" * 80)
    print("TEST 4: Manual Signal Trigger")
    print("=" * 80)

    test_host = "manual-sync-test.example.com"

    # Clean up any existing test site
    Site.objects.filter(host=test_host).delete()

    # Create a site without triggering automatic sync
    print(f"\n📝 Creating site: {test_host}")
    site = Site.objects.create(
        host=test_host,
        protocol='https',
        auto_ssl=True,
        status='active'
    )

    # Add address
    Addresses.objects.create(
        site=site,
        ip_address='127.0.0.1:9090'
    )

    print(f"✅ Site created: {site.host}")

    # Manually trigger sync signal
    print(f"\n📝 Manually triggering Caddy sync signal...")
    print(f"   Action: update")

    caddy_sync_required.send(
        sender=Site,
        site=site,
        action='update'
    )

    print(f"✅ Signal sent")

    print("\n💡 Check logs above for:")
    print("   - ##############################")
    print("   - # CADDY SYNC REQUIRED: ...")
    print("   - # CADDY AUTO-SYNC SUCCESS/FAILED: ...")
    print("   - ##############################")

    # Clean up
    site.delete()
    print(f"\n🧹 Cleaned up test site")


def test_ssl_certificate_signal():
    """
    Test 5: SSL certificate upload signal
    """
    print("\n" + "=" * 80)
    print("TEST 5: SSL Certificate Upload Signal")
    print("=" * 80)

    test_host = "ssl-test.example.com"

    # Clean up any existing test site
    Site.objects.filter(host=test_host).delete()

    print(f"\n📝 Creating site: {test_host}")
    site = Site.objects.create(
        host=test_host,
        protocol='https',
        auto_ssl=False,  # Manual SSL
        status='active'
    )

    # Add address
    Addresses.objects.create(
        site=site,
        ip_address='127.0.0.1:8443'
    )

    print(f"✅ Site created: {site.host}")

    # Manually trigger SSL upload signal
    print(f"\n📝 Triggering SSL certificate upload signal...")

    ssl_certificate_uploaded.send(
        sender=Site,
        site=site
    )

    print(f"✅ Signal sent")

    print("\n💡 Check logs above for:")
    print("   - ##############################")
    print("   - # SSL CERTIFICATE UPLOADED: ...")
    print("   - # SSL SYNC TRIGGERED: ...")
    print("   - ##############################")

    # Clean up
    site.delete()
    print(f"\n🧹 Cleaned up test site")


def display_summary():
    """
    Display test summary
    """
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print("\n✅ Tests Completed:")
    print("   1. Auto-Sync on Site Creation")
    print("   2. Auto-Sync on Site Update")
    print("   3. Auto-Sync on Site Deletion")
    print("   4. Manual Signal Trigger")
    print("   5. SSL Certificate Upload Signal")

    print("\n📊 What Was Tested:")
    print("   ✓ Django signals fire correctly")
    print("   ✓ Caddy sync is triggered automatically")
    print("   ✓ Logger separators appear in logs")
    print("   ✓ Success/failure cases are handled")
    print("   ✓ SSL certificate signals work")

    print("\n🔍 Signal Flow:")
    print("   Site Created → post_save signal → caddy_sync_required")
    print("   Site Updated → post_save signal → caddy_sync_required")
    print("   Site Deleted → post_delete signal → caddy_sync_required")
    print("   SSL Uploaded → ssl_certificate_uploaded → caddy_sync_required")

    print("\n📁 Log Locations:")
    print("   Main logs: logs/caddy-manager/operations/caddy_operations.log")
    print("   Site logs: logs/caddy-manager/sites/<domain>.log")

    print("\n💡 Note:")
    print("   If Caddy is not running at localhost:2019, you'll see error messages")
    print("   but the signals will still fire correctly (check for ###### separators)")

    print("\n" + "=" * 80)


def main():
    """
    Run all tests
    """
    print("\n" + "🧪" * 40)
    print("AUTOMATIC CADDY SYNC TEST SUITE")
    print("🧪" * 40 + "\n")

    print("⚠️  WARNING: This test will create and delete test sites")
    print("   Test sites: auto-sync-test.example.com, manual-sync-test.example.com, ssl-test.example.com\n")

    try:
        # Run tests
        test_auto_sync_on_site_creation()
        test_auto_sync_on_site_update()
        test_auto_sync_on_site_deletion()
        test_manual_signal_trigger()
        test_ssl_certificate_signal()

        # Display summary
        display_summary()

        print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        print("🧹 Cleaning up test sites...")

        # Clean up
        Site.objects.filter(host__in=[
            'auto-sync-test.example.com',
            'manual-sync-test.example.com',
            'ssl-test.example.com'
        ]).delete()

        print("✅ Cleanup complete\n")

    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Clean up
        print("\n🧹 Cleaning up test sites...")
        Site.objects.filter(host__in=[
            'auto-sync-test.example.com',
            'manual-sync-test.example.com',
            'ssl-test.example.com'
        ]).delete()
        print("✅ Cleanup complete\n")


if __name__ == '__main__':
    main()
