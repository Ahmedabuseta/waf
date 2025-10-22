"""
Validators for Site model - SSL/TLS certificate and configuration validation
Ensures certificates are valid, match configuration, and support required features
"""
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from pathlib import Path
import tempfile
import os
from typing import Dict, Optional, Tuple, List
from .utils.certificate_checker import CertificateChecker


class SiteSSLValidator:
    """
    Comprehensive SSL/TLS validation for Site model
    Validates certificates, keys, chains, and domain coverage
    """

    def __init__(self):
        self.cert_checker = CertificateChecker()

    def validate_site_ssl_configuration(
        self,
        protocol: str,
        auto_ssl: bool,
        support_subdomains: bool,
        host: str,
        ssl_certificate: Optional[UploadedFile] = None,
        ssl_key: Optional[UploadedFile] = None,
        ssl_chain: Optional[UploadedFile] = None
        ) -> Tuple[bool, List[str]]:
        """
        Validate complete SSL configuration for a site

        Args:
            protocol: 'http' or 'https'
            auto_ssl: Whether auto SSL is enabled
            support_subdomains: Whether subdomains should be supported
            host: Domain/hostname
            ssl_certificate: Uploaded certificate file
            ssl_key: Uploaded private key file
            ssl_chain: Uploaded certificate chain file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Rule 1: HTTP protocol cannot have SSL-related fields
        if protocol == 'http':
            if ssl_certificate or ssl_key or ssl_chain:
                errors.append(
                    "HTTP protocol cannot have SSL certificates. "
                    "Please remove certificate files or change protocol to HTTPS."
                )
            if auto_ssl:
                errors.append(
                    "HTTP protocol cannot have auto_ssl enabled. "
                    "Auto SSL requires HTTPS protocol."
                )
            # For HTTP, we're done validating
            return (len(errors) == 0, errors)

        # Rule 2: HTTPS requires either auto_ssl or manual certificates
        if protocol == 'https':
            if not auto_ssl and not ssl_certificate:
                errors.append(
                    "HTTPS protocol requires either auto_ssl=True or manual SSL certificate upload."
                )

            # Rule 3: If manual certificates, validate them
            if not auto_ssl:
                cert_errors = self._validate_manual_certificates(
                    host, support_subdomains, ssl_certificate, ssl_key, ssl_chain
                )
                errors.extend(cert_errors)

            # Rule 4: Auto SSL with subdomains needs DNS validation
            if auto_ssl and support_subdomains:
                # This will be handled by returning DNS challenge info
                # We don't add error, just a note
                pass

        return (len(errors) == 0, errors)

    def _validate_manual_certificates(
        self,
        host: str,
        support_subdomains: bool,
        ssl_certificate: Optional[UploadedFile],
        ssl_key: Optional[UploadedFile],
        ssl_chain: Optional[UploadedFile]
        ) -> List[str]:
        """
        Validate manually uploaded SSL certificates

        Returns:
            List of validation errors
        """
        errors = []

        if not ssl_certificate:
            errors.append("SSL certificate file is required when auto_ssl is disabled.")
            return errors

        if not ssl_key:
            errors.append("SSL private key file is required when auto_ssl is disabled.")
            return errors

        # Save files temporarily for validation
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Write certificate to temp file
                cert_path = os.path.join(temp_dir, 'cert.pem')
                with open(cert_path, 'wb') as f:
                    for chunk in ssl_certificate.chunks():
                        f.write(chunk)
                ssl_certificate.seek(0)  # Reset file pointer

                # Write key to temp file
                key_path = os.path.join(temp_dir, 'key.pem')
                with open(key_path, 'wb') as f:
                    for chunk in ssl_key.chunks():
                        f.write(chunk)
                ssl_key.seek(0)  # Reset file pointer

                # Write chain if provided
                chain_path = None
                if ssl_chain:
                    chain_path = os.path.join(temp_dir, 'chain.pem')
                    with open(chain_path, 'wb') as f:
                        for chunk in ssl_chain.chunks():
                            f.write(chunk)
                    ssl_chain.seek(0)  # Reset file pointer

                # Validate certificate
                cert_errors = self._validate_certificate_file(cert_path)
                errors.extend(cert_errors)

                # Validate private key
                key_errors = self._validate_key_file(key_path)
                errors.extend(key_errors)

                # If both are valid, check if they match
                if not cert_errors and not key_errors:
                    match_errors = self._validate_cert_key_match(cert_path, key_path)
                    errors.extend(match_errors)

                # Validate chain if provided
                if chain_path:
                    chain_errors = self._validate_chain_file(cert_path, chain_path)
                    errors.extend(chain_errors)

                # Check domain coverage
                if not cert_errors:
                    domain_errors = self._validate_domain_coverage(
                        cert_path, host, support_subdomains
                    )
                    errors.extend(domain_errors)

            except Exception as e:
                errors.append(f"Error validating certificate files: {str(e)}")

        return errors

    def _validate_certificate_file(self, cert_path: str) -> List[str]:
        """Validate certificate file format and content"""
        errors = []

        try:
            is_valid, message, details = self.cert_checker.validate_certificate(cert_path)

            if not is_valid:
                errors.append(f"Invalid certificate: {message}")
                return errors

            # Check expiration
            if details.get('days_until_expiry', 0) < 0:
                errors.append("Certificate has expired.")
            elif details.get('days_until_expiry', 0) < 7:
                errors.append(f"Certificate expires in {details.get('days_until_expiry')} days. Please renew soon.")

            # Check if certificate is self-signed (warning, not error)
            if details.get('is_self_signed'):
                errors.append("Warning: Certificate appears to be self-signed and may not be trusted by browsers.")

        except Exception as e:
            errors.append(f"Certificate validation error: {str(e)}")

        return errors

    def _validate_key_file(self, key_path: str) -> List[str]:
        """Validate private key file format and content"""
        errors = []

        try:
            is_valid, message, details = self.cert_checker.validate_private_key(key_path)

            if not is_valid:
                errors.append(f"Invalid private key: {message}")
                return errors

            # Check key strength
            key_size = details.get('key_size', 0)
            if key_size < 2048:
                errors.append(f"Private key is too weak ({key_size} bits). Minimum 2048 bits required.")

        except Exception as e:
            errors.append(f"Private key validation error: {str(e)}")

        return errors

    def _validate_cert_key_match(self, cert_path: str, key_path: str) -> List[str]:
        """Validate that certificate and private key match"""
        errors = []

        try:
            matches, message = self.cert_checker.validate_certificate_key_match(
                cert_path, key_path
            )

            if not matches:
                errors.append(f"Certificate and private key do not match: {message}")

        except Exception as e:
            errors.append(f"Certificate/key match validation error: {str(e)}")

        return errors

    def _validate_chain_file(self, cert_path: str, chain_path: str) -> List[str]:
        """Validate certificate chain file"""
        errors = []

        try:
            is_valid, message, details = self.cert_checker.validate_certificate_chain(
                cert_path, chain_path
            )

            if not is_valid:
                errors.append(f"Invalid certificate chain: {message}")

        except Exception as e:
            errors.append(f"Certificate chain validation error: {str(e)}")

        return errors

    def _validate_domain_coverage(
        self,
        cert_path: str,
        host: str,
        support_subdomains: bool
        ) -> List[str]:
        """Validate that certificate covers the required domain(s)"""
        errors = []

        try:
            # Get certificate domain information
            cert_info = self.cert_checker.check_certificate_domains(cert_path)

            if 'error' in cert_info:
                errors.append(f"Cannot verify domain coverage: {cert_info['error']}")
                return errors

            # Check if the main domain is covered
            domain_check = self.cert_checker.check_domain_coverage(host, cert_path)

            if not domain_check.get('matches', False):
                errors.append(
                    f"Certificate does not cover domain '{host}'. "
                    f"Certificate covers: {', '.join(cert_info.get('all_domains', []))}"
                )

            # If subdomains are required, check for wildcard
            if support_subdomains:
                has_wildcard = any(
                    domain.startswith('*.')
                    for domain in cert_info.get('all_domains', [])
                )

                if not has_wildcard:
                    errors.append(
                        f"Subdomain support is enabled but certificate does not include "
                        f"a wildcard domain (*.{host}). The certificate will not cover subdomains."
                    )
                else:
                    # Check if wildcard matches the host
                    wildcard = f"*.{host}"
                    base_domain = host.split('.', 1)[1] if '.' in host else host
                    wildcard_base = f"*.{base_domain}"

                    all_domains = cert_info.get('all_domains', [])
                    if wildcard not in all_domains and wildcard_base not in all_domains:
                        errors.append(
                            f"Subdomain support enabled but certificate wildcard doesn't match. "
                            f"Expected '*.{host}' or '*.{base_domain}', "
                            f"but certificate has: {', '.join([d for d in all_domains if d.startswith('*.')])}."
                        )

        except Exception as e:
            errors.append(f"Domain coverage validation error: {str(e)}")

        return errors

    def get_acme_dns_challenge(self, host: str, support_subdomains: bool) -> Dict:
        """
        Generate ACME DNS challenge information for auto SSL with subdomains

        Args:
            host: Domain name
            support_subdomains: Whether wildcard certificate is needed

        Returns:
            Dictionary with DNS challenge instructions
        """
        if not support_subdomains:
            return {
                'required': False,
                'message': 'DNS challenge not required for single domain with auto SSL'
            }

        # For wildcard certificates, DNS-01 challenge is required
        base_domain = host
        if host.startswith('www.'):
            base_domain = host[4:]

        return {
            'required': True,
            'challenge_type': 'DNS-01',
            'domain': host,
            'wildcard_domain': f"*.{base_domain}",
            'instructions': {
                'step1': f"Add a TXT record to your DNS for domain: _acme-challenge.{base_domain}",
                'step2': "The value will be provided by the ACME client when requesting the certificate",
                'step3': "Wait for DNS propagation (may take 5-60 minutes)",
                'step4': "The certificate will be automatically issued after DNS validation",
            },
            'dns_records': [
                {
                    'type': 'TXT',
                    'name': f"_acme-challenge.{base_domain}",
                    'value': '<ACME_CHALLENGE_VALUE>',
                    'ttl': 300
                }
            ],
            'notes': [
                "Wildcard certificates require DNS-01 challenge validation",
                "You need access to your domain's DNS settings",
                "The challenge value will be generated when certificate is requested",
                "DNS propagation can take time - be patient"
            ]
        }


def validate_protocol_ssl_consistency(protocol: str, auto_ssl: bool,
                                     ssl_certificate: Optional[UploadedFile]) -> None:
    """
    Django model validator for protocol and SSL field consistency

    Raises:
        ValidationError: If configuration is invalid
    """
    if protocol == 'http':
        if auto_ssl:
            raise ValidationError(
                "HTTP protocol cannot have auto_ssl enabled. "
                "Either change protocol to HTTPS or disable auto_ssl."
            )
        if ssl_certificate:
            raise ValidationError(
                "HTTP protocol cannot have SSL certificate. "
                "Either change protocol to HTTPS or remove SSL certificate."
            )

    if protocol == 'https' and not auto_ssl and not ssl_certificate:
        raise ValidationError(
            "HTTPS protocol requires either auto_ssl=True or an SSL certificate upload."
        )


def validate_subdomain_certificate_coverage(support_subdomains: bool,
                                            ssl_certificate: Optional[UploadedFile],
                                            host: str) -> None:
    """
    Django model validator for subdomain support and certificate wildcard

    Raises:
        ValidationError: If certificate doesn't support subdomains when required
    """
    if not support_subdomains or not ssl_certificate:
        return

    # Validate that uploaded certificate supports wildcards
    validator = SiteSSLValidator()

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            cert_path = os.path.join(temp_dir, 'cert.pem')
            with open(cert_path, 'wb') as f:
                for chunk in ssl_certificate.chunks():
                    f.write(chunk)
            ssl_certificate.seek(0)

            cert_info = validator.cert_checker.check_certificate_domains(cert_path)

            if 'error' not in cert_info:
                has_wildcard = any(
                    domain.startswith('*.')
                    for domain in cert_info.get('all_domains', [])
                )

                if not has_wildcard:
                    raise ValidationError(
                        f"Subdomain support is enabled but the certificate does not include "
                        f"a wildcard domain (*.{host}). Please upload a wildcard certificate."
                    )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Error validating certificate for subdomain support: {str(e)}")
