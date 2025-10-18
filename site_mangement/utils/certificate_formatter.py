"""
Certificate Formatter Module for Caddy WAF System
Provides consistent formatting and display of certificate information
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class CertificateFormatter:
    """
    Handles formatting and display of certificate information
    Provides consistent output formatting across all certificate utilities
    """

    @staticmethod
    def format_certificate_info(cert_info: Dict[str, Any], detailed: bool = False) -> str:
        """
        Format certificate information for display

        Args:
            cert_info: Certificate information dictionary
            detailed: Whether to show detailed information

        Returns:
            Formatted string with certificate information
        """
        if "error" in cert_info:
            return f"❌ Certificate error: {cert_info['error']}"

        output = []
        output.append("📋 Certificate Information:")
        output.append(f"   Common Name: {cert_info.get('common_name', 'N/A')}")
        output.append(f"   Expires: {cert_info.get('expires', 'N/A')}")

        # Status
        is_expired = cert_info.get('is_expired')
        if is_expired is True:
            output.append("   Status: ❌ EXPIRED")
        elif is_expired is False:
            output.append("   Status: ✅ Valid")
        else:
            output.append("   Status: ⚠️  Unknown")

        # Days until expiry
        days_until_expiry = cert_info.get('days_until_expiry')
        if days_until_expiry is not None:
            if days_until_expiry < 0:
                output.append(f"   Days since expiry: {abs(days_until_expiry)}")
            elif days_until_expiry <= 30:
                output.append(f"   Days until expiry: {days_until_expiry} ⚠️")
            else:
                output.append(f"   Days until expiry: {days_until_expiry}")

        # SAN domains
        san_domains = cert_info.get('san_domains', [])
        if san_domains:
            output.append(f"   SAN Domains ({len(san_domains)}):")
            for domain in san_domains:
                output.append(f"     - {domain}")

        # Wildcard domains
        wildcard_domains = cert_info.get('wildcard_domains', [])
        if wildcard_domains:
            output.append(f"   Wildcard Domains ({len(wildcard_domains)}):")
            for domain in wildcard_domains:
                output.append(f"     - {domain}")

        if detailed:
            output.append(CertificateFormatter._format_detailed_info(cert_info))

        return "\n".join(output)

    @staticmethod
    def _format_detailed_info(cert_info: Dict[str, Any]) -> str:
        """Format detailed certificate information"""
        output = []
        output.append("\n🔍 Detailed Information:")

        # Issuer information
        issuer = cert_info.get('issuer')
        if issuer:
            output.append(f"   Issuer: {issuer}")

        # Subject information
        subject = cert_info.get('subject')
        if subject:
            output.append(f"   Subject: {subject}")

        # Serial number
        serial = cert_info.get('serial_number')
        if serial:
            output.append(f"   Serial Number: {serial}")

        # Not before date
        not_before = cert_info.get('not_before')
        if not_before:
            output.append(f"   Valid From: {not_before}")

        # Signature algorithm
        sig_algorithm = cert_info.get('signature_algorithm')
        if sig_algorithm:
            output.append(f"   Signature Algorithm: {sig_algorithm}")

        # Public key algorithm
        pub_key_algorithm = cert_info.get('public_key_algorithm')
        if pub_key_algorithm:
            output.append(f"   Public Key Algorithm: {pub_key_algorithm}")

        # Key size
        key_size = cert_info.get('key_size')
        if key_size:
            output.append(f"   Key Size: {key_size} bits")

        # Version
        version = cert_info.get('version')
        if version:
            output.append(f"   Version: {version}")

        return "\n".join(output)

    @staticmethod
    def format_domain_coverage_result(result: Dict[str, Any]) -> str:
        """
        Format domain coverage check result

        Args:
            result: Domain coverage result dictionary

        Returns:
            Formatted string with domain coverage information
        """
        if result.get("matches"):
            match_type = result.get("type", "unknown")
            matched_value = result.get("matched_value", "unknown")
            return f"✅ Domain is covered by certificate ({match_type}: {matched_value})"
        else:
            reason = result.get("reason", "Unknown reason")
            return f"❌ Domain is not covered by certificate: {reason}"

    @staticmethod
    def format_validation_result(is_valid: bool, message: str, details: Dict[str, Any]) -> str:
        """
        Format certificate validation result

        Args:
            is_valid: Whether the certificate is valid
            message: Validation message
            details: Additional validation details

        Returns:
            Formatted string with validation result
        """
        status_icon = "✅" if is_valid else "❌"
        output = [f"{status_icon} {message}"]

        if details:
            # Add key details
            if "is_expired" in details:
                exp_status = "EXPIRED" if details["is_expired"] else "Valid"
                output.append(f"   Expiration: {exp_status}")

            if "days_until_expiry" in details and details["days_until_expiry"] is not None:
                days = details["days_until_expiry"]
                if days < 0:
                    output.append(f"   Days since expiry: {abs(days)}")
                else:
                    output.append(f"   Days until expiry: {days}")

            if "common_name" in details:
                output.append(f"   Common Name: {details['common_name']}")

        return "\n".join(output)

    @staticmethod
    def format_remote_certificate_info(remote_info: Dict[str, Any]) -> str:
        """
        Format remote certificate information

        Args:
            remote_info: Remote certificate information dictionary

        Returns:
            Formatted string with remote certificate information
        """
        if "error" in remote_info:
            return f"❌ Remote certificate error: {remote_info['error']}"

        output = []
        output.append(f"🌐 Remote Certificate for {remote_info.get('hostname', 'unknown')}:{remote_info.get('port', 443)}")
        output.append(f"   Common Name: {remote_info.get('common_name', 'N/A')}")
        output.append(f"   Organization: {remote_info.get('organization', 'N/A')}")
        output.append(f"   Issuer: {remote_info.get('issuer_cn', 'N/A')}")

        # Expiration info
        is_expired = remote_info.get('is_expired')
        if is_expired is True:
            output.append("   Status: ❌ EXPIRED")
        elif is_expired is False:
            output.append("   Status: ✅ Valid")
        else:
            output.append("   Status: ⚠️  Unknown")

        days_until_expiry = remote_info.get('days_until_expiry')
        if days_until_expiry is not None:
            if days_until_expiry < 0:
                output.append(f"   Days since expiry: {abs(days_until_expiry)}")
            else:
                output.append(f"   Days until expiry: {days_until_expiry}")

        # SAN domains
        san_domains = remote_info.get('san_domains', [])
        if san_domains:
            output.append(f"   SAN Domains ({len(san_domains)}):")
            for domain in san_domains:
                output.append(f"     - {domain}")

        return "\n".join(output)

    @staticmethod
    def format_certificate_comparison(comparison: Dict[str, Any]) -> str:
        """
        Format certificate comparison result

        Args:
            comparison: Certificate comparison dictionary

        Returns:
            Formatted string with comparison result
        """
        if "error" in comparison:
            return f"❌ Comparison error: {comparison['error']}"

        output = []
        if comparison.get("identical"):
            output.append("✅ Certificates are identical")
        else:
            output.append("❌ Certificates are different")

        # Show fingerprints
        fp1 = comparison.get("cert1_fingerprint")
        fp2 = comparison.get("cert2_fingerprint")
        if fp1 and fp2:
            output.append(f"   Certificate 1 Fingerprint: {fp1}")
            output.append(f"   Certificate 2 Fingerprint: {fp2}")

        # Show differences
        differences = comparison.get("differences", [])
        if differences:
            output.append("   Differences:")
            for diff in differences:
                field = diff.get("field", "unknown")
                val1 = diff.get("cert1", "N/A")
                val2 = diff.get("cert2", "N/A")
                output.append(f"     - {field}: '{val1}' vs '{val2}'")

        return "\n".join(output)

    @staticmethod
    def format_chain_analysis(chain_info: Dict[str, Any]) -> str:
        """
        Format certificate chain analysis

        Args:
            chain_info: Chain analysis dictionary

        Returns:
            Formatted string with chain analysis
        """
        output = []
        output.append("🔗 Certificate Chain Analysis:")
        output.append(f"   Chain Length: {chain_info.get('chain_length', 0)}")
        output.append(f"   Self-Signed: {'Yes' if chain_info.get('is_self_signed') else 'No'}")
        output.append(f"   Has Intermediate: {'Yes' if chain_info.get('has_intermediate') else 'No'}")

        certificates = chain_info.get("certificates", [])
        if certificates:
            output.append("   Certificates:")
            for i, cert in enumerate(certificates, 1):
                cert_type = cert.get("type", "unknown")
                subject = cert.get("subject", "N/A")
                issuer = cert.get("issuer", "N/A")
                output.append(f"     {i}. {cert_type.upper()}: {subject}")
                output.append(f"        Issuer: {issuer}")

        if "analysis_error" in chain_info:
            output.append(f"   ⚠️  Analysis Error: {chain_info['analysis_error']}")

        return "\n".join(output)

    @staticmethod
    def format_scan_results(scan_results: List[Dict[str, Any]]) -> str:
        """
        Format certificate scan results

        Args:
            scan_results: List of certificate scan results

        Returns:
            Formatted string with scan results
        """
        if not scan_results:
            return "No certificates found"

        output = []
        output.append(f"📊 Certificate Scan Results ({len(scan_results)} certificates):")

        # Categorize results
        valid_certs = []
        expired_certs = []
        expiring_soon = []
        errors = []

        for result in scan_results:
            if "error" in result:
                errors.append(result)
            elif result.get("is_expired"):
                expired_certs.append(result)
            elif result.get("days_until_expiry", 999) <= 30:
                expiring_soon.append(result)
            else:
                valid_certs.append(result)

        # Summary
        output.append(f"   ✅ Valid: {len(valid_certs)}")
        output.append(f"   ⚠️  Expiring Soon (≤30 days): {len(expiring_soon)}")
        output.append(f"   ❌ Expired: {len(expired_certs)}")
        output.append(f"   🚫 Errors: {len(errors)}")

        # Show details for each category
        if expired_certs:
            output.append("\n❌ Expired Certificates:")
            for cert in expired_certs:
                output.append(f"   - {cert.get('path', 'Unknown')}: {cert.get('common_name', 'N/A')}")

        if expiring_soon:
            output.append("\n⚠️  Expiring Soon:")
            for cert in expiring_soon:
                days = cert.get("days_until_expiry", 0)
                output.append(f"   - {cert.get('path', 'Unknown')}: {cert.get('common_name', 'N/A')} ({days} days)")

        if errors:
            output.append("\n🚫 Errors:")
            for cert in errors:
                output.append(f"   - {cert.get('path', 'Unknown')}: {cert.get('error', 'Unknown error')}")

        return "\n".join(output)



