"""
Certificate Validation Module for Caddy WAF System
Provides comprehensive certificate validation functionality
"""
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

from .certificate_operations import CertificateOperations, CertificateError


class CertificateValidation(CertificateOperations):
    """
    Comprehensive certificate validation functionality
    Handles certificate validation, key matching, and chain validation
    """

    def __init__(self):
        super().__init__()

    def validate_private_key(self, key_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate private key file

        Args:
            key_path: Path to private key file

        Returns:
            Tuple of (is_valid, message, details)
        """
        try:
            self._validate_file_exists(key_path, "private key")

            # Try different key types
            key_types = [
                ('rsa', ['openssl', 'rsa', '-in', key_path, '-check', '-noout']),
                ('ec', ['openssl', 'ec', '-in', key_path, '-check', '-noout']),
                ('generic', ['openssl', 'pkey', '-in', key_path, '-check', '-noout'])
            ]

            for key_type, command in key_types:
                success, stdout, stderr = self._run_openssl_command(command)
                if success:
                    return True, f"{key_type.upper()} private key is valid", {"key_type": key_type}

            return False, f"Invalid private key: {stderr}", {}

        except FileNotFoundError as e:
            return False, str(e), {}
        except Exception as e:
            return False, f"Key validation error: {str(e)}", {}

    def validate_certificate_key_match(self, cert_path: str, key_path: str) -> Tuple[bool, str]:
        """
        Validate that certificate and private key match

        Args:
            cert_path: Path to certificate file
            key_path: Path to private key file

        Returns:
            Tuple of (match, message)
        """
        try:
            self._validate_file_exists(cert_path, "certificate")
            self._validate_file_exists(key_path, "private key")

            # Get certificate public key
            cert_success, cert_stdout, cert_stderr = self._run_openssl_command([
                'openssl', 'x509', '-in', cert_path, '-pubkey', '-noout'
            ])

            if not cert_success:
                return False, f"Failed to extract certificate public key: {cert_stderr}"

            # Get private key public key
            key_success, key_stdout, key_stderr = self._run_openssl_command([
                'openssl', 'pkey', '-in', key_path, '-pubout'
            ])

            if not key_success:
                return False, f"Failed to extract private key public key: {key_stderr}"

            # Compare the public keys
            if cert_stdout.strip() == key_stdout.strip():
                return True, "Certificate and private key match"
            else:
                return False, "Certificate and private key do not match"

        except FileNotFoundError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Key matching validation error: {str(e)}"

    def validate_certificate_comprehensive(self, cert_path: str) -> Tuple[bool, str, Dict]:
        """
        Comprehensive certificate validation including expiration, key usage, and metadata

        Args:
            cert_path: Path to certificate file

        Returns:
            Tuple of (is_valid, message, details)
        """
        try:
            self._validate_file_exists(cert_path, "certificate")

            # Get comprehensive certificate information
            cert_info = self.get_comprehensive_certificate_info(cert_path)

            if "error" in cert_info:
                return False, cert_info["error"], {}

            # Check if certificate is expired
            if cert_info.get("is_expired") is True:
                return False, "Certificate has expired", cert_info

            # Additional validation checks
            validation_issues = []

            # Get certificate text for advanced validation
            cert_text_result = self.get_certificate_text_info(cert_path)
            if "cert_text" in cert_text_result:
                cert_text = cert_text_result["cert_text"]

                # Check key usage and extensions
                if "Digital Signature" not in cert_text and "Key Encipherment" not in cert_text:
                    validation_issues.append("Missing required key usage extensions")

            if validation_issues:
                return False, f"Certificate validation issues: {'; '.join(validation_issues)}", cert_info

            return True, "Certificate is valid", cert_info

        except FileNotFoundError as e:
            return False, str(e), {}
        except Exception as e:
            return False, f"Validation error: {str(e)}", {}

    def analyze_certificate_chain(self, cert_path: str, chain_path: Optional[str] = None) -> Dict:
        """
        Analyze certificate chain and return detailed information

        Args:
            cert_path: Path to main certificate
            chain_path: Optional path to certificate chain file

        Returns:
            Dictionary with chain analysis information
        """
        chain_info = {
            "chain_length": 1,
            "certificates": [],
            "is_self_signed": False,
            "has_intermediate": False
        }

        try:
            # Analyze main certificate
            metadata = self.get_certificate_metadata(cert_path)
            if metadata:
                chain_info["certificates"].append({
                    "type": "end_entity",
                    "subject": metadata.get("subject"),
                    "issuer": metadata.get("issuer"),
                    "serial": metadata.get("serial_number")
                })

                # Check if self-signed
                chain_info["is_self_signed"] = metadata.get("subject") == metadata.get("issuer")

            # Analyze chain file if provided
            if chain_path and Path(chain_path).exists():
                chain_certs = self.split_certificate_chain(chain_path)
                chain_info["chain_length"] += len(chain_certs)
                chain_info["has_intermediate"] = len(chain_certs) > 0

                for i, chain_cert_pem in enumerate(chain_certs):
                    # Create temporary file and get metadata
                    tmp_path = self.create_temporary_certificate(chain_cert_pem)
                    try:
                        cert_metadata = self.get_certificate_metadata(tmp_path)
                        if cert_metadata:
                            cert_type = "intermediate" if i < len(chain_certs) - 1 else "root"
                            chain_info["certificates"].append({
                                "type": cert_type,
                                "subject": cert_metadata.get("subject"),
                                "issuer": cert_metadata.get("issuer"),
                                "serial": cert_metadata.get("serial_number")
                            })
                    finally:
                        self.cleanup_temporary_file(tmp_path)

        except Exception as e:
            chain_info["analysis_error"] = str(e)

        return chain_info

    def validate_certificate_chain_comprehensive(self, cert_path: str, chain_path: Optional[str] = None, ca_bundle_path: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        Comprehensive certificate chain validation

        Args:
            cert_path: Path to certificate file
            chain_path: Optional path to certificate chain file
            ca_bundle_path: Optional path to CA bundle file

        Returns:
            Tuple of (is_valid, message, details)
        """
        try:
            self._validate_file_exists(cert_path, "certificate")

            details = {}

            # First validate the certificate itself
            cert_valid, cert_msg, cert_details = self.validate_certificate_comprehensive(cert_path)
            details.update(cert_details)

            if not cert_valid:
                return False, f"Certificate validation failed: {cert_msg}", details

            # Build verification command
            verify_cmd = ['openssl', 'verify']

            # Add CA bundle if provided
            if ca_bundle_path and Path(ca_bundle_path).exists():
                verify_cmd.extend(['-CAfile', ca_bundle_path])

            # Add certificate chain if provided
            if chain_path and Path(chain_path).exists():
                verify_cmd.extend(['-untrusted', chain_path])

            # Add the certificate to verify
            verify_cmd.append(cert_path)

            # Run verification
            success, stdout, stderr = self._run_openssl_command(verify_cmd, timeout=30)

            details['verification_output'] = stdout.strip()
            details['verification_error'] = stderr.strip()

            if success:
                if "OK" in stdout:
                    # Get chain details
                    chain_details = self.analyze_certificate_chain(cert_path, chain_path)
                    details.update(chain_details)
                    return True, "Certificate chain is valid", details
                else:
                    return False, f"Chain verification failed: {stdout}", details
            else:
                error_msg = stderr if stderr else stdout
                return False, f"Chain validation error: {error_msg}", details

        except Exception as e:
            return False, f"Chain validation error: {str(e)}", {}



