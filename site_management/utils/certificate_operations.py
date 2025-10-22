"""
Certificate Operations Module for Caddy WAF System
Provides core certificate operations, validation, and domain checking functionality
"""
import subprocess
import ssl
import socket
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import os


class CertificateError(Exception):
    """Base exception for certificate operations"""
    pass


class OpenSSLNotAvailableError(CertificateError):
    """Raised when OpenSSL is not available on the system"""
    pass


class CertificateOperations:
    """
    Core certificate operations and utilities
    Handles OpenSSL command execution, certificate parsing, and common validations
    """

    def __init__(self):
        self.openssl_available = self._check_openssl_availability()
        if not self.openssl_available:
            raise OpenSSLNotAvailableError("OpenSSL not available on system")

    def _check_openssl_availability(self) -> bool:
        """Check if OpenSSL is available in the system"""
        try:
            result = subprocess.run(['openssl', 'version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _run_openssl_command(self, command: List[str], timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Execute OpenSSL command and return success status, stdout, stderr

        Args:
            command: OpenSSL command as list of strings
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if not self.openssl_available:
                raise OpenSSLNotAvailableError("OpenSSL not available")

            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout
            )

            return result.returncode == 0, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Command timeout"
        except FileNotFoundError:
            return False, "", "OpenSSL not found"
        except Exception as e:
            return False, "", str(e)

    def _validate_file_exists(self, file_path: str, file_type: str = "file") -> bool:
        """Validate that a file exists and raise appropriate error if not"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"{file_type.capitalize()} file not found: {file_path}")
        return True

    def get_certificate_text_info(self, cert_path: str) -> Dict[str, Any]:
        """
        Get certificate text information using OpenSSL

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with certificate text info or error
        """
        self._validate_file_exists(cert_path, "certificate")

        success, stdout, stderr = self._run_openssl_command([
            'openssl', 'x509', '-in', cert_path, '-text', '-noout'
        ])

        if not success:
            return {"error": f"Invalid certificate: {stderr}"}

        return {"cert_text": stdout}

    def get_certificate_domains(self, cert_path: str) -> Dict[str, Any]:
        """
        Extract domains from certificate (CN and SAN)

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with domain information
        """
        cert_info_result = self.get_certificate_text_info(cert_path)

        if "error" in cert_info_result:
            return cert_info_result

        cert_text = cert_info_result["cert_text"]

        domains = {
            "common_name": None,
            "san_domains": [],
            "wildcard_domains": [],
            "all_domains": []
        }

        # Extract Common Name
        cn_match = re.search(r'Subject:.*?CN\s*=\s*([^,\n]+)', cert_text)
        if cn_match:
            cn = cn_match.group(1).strip()
            domains["common_name"] = cn
            domains["all_domains"].append(cn)

        # Extract Subject Alternative Names
        san_section = False
        for line in cert_text.split('\n'):
            line = line.strip()

            if 'X509v3 Subject Alternative Name:' in line:
                san_section = True
                continue

            if san_section:
                if line.startswith('DNS:') or 'DNS:' in line:
                    dns_entries = re.findall(r'DNS:([^,\s]+)', line)
                    for dns_entry in dns_entries:
                        dns_entry = dns_entry.strip()
                        if dns_entry.startswith('*.'):
                            domains["wildcard_domains"].append(dns_entry)
                        else:
                            domains["san_domains"].append(dns_entry)
                        domains["all_domains"].append(dns_entry)
                elif line and not line.startswith('DNS:') and not 'DNS:' in line:
                    break

        # Remove duplicates while preserving order
        domains["san_domains"] = list(dict.fromkeys(domains["san_domains"]))
        domains["wildcard_domains"] = list(dict.fromkeys(domains["wildcard_domains"]))
        domains["all_domains"] = list(dict.fromkeys(domains["all_domains"]))

        return domains

    def get_certificate_dates(self, cert_path: str) -> Dict[str, Any]:
        """
        Get certificate validity dates and expiration information

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with date information
        """
        self._validate_file_exists(cert_path, "certificate")

        # Get expiration date
        success, stdout, stderr = self._run_openssl_command([
            'openssl', 'x509', '-in', cert_path, '-enddate', '-noout'
        ])

        date_info = {}

        if success and stdout.strip().startswith('notAfter='):
            exp_date_str = stdout.strip().replace('notAfter=', '')
            date_info["expires"] = exp_date_str

            # Parse expiration date and check if expired
            exp_datetime = self._parse_openssl_date(exp_date_str)
            if exp_datetime:
                date_info["is_expired"] = exp_datetime < datetime.now()
                date_info["days_until_expiry"] = (exp_datetime - datetime.now()).days
                date_info["expiry_datetime"] = exp_datetime
            else:
                date_info["is_expired"] = None
                date_info["days_until_expiry"] = None

        # Get start date
        success, stdout, stderr = self._run_openssl_command([
            'openssl', 'x509', '-in', cert_path, '-startdate', '-noout'
        ])

        if success and stdout.strip().startswith('notBefore='):
            start_date_str = stdout.strip().replace('notBefore=', '')
            date_info["not_before"] = start_date_str

            start_datetime = self._parse_openssl_date(start_date_str)
            if start_datetime:
                date_info["start_datetime"] = start_datetime

        return date_info

    def get_certificate_metadata(self, cert_path: str) -> Dict[str, Any]:
        """
        Get certificate metadata (issuer, serial, etc.)

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with metadata
        """
        self._validate_file_exists(cert_path, "certificate")

        metadata = {}

        # Get issuer information
        success, stdout, stderr = self._run_openssl_command([
            'openssl', 'x509', '-in', cert_path, '-issuer', '-noout'
        ])

        if success and stdout.strip().startswith('issuer='):
            metadata["issuer"] = stdout.strip().replace('issuer=', '')

        # Get serial number
        success, stdout, stderr = self._run_openssl_command([
            'openssl', 'x509', '-in', cert_path, '-serial', '-noout'
        ])

        if success and stdout.strip().startswith('serial='):
            metadata["serial_number"] = stdout.strip().replace('serial=', '')

        # Get subject
        success, stdout, stderr = self._run_openssl_command([
            'openssl', 'x509', '-in', cert_path, '-subject', '-noout'
        ])

        if success and stdout.strip().startswith('subject='):
            metadata["subject"] = stdout.strip().replace('subject=', '')

        return metadata

    def get_certificate_fingerprint(self, cert_path: str, algorithm: str = "sha256") -> Optional[str]:
        """
        Get certificate fingerprint using specified algorithm

        Args:
            cert_path: Path to certificate file
            algorithm: Hash algorithm (sha1, sha256, md5, etc.)

        Returns:
            Fingerprint string or None if failed
        """
        try:
            self._validate_file_exists(cert_path, "certificate")

            success, stdout, stderr = self._run_openssl_command([
                'openssl', 'x509', '-in', cert_path, f'-{algorithm}', '-noout', '-fingerprint'
            ])

            if success and '=' in stdout:
                return stdout.strip().split('=', 1)[1]

        except Exception:
            pass

        return None

    def check_remote_certificate(self, hostname: str, port: int = 443, timeout: int = 10) -> Dict[str, Any]:
        """
        Check the certificate currently served by a remote host

        Args:
            hostname: Remote hostname
            port: Remote port (default 443)
            timeout: Connection timeout

        Returns:
            Dictionary with certificate information or error
        """
        try:
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Connect and get certificate
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

            # Parse certificate information
            subject = dict(x[0] for x in cert.get('subject', []))
            issuer = dict(x[0] for x in cert.get('issuer', []))

            # Extract SAN domains
            san_domains = []
            for san in cert.get('subjectAltName', []):
                if san[0] == 'DNS':
                    san_domains.append(san[1])

            # Parse dates
            not_before = cert.get('notBefore')
            not_after = cert.get('notAfter')

            # Calculate expiration
            days_until_expiry = None
            is_expired = None
            if not_after:
                try:
                    exp_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (exp_date - datetime.now()).days
                    is_expired = days_until_expiry < 0
                except ValueError:
                    pass

            return {
                "hostname": hostname,
                "port": port,
                "common_name": subject.get('commonName'),
                "organization": subject.get('organizationName'),
                "issuer_org": issuer.get('organizationName'),
                "issuer_cn": issuer.get('commonName'),
                "serial_number": cert.get('serialNumber'),
                "not_before": not_before,
                "not_after": not_after,
                "san_domains": san_domains,
                "days_until_expiry": days_until_expiry,
                "is_expired": is_expired,
                "version": cert.get('version'),
                "signature_algorithm": cert.get('signatureAlgorithm')
            }

        except socket.timeout:
            return {"error": f"Connection timeout to {hostname}:{port}"}
        except socket.gaierror as e:
            return {"error": f"DNS resolution failed for {hostname}: {e}"}
        except ssl.SSLError as e:
            return {"error": f"SSL error connecting to {hostname}:{port}: {e}"}
        except Exception as e:
            return {"error": f"Error checking remote certificate: {e}"}

    def matches_wildcard(self, domain: str, wildcard: str) -> bool:
        """
        Check if a domain matches a wildcard certificate

        Args:
            domain: Domain to check
            wildcard: Wildcard pattern

        Returns:
            True if domain matches wildcard
        """
        domain_lower = domain.lower()
        wildcard_lower = wildcard.lower()

        if not wildcard_lower.startswith('*.'):
            return domain_lower == wildcard_lower

        # Extract the base domain from wildcard (*.example.com -> example.com)
        wildcard_base = wildcard_lower[2:]

        # Exact match with base domain
        if domain_lower == wildcard_base:
            return True

        # Subdomain match
        if domain_lower.endswith(f'.{wildcard_base}'):
            # Ensure it's a direct subdomain (no nested subdomains for basic wildcard)
            subdomain_part = domain_lower[:-len(f'.{wildcard_base}')]
            return '.' not in subdomain_part

        return False

    def domain_matches_certificate(self, domain: str, cert_path: str) -> Dict[str, Any]:
        """
        Check if a domain is covered by a certificate

        Args:
            domain: Domain to check
            cert_path: Path to certificate file

        Returns:
            Dictionary with match information
        """
        try:
            # Get certificate domains
            domains_result = self.get_certificate_domains(cert_path)

            if "error" in domains_result:
                return {
                    "matches": False,
                    "reason": domains_result["error"],
                    "cert_info": domains_result
                }

            # Get certificate metadata for additional info
            metadata = self.get_certificate_metadata(cert_path)
            dates = self.get_certificate_dates(cert_path)

            # Combine all certificate info
            cert_info = {**domains_result, **metadata, **dates}

            domain_lower = domain.lower()

            # Check exact matches with Common Name
            if cert_info.get("common_name"):
                cn_lower = cert_info["common_name"].lower()
                if domain_lower == cn_lower:
                    return {
                        "matches": True,
                        "type": "common_name",
                        "matched_value": cert_info["common_name"],
                        "cert_info": cert_info
                    }

            # Check exact matches with SAN domains
            for san_domain in cert_info.get("san_domains", []):
                if domain_lower == san_domain.lower():
                    return {
                        "matches": True,
                        "type": "san",
                        "matched_value": san_domain,
                        "cert_info": cert_info
                    }

            # Check wildcard matches
            for wildcard in cert_info.get("wildcard_domains", []):
                if self.matches_wildcard(domain_lower, wildcard.lower()):
                    return {
                        "matches": True,
                        "type": "wildcard",
                        "matched_value": wildcard,
                        "cert_info": cert_info
                    }

            return {
                "matches": False,
                "reason": f"Domain '{domain}' not covered by certificate",
                "cert_info": cert_info
            }

        except Exception as e:
            return {
                "matches": False,
                "reason": f"Error checking domain coverage: {str(e)}",
                "cert_info": {}
            }

    def get_comprehensive_certificate_info(self, cert_path: str) -> Dict[str, Any]:
        """
        Get comprehensive certificate information combining all available data

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with all certificate information
        """
        try:
            # Get all certificate information
            domains = self.get_certificate_domains(cert_path)
            if "error" in domains:
                return domains

            dates = self.get_certificate_dates(cert_path)
            metadata = self.get_certificate_metadata(cert_path)

            # Get detailed certificate text info for additional parsing
            detailed_info = self._parse_certificate_details(cert_path)

            # Combine all information
            comprehensive_info = {
                **domains,
                **dates,
                **metadata,
                **detailed_info
            }

            return comprehensive_info

        except Exception as e:
            return {"error": f"Error getting comprehensive certificate info: {str(e)}"}

    def _parse_openssl_date(self, date_str: str) -> Optional[datetime]:
        """Parse OpenSSL date string to datetime object"""
        date_formats = [
            '%b %d %H:%M:%S %Y %Z',  # Standard format
            '%b %d %H:%M:%S %Y GMT', # GMT variant
            '%Y-%m-%d %H:%M:%S %Z'   # ISO format
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue

        return None

    def _parse_certificate_details(self, cert_path: str) -> Dict[str, Any]:
        """Parse detailed certificate information from OpenSSL text output"""
        details = {}

        try:
            cert_info_result = self.get_certificate_text_info(cert_path)
            if "error" in cert_info_result:
                return {}

            cert_text = cert_info_result["cert_text"]

            # Extract version
            version_match = re.search(r'Version:\s*(\d+)', cert_text)
            if version_match:
                details['version'] = int(version_match.group(1))

            # Extract signature algorithm
            sig_match = re.search(r'Signature Algorithm:\s*([^\n]+)', cert_text)
            if sig_match:
                details['signature_algorithm'] = sig_match.group(1).strip()

            # Extract public key info
            pub_key_match = re.search(r'Public Key Algorithm:\s*([^\n]+)', cert_text)
            if pub_key_match:
                details['public_key_algorithm'] = pub_key_match.group(1).strip()

            # Extract key size
            key_size_match = re.search(r'(?:RSA Public Key|Public-Key):\s*\((\d+)\s*bit\)', cert_text)
            if key_size_match:
                details['key_size'] = int(key_size_match.group(1))

        except Exception:
            pass

        return details

    def split_certificate_chain(self, chain_path: str) -> List[str]:
        """
        Split a chain file into individual certificate PEM blocks

        Args:
            chain_path: Path to certificate chain file

        Returns:
            List of individual certificate PEM strings
        """
        try:
            self._validate_file_exists(chain_path, "chain")

            with open(chain_path, 'r') as f:
                content = f.read()

            certificates = []
            cert_blocks = content.split('-----BEGIN CERTIFICATE-----')

            for block in cert_blocks[1:]:  # Skip first empty block
                if '-----END CERTIFICATE-----' in block:
                    cert_pem = '-----BEGIN CERTIFICATE-----' + block
                    certificates.append(cert_pem.strip())

            return certificates

        except Exception:
            return []

    def create_temporary_certificate(self, cert_pem: str) -> str:
        """
        Create a temporary certificate file from PEM string

        Args:
            cert_pem: Certificate PEM content

        Returns:
            Path to temporary certificate file
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as tmp_file:
            tmp_file.write(cert_pem)
            return tmp_file.name

    def cleanup_temporary_file(self, file_path: str) -> None:
        """Clean up temporary file"""
        try:
            os.unlink(file_path)
        except Exception:
            pass




