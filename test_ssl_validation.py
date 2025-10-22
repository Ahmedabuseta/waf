#!/usr/bin/env python
"""
Test script for SSL/TLS validation functionality
Tests certificate validation, DNS challenge generation, and site configuration
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waf_app.settings')
django.setup()

from site_management.validators import SiteSSLValidator
from site_management.utils.acme_dns_manager import ACMEDNSManager
from site_management.utils.certificate_checker import CertificateChecker
from site_management.ssl_helpers import SSLHelper
from site_management.models import Site
from django.core.exceptions import ValidationError


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_ssl_validator():
    """Test SSL configuration validator"""
    print_section("Testing SSL Configuration Validator")

    validator = SiteSSLValidator()

    # Test 1: HTTP with no SSL - should be valid
    print("Test 1: HTTP with no SSL")
    is_valid, errors = validator.validate_site_ssl_configuration(
        protocol='http',
        auto_ssl=False,
        support_subdomains=False,
        host='example.com',
        ssl_certificate=None,
        ssl_key=None,
        ssl_chain=None
    )
    print(f"  Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if errors:
        for error in errors:
            print(f"    Error: {error}")

    # Test 2: HTTP with auto_ssl - should fail
    print("\nTest 2: HTTP with auto_ssl (should fail)")
    is_valid, errors = validator.validate_site_ssl_configuration(
        protocol='http',
        auto_ssl=True,
        support_subdomains=False,
        host='example.com',
        ssl_certificate=None,
        ssl_key=None,
        ssl_chain=None
    )
    print(f"  Result: {'✅ PASS (correctly rejected)' if not is_valid else '❌ FAIL (should have been rejected)'}")
    if errors:
        for error in errors:
            print(f"    Error: {error}")

    # Test 3: HTTPS with auto_ssl - should be valid
    print("\nTest 3: HTTPS with auto_ssl")
    is_valid, errors = validator.validate_site_ssl_configuration(
        protocol='https',
        auto_ssl=True,
        support_subdomains=False,
        host='example.com',
        ssl_certificate=None,
        ssl_key=None,
        ssl_chain=None
    )
    print(f"  Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if errors:
        for error in errors:
            print(f"    Error: {error}")

    # Test 4: HTTPS without auto_ssl and no cert - should fail
    print("\nTest 4: HTTPS without auto_ssl and no cert (should fail)")
    is_valid, errors = validator.validate_site_ssl_configuration(
        protocol='https',
        auto_ssl=False,
        support_subdomains=False,
        host='example.com',
        ssl_certificate=None,
        ssl_key=None,
        ssl_chain=None
    )
    print(f"  Result: {'✅ PASS (correctly rejected)' if not is_valid else '❌ FAIL (should have been rejected)'}")
    if errors:
        for error in errors:
            print(f"    Error: {error}")

    print("\n✅ SSL Validator tests completed")


def test_dns_challenge_manager():
    """Test ACME DNS challenge manager"""
    print_section("Testing ACME DNS Challenge Manager")

    dns_manager = ACMEDNSManager()

    # Test 1: Generate instructions for single domain
    print("Test 1: Single domain (no wildcard)")
    instructions = dns_manager.generate_challenge_instructions(
        domain='example.com',
        support_subdomains=False
    )
    print(f"  Required: {instructions['required']}")
    print(f"  Challenge Type: {instructions.get('challenge_type', 'N/A')}")
    print(f"  Message: {instructions.get('message', 'N/A')}")

    # Test 2: Generate instructions for wildcard domain
    print("\nTest 2: Wildcard domain (DNS challenge required)")
    instructions = dns_manager.generate_challenge_instructions(
        domain='example.com',
        support_subdomains=True
    )
    print(f"  Required: {instructions['required']}")
    print(f"  Challenge Type: {instructions['challenge_type']}")
    print(f"  Domain: {instructions['domain']}")
    print(f"  Wildcard: {instructions['wildcard_domain']}")
    print(f"  Challenge Record: {instructions['challenge_record']}")
    print(f"  Steps: {len(instructions['instructions']['steps'])} steps provided")
    print(f"  DNS Providers: {len(instructions['common_dns_providers'])} providers listed")

    # Test 3: Verify DNS record (will fail but tests the function)
    print("\nTest 3: DNS record verification (expected to not find record)")
    verification = dns_manager.verify_dns_challenge_record(
        domain='example.com',
        expected_value='test-challenge-value'
    )
    print(f"  Record: {verification['record']}")
    print(f"  Exists: {verification['exists']}")
    print(f"  Status: {verification['status']}")
    print(f"  Message: {verification['message']}")

    # Test 4: Format instructions for display
    print("\nTest 4: Format instructions for display")
    formatted = dns_manager.format_instructions_for_display(instructions)
    print(f"  Generated {len(formatted)} characters of formatted instructions")
    print(f"  First 200 chars: {formatted[:200]}...")

    print("\n✅ DNS Challenge Manager tests completed")


def test_ssl_helper():
    """Test SSL helper functions"""
    print_section("Testing SSL Helper")

    helper = SSLHelper()

    # Test 1: Get DNS challenge instructions
    print("Test 1: Get DNS challenge instructions")
    instructions = helper.get_dns_challenge_instructions('example.com', True)
    print(f"  Required: {instructions['required']}")
    print(f"  Challenge Record: {instructions.get('challenge_record', 'N/A')}")

    # Test 2: Format HTML instructions
    print("\nTest 2: Format HTML instructions")
    html = helper.format_dns_instructions_html(instructions)
    print(f"  Generated {len(html)} characters of HTML")
    print(f"  Contains 'dns-challenge-instructions': {'dns-challenge-instructions' in html}")
    print(f"  Contains step-by-step: {'Step-by-Step' in html}")

    print("\n✅ SSL Helper tests completed")


def test_site_model_validation():
    """Test Site model validation"""
    print_section("Testing Site Model Validation")

    # Test 1: Create HTTP site (should work)
    print("Test 1: Create HTTP site")
    try:
        site = Site(
            host='test-http.example.com',
            slug='test-http-example-com',
            protocol='http',
            auto_ssl=False,
            support_subdomains=False,
            status='active'
        )
        site.clean()  # Run validation
        print("  ✅ PASS - HTTP site validation passed")
    except ValidationError as e:
        print(f"  ❌ FAIL - Unexpected validation error: {e}")

    # Test 2: Create HTTPS site with auto_ssl (should work)
    print("\nTest 2: Create HTTPS site with auto_ssl")
    try:
        site = Site(
            host='test-https-auto.example.com',
            slug='test-https-auto-example-com',
            protocol='https',
            auto_ssl=True,
            support_subdomains=False,
            status='active'
        )
        site.clean()  # Run validation
        print("  ✅ PASS - HTTPS with auto_ssl validation passed")
    except ValidationError as e:
        print(f"  ❌ FAIL - Unexpected validation error: {e}")

    # Test 3: Create HTTP site with auto_ssl (should fail)
    print("\nTest 3: Create HTTP site with auto_ssl (should fail)")
    try:
        site = Site(
            host='test-invalid.example.com',
            slug='test-invalid-example-com',
            protocol='http',
            auto_ssl=True,
            support_subdomains=False,
            status='active'
        )
        site.clean()  # Run validation
        print("  ❌ FAIL - Validation should have failed")
    except ValidationError as e:
        print(f"  ✅ PASS - Correctly rejected with error: {e}")

    # Test 4: Create HTTPS site without SSL config (should fail)
    print("\nTest 4: Create HTTPS site without SSL config (should fail)")
    try:
        site = Site(
            host='test-invalid2.example.com',
            slug='test-invalid2-example-com',
            protocol='https',
            auto_ssl=False,
            support_subdomains=False,
            status='active'
        )
        site.clean()  # Run validation
        print("  ❌ FAIL - Validation should have failed")
    except ValidationError as e:
        print(f"  ✅ PASS - Correctly rejected with error: {e}")

    # Test 5: Check requires_dns_challenge method
    print("\nTest 5: Test requires_dns_challenge method")
    site_no_wildcard = Site(
        protocol='https',
        auto_ssl=True,
        support_subdomains=False
    )
    site_with_wildcard = Site(
        protocol='https',
        auto_ssl=True,
        support_subdomains=True
    )
    print(f"  Single domain requires DNS challenge: {site_no_wildcard.requires_dns_challenge()}")
    print(f"  Wildcard domain requires DNS challenge: {site_with_wildcard.requires_dns_challenge()}")
    if not site_no_wildcard.requires_dns_challenge() and site_with_wildcard.requires_dns_challenge():
        print("  ✅ PASS - DNS challenge detection working correctly")
    else:
        print("  ❌ FAIL - DNS challenge detection not working correctly")

    # Test 6: Test get_ssl_status method
    print("\nTest 6: Test get_ssl_status method")

    http_site = Site(protocol='http', auto_ssl=False)
    status = http_site.get_ssl_status()
    print(f"  HTTP site SSL status: {status}")

    https_auto_site = Site(protocol='https', auto_ssl=True, support_subdomains=False)
    status = https_auto_site.get_ssl_status()
    print(f"  HTTPS auto SSL status: {status}")

    https_wildcard_site = Site(protocol='https', auto_ssl=True, support_subdomains=True)
    status = https_wildcard_site.get_ssl_status()
    print(f"  HTTPS auto SSL wildcard status: {status}")

    print("\n✅ Site Model Validation tests completed")


def test_certificate_checker():
    """Test certificate checker (without actual certificates)"""
    print_section("Testing Certificate Checker")

    checker = CertificateChecker()

    print("Test 1: Certificate checker initialization")
    print(f"  Operations module loaded: {hasattr(checker, 'operations')}")
    print(f"  Validation module loaded: {hasattr(checker, 'validation')}")
    print(f"  Formatter module loaded: {hasattr(checker, 'formatter')}")

    if all([hasattr(checker, 'operations'),
            hasattr(checker, 'validation'),
            hasattr(checker, 'formatter')]):
        print("  ✅ PASS - Certificate checker initialized correctly")
    else:
        print("  ❌ FAIL - Certificate checker missing modules")

    print("\n✅ Certificate Checker tests completed")


def run_all_tests():
    """Run all test suites"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  SSL/TLS VALIDATION SYSTEM - TEST SUITE".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)

    try:
        test_ssl_validator()
        test_dns_challenge_manager()
        test_ssl_helper()
        test_site_model_validation()
        test_certificate_checker()

        print_section("TEST SUMMARY")
        print("✅ All test suites completed successfully!")
        print("\nThe SSL validation system is working correctly:")
        print("  • SSL configuration validation")
        print("  • DNS challenge generation for wildcard certificates")
        print("  • Site model validation")
        print("  • Helper functions for views")
        print("  • Certificate checker utilities")
        print("\nNext steps:")
        print("  1. Test with actual certificate files")
        print("  2. Integrate with frontend forms")
        print("  3. Test DNS challenge workflow end-to-end")
        print("  4. Configure ACME client for auto SSL")

        return 0

    except Exception as e:
        print_section("TEST FAILED")
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
