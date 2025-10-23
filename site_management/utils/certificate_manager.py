#!/usr/bin/env python3
"""
Certificate Management Utilities for Caddy WAF System
Provides comprehensive certificate validation, monitoring, and management
Refactored to use modular certificate utilities for better reusability
"""
import argparse
import sys
import os
import shutil
import tarfile
import subprocess
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Add the parent directory to the path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "site_management"))

try:
    from site_management.caddy_logger import caddy_logger
    from .certificate_checker import CertificateChecker
    from .certificate_operations import OpenSSLNotAvailableError
    from .acme_dns_manager import ACMEDNSManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)


class CertificateManager:
    """Comprehensive certificate management for Caddy WAF system using modular utilities"""

    def __init__(self, certs_dir: str = "/etc/caddy/certs", caddy_base_path: str = "/etc/caddy"):
        try:
            self.checker = CertificateChecker()
        except OpenSSLNotAvailableError:
            print("❌ OpenSSL not available on system")
            sys.exit(1)

        self.certs_dir = Path(certs_dir)
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.logger = caddy_logger
        self.caddy_base_path = Path(caddy_base_path)
        self.acme_manager = ACMEDNSManager()

    def check_certificate(self, cert_path: str, detailed: bool = False) -> bool:
        """Check certificate details and validity using modular utilities"""
        try:
            print(f"🔍 Checking certificate: {cert_path}")

            if not Path(cert_path).exists():
                print(f"❌ Certificate file not found: {cert_path}")
                return False

            # Get comprehensive certificate information using modular checker
            cert_info = self.checker.check_certificate_domains(cert_path)

            if "error" in cert_info:
                print(f"❌ Certificate error: {cert_info['error']}")
                return False

            # Use formatter for consistent output
            formatted_info = self.checker.format_certificate_info(cert_info, detailed)
            print(formatted_info)

            return True

        except Exception as e:
            print(f"❌ Error checking certificate: {e}")
            return False

    def check_domain_coverage(self, domain: str, cert_path: str) -> bool:
        """Check if a domain is covered by a certificate using modular utilities"""
        try:
            print(f"🔍 Checking if '{domain}' is covered by certificate...")

            # Use modular checker for domain coverage
            result = self.checker.check_domain_coverage(domain, cert_path)

            # Use formatter for consistent output
            formatted_result = self.checker.format_domain_coverage_result(result)
            print(formatted_result)

            if result.get("matches"):
                # Show additional certificate info
                if "cert_info" in result:
                    cert_info = result["cert_info"]
                    expires = cert_info.get("expires", "Unknown")
                    print(f"   Certificate expires: {expires}")

                return True
            else:
                # Show what domains are covered
                if "cert_info" in result:
                    cert_info = result["cert_info"]
                    print("   Certificate covers:")
                    if cert_info.get("common_name"):
                        print(f"     - {cert_info['common_name']} (CN)")
                    for san in cert_info.get("san_domains", []):
                        print(f"     - {san} (SAN)")
                    for wildcard in cert_info.get("wildcard_domains", []):
                        print(f"     - {wildcard} (Wildcard)")

                return False

        except Exception as e:
            print(f"❌ Error checking domain coverage: {e}")
            return False

    def validate_certificate_chain(self, cert_path: str, key_path: Optional[str] = None) -> bool:
        """Validate certificate and optionally check key match using modular utilities"""
        try:
            print(f"🔍 Validating certificate chain: {cert_path}")

            # Use modular validation
            cert_valid, cert_message, cert_details = self.checker.validate_certificate(cert_path)

            if not cert_valid:
                print(f"❌ Certificate validation failed: {cert_message}")
                return False

            print("✅ Certificate is valid")

            # Show certificate details using formatter
            if cert_details.get("common_name"):
                print(f"   Common Name: {cert_details['common_name']}")
            if cert_details.get("issuer"):
                print(f"   Issuer: {cert_details['issuer']}")
            if cert_details.get("expires"):
                print(f"   Expires: {cert_details['expires']}")

            # Validate private key if provided
            if key_path:
                print(f"🔍 Validating private key: {key_path}")

                key_valid, key_message, key_details = self.checker.validate_private_key(key_path)
                if not key_valid:
                    print(f"❌ Private key validation failed: {key_message}")
                    return False

                print("✅ Private key is valid")

                # Check if certificate and key match
                print("🔍 Checking certificate-key match...")
                match_valid, match_message = self.checker.validate_certificate_key_match(cert_path, key_path)

                if not match_valid:
                    print(f"❌ Certificate and key do not match: {match_message}")
                    return False

                print("✅ Certificate and key match")

            return True

        except Exception as e:
            print(f"❌ Error validating certificate chain: {e}")
            return False

    def check_chain(self, cert_path: str, chain_path: Optional[str] = None, ca_bundle_path: Optional[str] = None) -> bool:
        """Check and validate SSL certificate chain using modular utilities"""
        try:
            print(f"🔗 Checking SSL certificate chain: {cert_path}")

            # Validate the full certificate chain
            chain_valid, chain_message, chain_details = self.checker.validate_certificate_chain(
                cert_path, chain_path, ca_bundle_path
            )

            if not chain_valid:
                print(f"❌ Certificate chain validation failed: {chain_message}")
                if chain_details.get("verification_error"):
                    print(f"   Error: {chain_details['verification_error']}")
                return False

            print(f"✅ {chain_message}")

            # Display chain analysis
            chain_analysis = self.checker.analyze_certificate_chain(cert_path, chain_path)
            formatted_analysis = self.checker.format_chain_analysis(chain_analysis)
            print(formatted_analysis)

            # Show verification output if available
            if chain_details.get("verification_output"):
                print(f"\n📋 Verification Output:")
                print(f"   {chain_details['verification_output']}")

            return True

        except Exception as e:
            print(f"❌ Error checking certificate chain: {e}")
            return False

    def check_remote_certificate_info(self, hostname: str, port: int = 443) -> bool:
        """Check remote certificate using modular utilities"""
        try:
            print(f"🌐 Checking remote certificate for {hostname}:{port}")

            # Use modular checker for remote certificate
            remote_info = self.checker.check_remote_certificate(hostname, port)

            # Use formatter for consistent output
            formatted_info = self.checker.format_remote_certificate_info(remote_info)
            print(formatted_info)

            return "error" not in remote_info

        except Exception as e:
            print(f"❌ Error checking remote certificate: {e}")
            return False

    def scan_all_certificates(self, show_expired: bool = False, days_warning: int = 30) -> bool:
        """Scan all certificates in the certs directory using modular utilities"""
        try:
            print("🔍 Scanning all certificates...")

            scan_results = []
            cert_files = []

            # Find all certificate files
            for cert_file in self.certs_dir.rglob("*.pem"):
                if cert_file.is_file():
                    cert_files.append(cert_file)

            if not cert_files:
                print("ℹ️  No certificate files found")
                return True

            print(f"📊 Found {len(cert_files)} certificate files")

            # Check each certificate
            for cert_file in cert_files:
                try:
                    cert_info = self.checker.check_certificate_domains(str(cert_file))
                    cert_info["path"] = str(cert_file)
                    scan_results.append(cert_info)
                except Exception as e:
                    scan_results.append({
                        "path": str(cert_file),
                        "error": str(e)
                    })

            # Use formatter for consistent output
            formatted_results = self.checker.formatter.format_scan_results(scan_results)
            print(formatted_results)

            # Show specific warnings
            if show_expired:
                expired_count = sum(1 for r in scan_results if r.get("is_expired"))
                if expired_count > 0:
                    print(f"\n⚠️  Found {expired_count} expired certificates")

            expiring_soon = [r for r in scan_results if r.get("days_until_expiry", 999) <= days_warning and not r.get("is_expired")]
            if expiring_soon:
                print(f"\n⚠️  Found {len(expiring_soon)} certificates expiring within {days_warning} days")

            return True

        except Exception as e:
            print(f"❌ Error scanning certificates: {e}")
            return False

    def install_certificate(self, domain: str, cert_path: str, key_path: str,
                          chain_path: Optional[str] = None, force: bool = False) -> bool:
        """Install certificate for a domain using modular utilities"""
        try:
            print(f"📦 Installing certificate for domain: {domain}")

            # Validate certificate using modular checker
            cert_valid, cert_message, cert_details = self.checker.validate_certificate(cert_path)
            if not cert_valid:
                print(f"❌ Certificate validation failed: {cert_message}")
                return False

            # Check domain coverage
            coverage_result = self.checker.check_domain_coverage(domain, cert_path)
            if not coverage_result.get("matches") and not force:
                print(f"❌ Certificate does not cover domain '{domain}'")
                print("   Use --force to install anyway")
                return False

            # Validate private key
            key_valid, key_message, key_details = self.checker.validate_private_key(key_path)
            if not key_valid:
                print(f"❌ Private key validation failed: {key_message}")
                return False

            # Check certificate-key match
            match_valid, match_message = self.checker.validate_certificate_key_match(cert_path, key_path)
            if not match_valid:
                print(f"❌ Certificate and key do not match: {match_message}")
                return False

            # Create domain directory
            domain_dir = self.certs_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # Copy certificate files
            shutil.copy2(cert_path, domain_dir / "cert.pem")
            shutil.copy2(key_path, domain_dir / "key.pem")

            if chain_path and Path(chain_path).exists():
                shutil.copy2(chain_path, domain_dir / "chain.pem")

            print(f"✅ Certificate installed successfully for {domain}")
            print(f"   Certificate: {domain_dir / 'cert.pem'}")
            print(f"   Private Key: {domain_dir / 'key.pem'}")
            if chain_path:
                print(f"   Chain: {domain_dir / 'chain.pem'}")

            # Log the operation
            if self.logger:
                self.logger.log_certificate_operation(
                    domain, "install", cert_details, True
                )

            return True

        except Exception as e:
            print(f"❌ Error installing certificate: {e}")
            return False

    def generate_wildcard_certificate_acme(self, domain: str, email: str,
                                         dns_provider: str = "manual",
                                         staging: bool = False,
                                         force_renew: bool = False) -> dict:
        """
        Generate wildcard certificate using acme.sh for a domain with manual DNS validation
        User will need to manually add TXT records to their DNS provider
        Uses modular utilities for validation and verification
        """
        try:
            print(f"🔐 Generating wildcard certificate for domain: {domain}")
            print("ℹ️  This process requires manual DNS TXT record creation")

            # Check if acme.sh is available
            if not self._check_acme_sh_available():
                return {
                    "error": "acme.sh is not installed or not available in PATH"
                }

            # Prepare domain for wildcard certificate
            wildcard_domain = f"*.{domain}"

            # Create domain directory in our certs structure
            domain_dir = self.certs_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # Check if certificate already exists and is valid using modular checker
            if not force_renew and self._check_existing_wildcard_cert(domain):
                print(f"✅ Valid wildcard certificate already exists for {domain}")
                return True

            # Build acme.sh command for manual DNS validation
            acme_cmd = self._build_acme_command(
                domain, wildcard_domain, email, dns_provider, staging
            )

            print("🔄 Running acme.sh command...")
            print("   This will generate DNS TXT records that you need to add manually")
            print(f"   Command: {' '.join(acme_cmd[:5])}...")  # Show partial command for security

            # Execute acme.sh command interactively for manual DNS
            # Note: manual DNS mode requires user interaction
            result = subprocess.run(
                acme_cmd,
                text=True,
                timeout=600  # 10 minute timeout for manual process
            )

            if result.returncode != 0:
                return {
                    "error": f"acme.sh failed with exit code {result.returncode}"
                    }

            print("✅ acme.sh certificate generation completed")

            # Copy certificates from acme.sh to our structure
            if self._copy_acme_certificates_to_domain_dir(domain, domain_dir):
                print(f"✅ Wildcard certificate installed successfully for {domain}")

                # Verify the installed certificate using modular checker
                cert_path = domain_dir / "cert.pem"
                key_path = domain_dir / "key.pem"

                if self._verify_wildcard_certificate(str(cert_path), domain):
                    print("✅ Certificate verification passed")

                    # Update Caddyfile with new certificate
                    caddy_update_result = self._update_caddyfile_with_certificate(
                        domain, str(cert_path), str(key_path)
                    )

                    if caddy_update_result.get("success"):
                        print("✅ Caddyfile updated successfully")
                    else:
                        print(f"⚠️  Warning: Failed to update Caddyfile: {caddy_update_result.get('error')}")

                    # Log the operation
                    if self.logger:
                        cert_info = self.checker.check_certificate_domains(str(cert_path))
                        self.logger.log_certificate_operation(
                            domain, "generate_wildcard_acme", cert_info, True
                        )

                    return {
                        "success": True,
                        "cert_path": str(cert_path),
                        "key_path": str(key_path),
                        "caddy_updated": caddy_update_result.get("success", False)
                    }
                else:
                    return {
                    "error": "Certificate verification failed after installation"
                    }
            else:
                return {
                    "error": "Failed to copy certificates from acme.sh"
                }

        except subprocess.TimeoutExpired:
            return {
                "error": "acme.sh command timed out. Please try again."
            }
        except Exception as e:
            return {
                "error": f"Error generating wildcard certificate: {e}"
            }

    def get_dns_txt_records_for_verification(self, domain: str, email: str,
                                             staging: bool = False) -> Dict:
        """
        Get DNS TXT records from acme.sh without completing the challenge
        This extracts the TXT records that user needs to add to their DNS

        Returns:
            Dict with:
            - success: bool
            - txt_records: List[Dict] with record_name and record_value
            - instructions: str with formatted instructions
            - error: str if failed
        """
        try:
            print(f"🔍 Getting DNS TXT records for {domain}...")

            # Check if acme.sh is available
            if not self._check_acme_sh_available():
                return {
                    "success": False,
                    "error": "acme.sh is not installed. Please install it first:\n  curl https://get.acme.sh | sh"
                }

            wildcard_domain = f"*.{domain}"
            acme_sh_path = str(Path.home() / '.acme.sh' / 'acme.sh')

            # Build acme.sh command to get DNS records
            acme_cmd = [
                acme_sh_path, '--issue',
                '--dns', 'dns_manual',
                '-d', domain,
                '-d', wildcard_domain,
                '--email', email,
                '--keylength', '2048',
                '--server', 'letsencrypt',
                '--yes-I-know-dns-manual-mode-enough-go-ahead-please'
            ]

            if staging:
                acme_cmd.append('--staging')

            print("🔄 Running acme.sh to get TXT records...")

            # Run acme.sh with timeout, send 'n' to decline verification immediately
            # This way we get the TXT records but don't complete the challenge
            result = subprocess.run(
                acme_cmd,
                input='n\n',  # Send 'n' to decline proceeding
                capture_output=True,
                text=True,
                timeout=60
            )

            # Extract TXT records from output
            txt_records = self._extract_txt_records_from_acme_output(result.stdout)

            if not txt_records:
                return {
                    "success": False,
                    "error": "Could not extract TXT records from acme.sh output. Output:\n" + result.stdout
                }

            # Generate formatted instructions
            instructions = self._format_dns_instructions(domain, txt_records)

            return {
                "success": True,
                "txt_records": txt_records,
                "instructions": instructions,
                "domain": domain,
                "wildcard_domain": wildcard_domain
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Failed to get TXT records (timeout)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting DNS TXT records: {str(e)}"
            }

    def verify_dns_challenge_and_generate_cert(self, domain: str, email: str,
                                               txt_records: List[Dict] = None,
                                               staging: bool = False) -> Dict:
        """
        Web-based certificate generation with DNS verification

        This method is for WEB INTERFACE use:
        1. Verify DNS TXT records exist with correct values
        2. If verified, generate certificate with acme.sh
        3. Install certificate to domain directory
        4. Update Caddyfile with new certificate
        5. Return results

        Args:
            domain: Base domain (e.g., example.com)
            email: Email for Let's Encrypt registration
            txt_records: List of TXT records to verify [{"name": "...", "value": "..."}]
            staging: Use staging environment
        """
        try:
            print(f"🔍 Verifying DNS challenges for {domain}...")

            # If txt_records not provided, get them first
            if not txt_records:
                records_result = self.get_dns_txt_records_for_verification(domain, email, staging)
                if not records_result.get('success'):
                    return records_result
                txt_records = records_result.get('txt_records', [])

            # Step 1: Verify all DNS records
            verification_failed = False
            verification_details = []

            for record in txt_records:
                record_name = record.get('name', '')
                record_value = record.get('value', '')

                # Extract just the subdomain part for verification
                # _acme-challenge.example.com -> check _acme-challenge.example.com
                verification_result = self.acme_manager.verify_dns_challenge_record(
                    domain=domain,
                    expected_value=record_value
                )

                verification_details.append({
                    "record_name": record_name,
                    "record_value": record_value,
                    "exists": verification_result.get('exists'),
                    "matched": verification_result.get('matched'),
                    "found_value": verification_result.get('found_value')
                })

                if not verification_result.get('exists'):
                    verification_failed = True
                    print(f"❌ DNS TXT record not found: {record_name}")
                elif not verification_result.get('matched'):
                    verification_failed = True
                    print(f"❌ DNS TXT record value mismatch for: {record_name}")
                else:
                    print(f"✅ DNS TXT record verified: {record_name}")

            if verification_failed:
                return {
                    "success": False,
                    "error": "DNS TXT record verification failed. Please ensure all records are added correctly and DNS has propagated.",
                    "verification_details": verification_details
                }

            print("✅ All DNS challenges verified successfully!")

            # Step 2: Generate certificate using acme.sh
            print(f"🔐 Generating wildcard certificate for {domain}...")

            wildcard_domain = f"*.{domain}"
            domain_dir = self.certs_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            acme_sh_path = str(Path.home() / '.acme.sh' / 'acme.sh')

            acme_cmd = [
                acme_sh_path, '--issue',
                '--dns', 'dns_manual',
                '-d', domain,
                '-d', wildcard_domain,
                '--email', email,
                '--keylength', '2048',
                '--server', 'letsencrypt',
                '--yes-I-know-dns-manual-mode-enough-go-ahead-please'
            ]

            if staging:
                acme_cmd.append('--staging')

            print("🔄 Running acme.sh to generate certificate...")
            # Send 'y' to proceed with verification
            result = subprocess.run(
                acme_cmd,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                # Check if certificate already exists
                if "Domains not changed" in result.stdout or "cert already exists" in result.stdout.lower():
                    print("ℹ️  Certificate already exists, using existing certificate")
                else:
                    return {
                        "success": False,
                        "error": f"acme.sh failed: {result.stderr or result.stdout}",
                        "verification_details": verification_details
                    }

            print("✅ acme.sh completed successfully!")

            # Step 3: Copy certificates to domain directory
            if not self._copy_acme_certificates_to_domain_dir(domain, domain_dir):
                return {
                    "success": False,
                    "error": "Failed to copy certificates from acme.sh directory",
                    "verification_details": verification_details
                }

            cert_path = domain_dir / "cert.pem"
            key_path = domain_dir / "key.pem"

            # Step 4: Verify installed certificate
            print(f"🔍 Verifying certificate...")
            if not self._verify_wildcard_certificate(str(cert_path), domain):
                return {
                    "success": False,
                    "error": "Certificate verification failed after installation",
                    "verification_details": verification_details
                }

            print("✅ Certificate verification passed!")

            # Step 5: Update Caddyfile
            print("📝 Updating Caddyfile configuration...")
            caddy_result = self._update_caddyfile_with_certificate(
                domain, str(cert_path), str(key_path)
            )

            # Log the operation
            if self.logger:
                cert_info = self.checker.check_certificate_domains(str(cert_path))
                self.logger.log_certificate_operation(
                    domain, "generate_wildcard_web", cert_info, True
                )

            return {
                "success": True,
                "cert_path": str(cert_path),
                "key_path": str(key_path),
                "verification_details": verification_details,
                "caddy_updated": caddy_result.get("success", False),
                "caddy_message": caddy_result.get("message", ""),
                "message": f"Wildcard certificate successfully generated for {domain} and *.{domain}"
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Certificate generation timed out. Please try again."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error during certificate generation: {str(e)}"
            }

    def generate_wildcard_cert_interactive(self, domain: str, email: str,
                                          staging: bool = False) -> Dict:
        """
        Generate wildcard certificate using acme.sh dns_manual interactive mode

        This method is for CLI/COMMAND LINE use:
        This runs acme.sh which will:
        1. Display the TXT records that need to be added
        2. Wait for user to press Enter after adding records
        3. Verify DNS records
        4. Generate certificate
        5. Install certificate to domain directory
        6. Update Caddyfile

        This method is designed to be called from CLI and will interact with user directly
        """
        try:
            print(f"🔐 Generating wildcard certificate for {domain}")
            print(f"📧 Using email: {email}")
            print()

            # Check if acme.sh is available
            if not self._check_acme_sh_available():
                return {
                    "success": False,
                    "error": "acme.sh is not installed. Please install it first:\n  curl https://get.acme.sh | sh"
                }

            wildcard_domain = f"*.{domain}"
            domain_dir = self.certs_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # Build acme.sh command for interactive dns_manual mode
            acme_sh_path = str(Path.home() / '.acme.sh' / 'acme.sh')

            acme_cmd = [
                acme_sh_path, '--issue',
                '--dns', 'dns_manual',
                '-d', domain,
                '-d', wildcard_domain,
                '--email', email,
                '--keylength', '2048',
                '--server', 'letsencrypt',
                '--yes-I-know-dns-manual-mode-enough-go-ahead-please'
            ]

            if staging:
                acme_cmd.append('--staging')
                print("⚠️  Using Let's Encrypt STAGING environment (for testing)")
                print()

            print("=" * 70)
            print("🔄 Starting acme.sh certificate generation process...")
            print("=" * 70)
            print()
            print("📝 acme.sh will now:")
            print("   1. Show you the TXT records to add to your DNS")
            print("   2. Wait for you to add them")
            print("   3. Ask you to press Enter when ready")
            print("   4. Verify the DNS records")
            print("   5. Generate the certificate")
            print()
            print("⏳ Please wait for acme.sh instructions...")
            print("=" * 70)
            print()

            # Run acme.sh interactively (user will see output and interact with it)
            result = subprocess.run(
                acme_cmd,
                text=True,
                stdin=None,  # Use terminal stdin for user interaction
                timeout=600  # 10 minute timeout
            )

            print()
            print("=" * 70)

            if result.returncode != 0:
                # Check if certificate already exists
                print("❌ acme.sh command failed")
                return {
                    "success": False,
                    "error": "Certificate generation failed. Please check the output above."
                }

            print("✅ acme.sh completed successfully!")
            print("=" * 70)
            print()

            # Copy certificates to domain directory
            print(f"📦 Installing certificate to {domain_dir}...")
            if not self._copy_acme_certificates_to_domain_dir(domain, domain_dir):
                return {
                    "success": False,
                    "error": "Failed to copy certificates from acme.sh directory"
                }

            cert_path = domain_dir / "cert.pem"
            key_path = domain_dir / "key.pem"

            # Verify installed certificate
            print(f"🔍 Verifying certificate...")
            if not self._verify_wildcard_certificate(str(cert_path), domain):
                return {
                    "success": False,
                    "error": "Certificate verification failed after installation"
                }

            print("✅ Certificate verification passed!")
            print()

            # Update Caddyfile
            print("📝 Updating Caddyfile configuration...")
            caddy_result = self._update_caddyfile_with_certificate(
                domain, str(cert_path), str(key_path)
            )

            if caddy_result.get("success"):
                print(f"✅ Caddyfile updated: {caddy_result.get('config_path')}")
                print("✅ Caddy reloaded successfully")
            else:
                print(f"⚠️  Warning: {caddy_result.get('error')}")
                print("   You may need to manually update Caddyfile and reload Caddy")

            # Log the operation
            if self.logger:
                cert_info = self.checker.check_certificate_domains(str(cert_path))
                self.logger.log_certificate_operation(
                    domain, "generate_wildcard_interactive", cert_info, True
                )

            print()
            print("=" * 70)
            print("🎉 SUCCESS! Wildcard certificate generated and installed!")
            print("=" * 70)
            print(f"📄 Certificate: {cert_path}")
            print(f"🔑 Private Key: {key_path}")
            print(f"🌐 Covers: {domain} and *.{domain}")
            print("=" * 70)
            print()

            return {
                "success": True,
                "cert_path": str(cert_path),
                "key_path": str(key_path),
                "domain": domain,
                "caddy_updated": caddy_result.get("success", False),
                "message": f"Wildcard certificate successfully generated for {domain} and *.{domain}"
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Certificate generation timed out after 10 minutes. Please try again."
            }
        except KeyboardInterrupt:
            print("\n\n⚠️  Certificate generation cancelled by user")
            return {
                "success": False,
                "error": "Certificate generation cancelled by user"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error during certificate generation: {str(e)}"
            }

    def backup_certificates(self, backup_path: str) -> bool:
        """Backup all certificates to a tar.gz file"""
        try:
            print(f"💾 Creating backup of certificates...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_path}/caddy_certs_backup_{timestamp}.tar.gz"

            # Create backup directory
            Path(backup_path).mkdir(parents=True, exist_ok=True)

            with tarfile.open(backup_file, 'w:gz') as tar:
                tar.add(self.certs_dir, arcname='certificates')

            print(f"✅ Backup created: {backup_file}")
            return True

        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False

    # Helper methods
    def _check_acme_sh_available(self) -> bool:
        """Check if acme.sh is available on the system"""
        try:
            acme_sh_path = Path.home() / '.acme.sh' / 'acme.sh'
            if not acme_sh_path.exists():
                return False
            result = subprocess.run([str(acme_sh_path), '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_existing_wildcard_cert(self, domain: str) -> bool:
        """Check if a valid wildcard certificate already exists for the domain"""
        try:
            cert_path = self.certs_dir / domain / "cert.pem"
            if not cert_path.exists():
                return False

            # Use modular checker to validate existing certificate
            cert_info = self.checker.check_certificate_domains(str(cert_path))
            if "error" in cert_info:
                return False

            # Check if it's expired
            if cert_info.get("is_expired"):
                return False

            # Check if it covers the domain and wildcard
            domain_coverage = self.checker.check_domain_coverage(domain, str(cert_path))
            wildcard_coverage = self.checker.check_domain_coverage(f"*.{domain}", str(cert_path))

            return domain_coverage.get("matches") and wildcard_coverage.get("matches")

        except Exception:
            return False

    def _build_acme_command(self, domain: str, wildcard_domain: str, email: str,
                          dns_provider: str, staging: bool) -> List[str]:
        """Build acme.sh command for wildcard certificate generation"""
        acme_sh_path = str(Path.home() / '.acme.sh' / 'acme.sh')
        cmd = [acme_sh_path, '--issue', '--dns', 'dns_manual']

        if staging:
            cmd.append('--staging')

        cmd.extend([
            '-d', domain,
            '-d', wildcard_domain,
            '--email', email,
            '--keylength', '2048',
            '--server', 'letsencrypt',
            '--yes-I-know-dns-manual-mode-enough-go-ahead-please'
        ])

        return cmd

    def _copy_acme_certificates_to_domain_dir(self, domain: str, domain_dir: Path) -> bool:
        """Copy certificates from acme.sh to our domain directory structure"""
        try:
            # acme.sh stores certificates in ~/.acme.sh/domain/
            acme_dir = Path.home() / '.acme.sh' / domain

            if not acme_dir.exists():
                print(f"❌ acme.sh certificate directory not found: {acme_dir}")
                return False

            # Copy certificate files
            cert_files = {
                'fullchain.cer': 'cert.pem',
                'domain.key': 'key.pem',
                'ca.cer': 'chain.pem'
            }

            for acme_file, target_file in cert_files.items():
                source = acme_dir / acme_file
                target = domain_dir / target_file

                if source.exists():
                    shutil.copy2(source, target)
                    print(f"   Copied {acme_file} -> {target_file}")
                else:
                    print(f"   ⚠️  {acme_file} not found in acme.sh directory")

            return True

        except Exception as e:
            print(f"❌ Error copying certificates: {e}")
            return False

    def _verify_wildcard_certificate(self, cert_path: str, domain: str) -> bool:
        """Verify that the generated wildcard certificate is valid and covers the domain"""
        try:
            # Use modular checker to verify certificate
            cert_info = self.checker.check_certificate_domains(cert_path)
            if "error" in cert_info:
                print(f"   ❌ Certificate verification failed: {cert_info['error']}")
                return False

            # Check domain coverage
            domain_coverage = self.checker.check_domain_coverage(domain, cert_path)
            wildcard_coverage = self.checker.check_domain_coverage(f"*.{domain}", cert_path)

            if not domain_coverage.get("matches"):
                print(f"   ❌ Certificate does not cover domain: {domain}")
                return False

            if not wildcard_coverage.get("matches"):
                print(f"   ❌ Certificate does not cover wildcard: *.{domain}")
                return False

            print(f"   ✅ Certificate covers both {domain} and *.{domain}")
            return True

        except Exception as e:
            print(f"   ❌ Certificate verification error: {e}")
            return False

    def _extract_txt_records_from_acme_output(self, output: str) -> List[Dict]:
        """
        Extract TXT record information from acme.sh output

        acme.sh output looks like:
        Add the following TXT record:
        Domain: '_acme-challenge.example.com'
        TXT value: 'xxxxxxxxxxxxxxxxxxxxxx'
        """
        txt_records = []
        lines = output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for domain line
            if "Domain:" in line and "_acme-challenge" in line:
                # Extract domain name
                domain_match = re.search(r"Domain:\s*'?([^'\"]+)'?", line)
                if domain_match:
                    domain_name = domain_match.group(1).strip()

                    # Look for TXT value in next few lines
                    for j in range(i+1, min(i+5, len(lines))):
                        value_line = lines[j].strip()
                        if "TXT value:" in value_line:
                            value_match = re.search(r"TXT value:\s*'?([^'\"]+)'?", value_line)
                            if value_match:
                                txt_value = value_match.group(1).strip()
                                txt_records.append({
                                    "name": domain_name,
                                    "value": txt_value
                                })
                                break
            i += 1

        return txt_records

    def _format_dns_instructions(self, domain: str, txt_records: List[Dict]) -> str:
        """Format DNS instructions for display to user"""
        instructions = f"""
DNS TXT Records Required for {domain}
{'=' * 70}

Please add the following TXT record(s) to your DNS provider:
"""
        for idx, record in enumerate(txt_records, 1):
            instructions += f"""
Record #{idx}:
  Name/Host: {record['name']}
  Type: TXT
  Value: {record['value']}
  TTL: 300 (or Auto)
"""

        instructions += f"""
{'=' * 70}

Instructions:
1. Log in to your DNS provider (Cloudflare, Route53, etc.)
2. Add the TXT record(s) shown above
3. Wait 5-10 minutes for DNS propagation
4. Click 'Verify DNS Records' button to continue

To check if DNS has propagated, run:
  dig TXT {txt_records[0]['name'] if txt_records else '_acme-challenge.' + domain}
"""
        return instructions

    def _update_caddyfile_with_certificate(self, domain: str, cert_path: str, key_path: str) -> Dict:
        """
        Update Caddyfile template or site-specific config with certificate paths
        This integrates the certificate into Caddy's configuration
        """
        try:
            # Path to site-specific Caddyfile
            sites_dir = self.caddy_base_path / "sites"
            sites_dir.mkdir(parents=True, exist_ok=True)
            site_caddyfile = sites_dir / f"{domain}.caddy"

            # Generate Caddyfile configuration
            config_content = self._generate_caddyfile_config(domain, cert_path, key_path)

            # Write configuration to file
            site_caddyfile.write_text(config_content)

            # Ensure main Caddyfile imports site configs
            self._ensure_site_import_in_main_caddyfile(sites_dir)

            # Reload Caddy to apply changes
            reload_result = self._reload_caddy_config()

            if reload_result.get("success"):
                print(f"✅ Caddyfile updated and Caddy reloaded for {domain}")
                return {
                    "success": True,
                    "message": f"Certificate configured for {domain}",
                    "config_path": str(site_caddyfile)
                }
            else:
                return {
                    "success": False,
                    "error": f"Caddyfile created but reload failed: {reload_result.get('error')}",
                    "config_path": str(site_caddyfile)
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update Caddyfile: {e}"
            }

    def _generate_caddyfile_config(self, domain: str, cert_path: str, key_path: str) -> str:
        """Generate Caddyfile configuration for a domain with custom certificates"""
        config = f"""# Caddy configuration for {domain}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{domain}, *.{domain} {{
    tls {cert_path} {key_path}

    # Reverse proxy to backend (customize as needed)
    reverse_proxy localhost:8000

    # Logging
    log {{
        output file /var/log/caddy/{domain}.log
        format json
    }}

    # Security headers
    header {{
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
    }}
}}
"""
        return config

    def _ensure_site_import_in_main_caddyfile(self, sites_dir: Path) -> bool:
        """Ensure main Caddyfile imports all site configurations"""
        try:
            main_caddyfile = self.caddy_base_path / "Caddyfile"

            # Import directive to add
            import_directive = f"import {sites_dir}/*.caddy"

            # Read existing Caddyfile or create new one
            if main_caddyfile.exists():
                content = main_caddyfile.read_text()

                # Check if import already exists
                if import_directive in content:
                    return True

                # Add import at the beginning
                content = f"{import_directive}\n\n{content}"
            else:
                # Create new Caddyfile with import
                content = f"""# Main Caddyfile
# Auto-generated by Certificate Manager

{import_directive}

# Global options
{{
    admin localhost:2019
    auto_https off
}}
"""

            main_caddyfile.write_text(content)
            print(f"✅ Updated main Caddyfile to import site configs")
            return True

        except Exception as e:
            print(f"⚠️  Failed to update main Caddyfile: {e}")
            return False

    def _reload_caddy_config(self) -> Dict:
        """Reload Caddy configuration using caddy reload command or API"""
        try:
            # Try using caddy reload command
            result = subprocess.run(
                ['caddy', 'reload', '--config', str(self.caddy_base_path / 'Caddyfile')],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Caddy reloaded successfully"
                }
            else:
                # Try using Caddy API as fallback
                try:
                    import requests
                    response = requests.post('http://localhost:2019/load', timeout=10)
                    if response.status_code == 200:
                        return {
                            "success": True,
                            "message": "Caddy reloaded via API"
                        }
                except:
                    pass

                return {
                    "success": False,
                    "error": f"Caddy reload failed: {result.stderr or result.stdout}"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Caddy reload timed out"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Caddy executable not found in PATH"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to reload Caddy: {e}"
            }


def main():
    """Main CLI interface for certificate management"""
    parser = argparse.ArgumentParser(
        description="Certificate Management for Caddy WAF System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            %(prog)s check /path/to/cert.pem                           # Check certificate
            %(prog)s check /path/to/cert.pem --detailed                # Detailed certificate info
            %(prog)s domain example.com /path/to/cert.pem              # Check domain coverage
            %(prog)s validate /path/to/cert.pem /path/to/key.pem       # Validate cert and key
            %(prog)s check-chain /path/to/cert.pem                     # Check certificate chain
            %(prog)s check-chain /path/to/cert.pem --chain chain.pem   # Check with intermediate chain
            %(prog)s check-chain /path/to/cert.pem --chain chain.pem --ca-bundle /etc/ssl/certs/ca-bundle.crt  # Verify against CA bundle
            %(prog)s remote example.com                                # Check remote certificate
            %(prog)s remote example.com --port 8443                    # Check remote cert on custom port
            %(prog)s scan                                              # Scan all certificates
            %(prog)s scan --show-expired --days-warning 7              # Show expired and warn 7 days early
            %(prog)s install example.com cert.pem key.pem              # Install certificate
            %(prog)s install example.com cert.pem key.pem --chain chain.pem --force  # Install with chain (forced)
            %(prog)s backup /path/to/backup                            # Backup all certificates
            %(prog)s acme-wildcard example.com admin@example.com       # Generate wildcard cert with acme.sh
            %(prog)s acme-wildcard example.com admin@example.com --dns-provider cloudflare --staging  # Use staging environment

            Wildcard Certificate Generation (Interactive Mode):
            The acme-wildcard command generates certificates that cover both the base domain
            and all its subdomains (*.domain.com) using acme.sh dns_manual interactive mode.

            The process will:
            1. Display TXT records that need to be added to your DNS
            2. Wait for you to add the records
            3. Ask you to press Enter when ready
            4. Verify DNS records and generate certificate
            5. Install certificate and update Caddyfile

            Prerequisites:
            - Install acme.sh: curl https://get.acme.sh | sh
            - Access to your DNS provider to add TXT records

            Examples:
                # Generate wildcard certificate (production)
                %(prog)s acme-wildcard example.com admin@example.com

                # Test with staging environment (recommended for first try)
                %(prog)s acme-wildcard example.com admin@example.com --staging
                    """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Check certificate
    check_parser = subparsers.add_parser('check', help='Check certificate details')
    check_parser.add_argument('cert_path', help='Path to certificate file')
    check_parser.add_argument('--detailed', action='store_true', help='Show detailed certificate information')

    # Check domain coverage
    domain_parser = subparsers.add_parser('domain', help='Check if domain is covered by certificate')
    domain_parser.add_argument('domain', help='Domain name to check')
    domain_parser.add_argument('cert_path', help='Path to certificate file')

    # Validate certificate and key
    validate_parser = subparsers.add_parser('validate', help='Validate certificate and key')
    validate_parser.add_argument('cert_path', help='Path to certificate file')
    validate_parser.add_argument('key_path', nargs='?', help='Path to private key file (optional)')

    # Check certificate chain
    chain_parser = subparsers.add_parser('check-chain', help='Check and validate SSL certificate chain')
    chain_parser.add_argument('cert_path', help='Path to certificate file')
    chain_parser.add_argument('--chain', help='Path to certificate chain file')
    chain_parser.add_argument('--ca-bundle', help='Path to CA bundle file for verification')

    # Check remote certificate
    remote_parser = subparsers.add_parser('remote', help='Check remote certificate')
    remote_parser.add_argument('domain', help='Domain name')
    remote_parser.add_argument('--port', type=int, default=443, help='Port number (default: 443)')

    # Scan all certificates
    scan_parser = subparsers.add_parser('scan', help='Scan all certificates')
    scan_parser.add_argument('--show-expired', action='store_true', help='Show expired certificates')
    scan_parser.add_argument('--days-warning', type=int, default=30, help='Days before expiry to warn (default: 30)')

    # Install certificate
    install_parser = subparsers.add_parser('install', help='Install certificate for domain')
    install_parser.add_argument('domain', help='Domain name')
    install_parser.add_argument('cert_path', help='Path to certificate file')
    install_parser.add_argument('key_path', help='Path to private key file')
    install_parser.add_argument('--chain', help='Path to certificate chain file')
    install_parser.add_argument('--force', action='store_true', help='Force installation even if certificate doesn\'t cover domain')

    # Backup certificates
    backup_parser = subparsers.add_parser('backup', help='Backup all certificates')
    backup_parser.add_argument('backup_path', help='Path to backup directory')

    # Generate wildcard certificate with acme.sh (interactive mode)
    acme_parser = subparsers.add_parser('acme-wildcard', help='Generate wildcard certificate using acme.sh (interactive DNS manual mode)')
    acme_parser.add_argument('domain', help='Base domain name (e.g., example.com)')
    acme_parser.add_argument('email', help='Email address for Let\'s Encrypt registration')
    acme_parser.add_argument('--staging', action='store_true', help='Use Let\'s Encrypt staging environment for testing')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize certificate manager
    try:
        cert_manager = CertificateManager()
    except Exception as e:
        print(f"❌ Failed to initialize certificate manager: {e}")
        return 1

    # Execute command
    success = False

    if args.command == 'check':
        success = cert_manager.check_certificate(args.cert_path, args.detailed)
    elif args.command == 'domain':
        success = cert_manager.check_domain_coverage(args.domain, args.cert_path)
    elif args.command == 'validate':
        success = cert_manager.validate_certificate_chain(args.cert_path, args.key_path)
    elif args.command == 'check-chain':
        success = cert_manager.check_chain(
            args.cert_path,
            getattr(args, 'chain', None),
            getattr(args, 'ca_bundle', None)
        )
    elif args.command == 'remote':
        success = cert_manager.check_remote_certificate_info(args.domain, args.port)
    elif args.command == 'scan':
        success = cert_manager.scan_all_certificates(args.show_expired, args.days_warning)
    elif args.command == 'install':
        success = cert_manager.install_certificate(
            args.domain, args.cert_path, args.key_path, args.chain, args.force
        )
    elif args.command == 'backup':
        success = cert_manager.backup_certificates(args.backup_path)
    elif args.command == 'acme-wildcard':
        result = cert_manager.generate_wildcard_cert_interactive(
            args.domain, args.email, args.staging
        )
        success = result.get('success', False)
        if not success and result.get('error'):
            print(f"\n❌ Error: {result['error']}")
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
