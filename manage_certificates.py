#!/usr/bin/env python3
"""
Certificate Management Wrapper Script
Provides easy access to certificate manager functionality with proper imports
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__fi- ✅ Production-ready examples
le__).parent
sys.path.insert(0, str(project_root))

# Set Django settings if needed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waf_app.settings')

# Import and run certificate manager
try:
    from site_mangement.utils.certificate_manager import main
    sys.exit(main())
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTroubleshooting:")
    print("1. Ensure you're in the project root directory")
    print("2. Check that all dependencies are installed:")
    print("   pip install -r requirements.txt")
    print("3. Verify OpenSSL is installed: openssl version")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
