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
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add the parent directory to the path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "site_management"))

try:
    from site_management.caddy_logger import caddy_logger
    from .certificate_checker import CertificateChecker
    from .certificate_operations import OpenSSLNotAvailableError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)


class CertificateManager:
    """Comprehensive certificate management for Caddy WAF system using modular utilities"""

    def __init__(self, certs_dir: str = "/etc/caddy/certs"):
        try:
            self.checker = CertificateChecker()
        except OpenSSLNotAvailableError:
            print("❌ OpenSSL not available on system")
            sys.exit(1)

        self.certs_dir = Path(certs_dir)
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.logger = caddy_logger

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
                if self._verify_wildcard_certificate(str(cert_path), domain):
                    print("✅ Certificate verification passed")

                    # Log the operation
                    if self.logger:
                        cert_info = self.checker.check_certificate_domains(str(cert_path))
                        self.logger.log_certificate_operation(
                            domain, "generate_wildcard_acme", cert_info, True
                        )

                    return {
                        "success": True,
                        "cert_path": str(cert_path),
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
            result = subprocess.run(['acme.sh', '--version'], capture_output=True, timeout=5)
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
        cmd = ['acme.sh', '--issue', '--dns', 'dns_manual']

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

            Wildcard Certificate Generation:
            The acme-wildcard command generates certificates that cover both the base domain
            and all its subdomains (*.domain.com). Requires acme.sh and DNS provider API access.

            Prerequisites:
            - Install acme.sh: curl https://get.acme.sh | sh
            - Configure DNS provider credentials (see acme.sh documentation)

            Examples:
                # Cloudflare (set CF_Token and CF_Account_ID environment variables)
                export CF_Token="your_cloudflare_api_token"
                export CF_Account_ID="your_cloudflare_account_id"
                %(prog)s acme-wildcard example.com admin@example.com --dns-provider cloudflare

                # Route53 (set AWS credentials)
                export AWS_ACCESS_KEY_ID="your_aws_key"
                export AWS_SECRET_ACCESS_KEY="your_aws_secret"
                %(prog)s acme-wildcard example.com admin@example.com --dns-provider route53
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

    # Generate wildcard certificate with acme.sh
    acme_parser = subparsers.add_parser('acme-wildcard', help='Generate wildcard certificate using acme.sh')
    acme_parser.add_argument('domain', help='Base domain name (e.g., example.com)')
    acme_parser.add_argument('email', help='Email address for Let\'s Encrypt registration')
    acme_parser.add_argument('--dns-provider', default='cloudflare', help='DNS provider for validation (default: cloudflare)')
    acme_parser.add_argument('--staging', action='store_true', help='Use Let\'s Encrypt staging environment for testing')
    acme_parser.add_argument('--force-renew', action='store_true', help='Force renewal even if certificate exists')

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
        success = cert_manager.generate_wildcard_certificate_acme(
            args.domain, args.email, args.dns_provider, args.staging, args.force_renew
        )
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
