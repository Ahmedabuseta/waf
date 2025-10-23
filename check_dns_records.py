#!/usr/bin/env python3
"""
DNS Records Verification Script for Wildcard Certificates

This script helps you verify that your DNS TXT records are correctly configured
for wildcard certificate generation with acme.sh.

Usage:
    python check_dns_records.py example.com value1 value2

Example:
    python check_dns_records.py p2s.tech iLrJgVH3mA7KHGyUXtE5bQXuAQqyJJLYRWg_Lh59kj0 sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos
"""

import sys
import subprocess
import time
from typing import List, Tuple

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_section(text: str):
    """Print formatted section"""
    print(f"\n{'-'*70}")
    print(f"  {text}")
    print(f"{'-'*70}")

def check_dig_available() -> bool:
    """Check if dig command is available"""
    try:
        subprocess.run(['dig', '-v'], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def query_dns_records(domain: str) -> Tuple[bool, List[str]]:
    """
    Query DNS TXT records using dig

    Args:
        domain: The domain to query (e.g., _acme-challenge.example.com)

    Returns:
        Tuple of (success, list of TXT values)
    """
    try:
        result = subprocess.run(
            ['dig', 'TXT', domain, '+short'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return False, []

        # Parse output - each line is a TXT record
        txt_values = []
        for line in result.stdout.strip().split('\n'):
            if line:
                # Remove quotes from the value
                value = line.strip().strip('"')
                if value:
                    txt_values.append(value)

        return True, txt_values

    except Exception as e:
        print(f"Error querying DNS: {e}")
        return False, []

def query_multiple_servers(domain: str) -> dict:
    """Query multiple DNS servers to check propagation"""
    servers = {
        'Google DNS': '8.8.8.8',
        'Cloudflare DNS': '1.1.1.1',
        'Quad9 DNS': '9.9.9.9',
    }

    results = {}

    for name, server in servers.items():
        try:
            result = subprocess.run(
                ['dig', f'@{server}', 'TXT', domain, '+short'],
                capture_output=True,
                text=True,
                timeout=10
            )

            txt_values = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    value = line.strip().strip('"')
                    if value:
                        txt_values.append(value)

            results[name] = txt_values
        except Exception as e:
            results[name] = f"Error: {e}"

    return results

def verify_records(domain: str, expected_values: List[str]):
    """Main verification logic"""

    print_header("DNS TXT Record Verification for Wildcard Certificates")

    # Construct the ACME challenge domain
    if not domain.startswith('_acme-challenge.'):
        acme_domain = f"_acme-challenge.{domain}"
    else:
        acme_domain = domain

    print(f"Domain:          {domain}")
    print(f"ACME Domain:     {acme_domain}")
    print(f"Expected Records: {len(expected_values)}")
    print(f"\nExpected Values:")
    for idx, value in enumerate(expected_values, 1):
        print(f"  Record #{idx}: {value[:40]}...")

    # Check if dig is available
    print_section("Checking Prerequisites")

    if not check_dig_available():
        print("❌ 'dig' command not found!")
        print("   Please install dig:")
        print("   - Ubuntu/Debian: sudo apt-get install dnsutils")
        print("   - CentOS/RHEL:   sudo yum install bind-utils")
        print("   - macOS:         Already installed (usually)")
        return False

    print("✅ 'dig' command is available")

    # Query DNS records
    print_section("Querying DNS Records")
    print(f"Querying: {acme_domain}")

    success, found_values = query_dns_records(acme_domain)

    if not success:
        print("❌ DNS query failed!")
        return False

    if not found_values:
        print("❌ No TXT records found!")
        print(f"\n💡 You need to add {len(expected_values)} TXT record(s) to your DNS provider:")
        for idx, value in enumerate(expected_values, 1):
            print(f"\n   Record #{idx}:")
            print(f"   Type:  TXT")
            print(f"   Name:  {acme_domain}")
            print(f"   Value: {value}")
        return False

    print(f"✅ Found {len(found_values)} TXT record(s) in DNS\n")

    # Display found records
    print("Found DNS Records:")
    for idx, value in enumerate(found_values, 1):
        print(f"  {idx}. {value}")

    # Verify each expected value
    print_section("Verification Results")

    all_matched = True
    for idx, expected_value in enumerate(expected_values, 1):
        if expected_value in found_values:
            print(f"✅ Record #{idx}: VERIFIED")
            print(f"   Expected: {expected_value[:40]}...")
            print(f"   Status:   Found in DNS ✓")
        else:
            print(f"❌ Record #{idx}: NOT FOUND")
            print(f"   Expected: {expected_value}")
            print(f"   Status:   Missing from DNS")
            all_matched = False
        print()

    # Summary
    print_section("Summary")

    if all_matched:
        print(f"✅ SUCCESS! All {len(expected_values)} record(s) verified!")
        print(f"\n   DNS is correctly configured for wildcard certificate generation.")
        print(f"   You can now proceed with certificate verification.")
    else:
        matched_count = sum(1 for val in expected_values if val in found_values)
        print(f"❌ FAILED! Only {matched_count}/{len(expected_values)} record(s) verified.")
        print(f"\n   Missing records need to be added to your DNS provider.")
        print(f"\n   Important: For wildcard certificates, you need {len(expected_values)} TXT records")
        print(f"   with the SAME name ({acme_domain}) but DIFFERENT values.")

    # Check propagation across multiple servers
    print_section("DNS Propagation Check")
    print("Checking propagation across multiple DNS servers...\n")

    propagation_results = query_multiple_servers(acme_domain)

    all_propagated = True
    for server_name, values in propagation_results.items():
        if isinstance(values, str):
            print(f"❌ {server_name}: {values}")
            all_propagated = False
        elif not values:
            print(f"❌ {server_name}: No records found")
            all_propagated = False
        elif len(values) != len(expected_values):
            print(f"⚠️  {server_name}: Found {len(values)}/{len(expected_values)} records")
            all_propagated = False
        else:
            # Check if all expected values are present
            all_present = all(val in values for val in expected_values)
            if all_present:
                print(f"✅ {server_name}: All records present")
            else:
                print(f"⚠️  {server_name}: Some records missing")
                all_propagated = False

    print()
    if all_propagated and all_matched:
        print("✅ DNS records are fully propagated across all tested servers!")
    elif all_matched and not all_propagated:
        print("⚠️  Records are correct but not fully propagated yet.")
        print("   Wait 5-10 minutes and try again.")
    else:
        print("⚠️  DNS configuration incomplete. Add missing records.")

    return all_matched

def main():
    """Main entry point"""

    if len(sys.argv) < 3:
        print("Usage: python check_dns_records.py <domain> <value1> [value2] ...")
        print("\nExample:")
        print("  python check_dns_records.py p2s.tech \\")
        print("    iLrJgVH3mA7KHGyUXtE5bQXuAQqyJJLYRWg_Lh59kj0 \\")
        print("    sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos")
        print("\nNote: For wildcard certificates, you typically need 2 TXT records.")
        sys.exit(1)

    domain = sys.argv[1]
    expected_values = sys.argv[2:]

    success = verify_records(domain, expected_values)

    print_header("Next Steps")

    if success:
        print("1. ✅ Your DNS records are correctly configured")
        print("2. 🔐 You can now verify and generate your wildcard certificate")
        print("3. 🌐 Go to your web interface and click 'Verify DNS & Generate Certificate'")
    else:
        print("1. 📝 Add the missing TXT record(s) to your DNS provider")
        print("2. ⏰ Wait 5-10 minutes for DNS propagation")
        print("3. 🔄 Run this script again to verify")
        print("4. 🔐 Once all records are verified, generate your certificate")

    print()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
