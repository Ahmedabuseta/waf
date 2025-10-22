"""
Certificate Checker module for Caddy WAF System
Provides a clean interface for certificate validation, domain checking, and SSL management
"""
from typing import Dict, Optional, Tuple, Any

from .certificate_operations import CertificateOperations
from .certificate_validation import CertificateValidation
from .certificate_formatter import CertificateFormatter


class CertificateChecker:
    """
    Clean interface for certificate validation and checking functionality
    Combines operations, validation, and formatting in a simple API
    """

    def __init__(self):
        self.operations = CertificateOperations()
        self.validation = CertificateValidation()
        self.formatter = CertificateFormatter()

    def check_certificate_domains(self, cert_path: str) -> Dict:
        """
        Check what domains a certificate covers
        Returns comprehensive domain information including wildcards and expiration
        """
        try:
            return self.operations.get_comprehensive_certificate_info(cert_path)
        except Exception as e:
            return {"error": f"Certificate check failed: {str(e)}"}

    def validate_certificate(self, cert_path: str) -> Tuple[bool, str, Dict]:
        """
        Validate SSL certificate
        Returns: (is_valid, message, details)
        """
        return self.validation.validate_certificate_comprehensive(cert_path)

    def validate_certificate_chain(self, cert_path: str, chain_path: Optional[str] = None, ca_bundle_path: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        Validate SSL certificate chain
        Returns: (is_valid, message, details)
        """
        return self.validation.validate_certificate_chain_comprehensive(cert_path, chain_path, ca_bundle_path)

    def validate_private_key(self, key_path: str) -> Tuple[bool, str, Dict]:
        """
        Validate private key file
        Returns: (is_valid, message, details)
        """
        return self.validation.validate_private_key(key_path)

    def validate_certificate_key_match(self, cert_path: str, key_path: str) -> Tuple[bool, str]:
        """
        Validate that certificate and private key match
        Returns: (match, message)
        """
        return self.validation.validate_certificate_key_match(cert_path, key_path)

    def check_domain_coverage(self, domain: str, cert_path: str) -> Dict:
        """
        Check if a domain is covered by a certificate
        Returns: Domain coverage information
        """
        return self.operations.domain_matches_certificate(domain, cert_path)

    def check_remote_certificate(self, hostname: str, port: int = 443, timeout: int = 10) -> Dict:
        """
        Check the certificate currently served by a remote host
        Returns: Remote certificate information
        """
        return self.operations.check_remote_certificate(hostname, port, timeout)

    def compare_certificates(self, cert1_path: str, cert2_path: str) -> Dict:
        """Compare two certificates and return differences"""
        try:
            cert1_info = self.operations.get_comprehensive_certificate_info(cert1_path)
            cert2_info = self.operations.get_comprehensive_certificate_info(cert2_path)

            if "error" in cert1_info:
                return {"error": f"Certificate 1 error: {cert1_info['error']}"}
            if "error" in cert2_info:
                return {"error": f"Certificate 2 error: {cert2_info['error']}"}

            # Get fingerprints for comparison
            fp1 = self.operations.get_certificate_fingerprint(cert1_path)
            fp2 = self.operations.get_certificate_fingerprint(cert2_path)

            comparison = {
                "identical": fp1 == fp2 and fp1 is not None,
                "cert1_fingerprint": fp1,
                "cert2_fingerprint": fp2,
                "differences": []
            }

            # Compare domains
            if cert1_info.get("common_name") != cert2_info.get("common_name"):
                comparison["differences"].append({
                    "field": "common_name",
                    "cert1": cert1_info.get("common_name"),
                    "cert2": cert2_info.get("common_name")
                })

            if set(cert1_info.get("san_domains", [])) != set(cert2_info.get("san_domains", [])):
                comparison["differences"].append({
                    "field": "san_domains",
                    "cert1": cert1_info.get("san_domains", []),
                    "cert2": cert2_info.get("san_domains", [])
                })

            if cert1_info.get("expires") != cert2_info.get("expires"):
                comparison["differences"].append({
                    "field": "expiration",
                    "cert1": cert1_info.get("expires"),
                    "cert2": cert2_info.get("expires")
                })

            return comparison

        except Exception as e:
            return {"error": f"Certificate comparison failed: {str(e)}"}

    def analyze_certificate_chain(self, cert_path: str, chain_path: Optional[str] = None) -> Dict:
        """
        Analyze certificate chain and return detailed information
        Returns: Chain analysis information
        """
        return self.validation.analyze_certificate_chain(cert_path, chain_path)

    # Formatting methods for easy output
    def format_certificate_info(self, cert_info: Dict[str, Any], detailed: bool = False) -> str:
        """Format certificate information for display"""
        return self.formatter.format_certificate_info(cert_info, detailed)

    def format_domain_coverage_result(self, result: Dict[str, Any]) -> str:
        """Format domain coverage check result"""
        return self.formatter.format_domain_coverage_result(result)

    def format_validation_result(self, is_valid: bool, message: str, details: Dict[str, Any]) -> str:
        """Format certificate validation result"""
        return self.formatter.format_validation_result(is_valid, message, details)

    def format_remote_certificate_info(self, remote_info: Dict[str, Any]) -> str:
        """Format remote certificate information"""
        return self.formatter.format_remote_certificate_info(remote_info)

    def format_certificate_comparison(self, comparison: Dict[str, Any]) -> str:
        """Format certificate comparison result"""
        return self.formatter.format_certificate_comparison(comparison)

    def format_chain_analysis(self, chain_info: Dict[str, Any]) -> str:
        """Format certificate chain analysis"""
        return self.formatter.format_chain_analysis(chain_info)