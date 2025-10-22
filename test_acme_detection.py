#!/usr/bin/env python3
"""
Test script to verify acme.sh detection and path resolution
"""
import sys
import os
from pathlib import Path
import subprocess

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waf_app.settings')

def test_acme_path():
    """Test acme.sh path resolution"""
    print("=" * 60)
    print("Testing acme.sh Path Resolution")
    print("=" * 60)

    # Test 1: Check if acme.sh exists at expected location
    acme_sh_path = Path.home() / '.acme.sh' / 'acme.sh'
    print(f"\n1. Checking acme.sh location: {acme_sh_path}")

    if acme_sh_path.exists():
        print(f"   ✅ Found: {acme_sh_path}")
        print(f"   Size: {acme_sh_path.stat().st_size} bytes")
        print(f"   Executable: {os.access(acme_sh_path, os.X_OK)}")
    else:
        print(f"   ❌ Not found at {acme_sh_path}")
        return False

    # Test 2: Check if acme.sh can be executed
    print("\n2. Testing acme.sh execution")
    try:
        result = subprocess.run(
            [str(acme_sh_path), '--version'],
            capture_output=True,
            timeout=5,
            text=True
        )

        if result.returncode == 0:
            print(f"   ✅ acme.sh executed successfully")
            print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"   ❌ acme.sh failed with exit code {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("   ❌ acme.sh execution timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error executing acme.sh: {e}")
        return False

    # Test 3: Import and test CertificateManager
    print("\n3. Testing CertificateManager acme.sh detection")
    try:
        import django
        django.setup()

        from site_management.utils.certificate_manager import CertificateManager

        cm = CertificateManager()
        is_available = cm._check_acme_sh_available()

        if is_available:
            print("   ✅ CertificateManager detected acme.sh successfully")
        else:
            print("   ❌ CertificateManager failed to detect acme.sh")
            return False

    except Exception as e:
        print(f"   ❌ Error testing CertificateManager: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Build acme command
    print("\n4. Testing acme.sh command building")
    try:
        cmd = cm._build_acme_command(
            domain="example.com",
            wildcard_domain="*.example.com",
            email="admin@example.com",
            dns_provider="cloudflare",
            staging=False
        )

        print(f"   ✅ Command built successfully")
        print(f"   Command: {' '.join(cmd[:3])}... (truncated)")
        print(f"   First element (acme.sh path): {cmd[0]}")

        # Verify first element is the correct path
        if cmd[0] == str(acme_sh_path):
            print(f"   ✅ Command uses correct acme.sh path")
        else:
            print(f"   ❌ Command path mismatch: {cmd[0]} != {acme_sh_path}")
            return False

    except Exception as e:
        print(f"   ❌ Error building command: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True

def test_acme_environment():
    """Test acme.sh environment setup"""
    print("\n" + "=" * 60)
    print("Checking acme.sh Environment")
    print("=" * 60)

    acme_dir = Path.home() / '.acme.sh'

    print(f"\n📁 acme.sh directory: {acme_dir}")
    if acme_dir.exists():
        print("   ✅ Directory exists")

        # List key files
        key_files = ['acme.sh', 'acme.sh.env', 'account.conf']
        print("\n   Key files:")
        for filename in key_files:
            filepath = acme_dir / filename
            if filepath.exists():
                print(f"      ✅ {filename}")
            else:
                print(f"      ❌ {filename} (missing)")

        # Check DNS API plugins
        dnsapi_dir = acme_dir / 'dnsapi'
        if dnsapi_dir.exists():
            dns_plugins = list(dnsapi_dir.glob('dns_*.sh'))
            print(f"\n   📦 DNS API plugins: {len(dns_plugins)} found")
            print(f"      Examples: {', '.join([p.stem for p in dns_plugins[:5]])}")

    else:
        print("   ❌ Directory not found")
        print("\n   To install acme.sh, run:")
        print("   curl https://get.acme.sh | sh")

if __name__ == '__main__':
    print("\n🔍 acme.sh Detection Test Suite\n")

    # Run environment check
    test_acme_environment()

    print("\n")

    # Run main tests
    success = test_acme_path()

    sys.exit(0 if success else 1)
