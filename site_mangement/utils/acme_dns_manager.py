"""
ACME DNS Challenge Manager for Wildcard Certificate Automation
Handles DNS-01 challenge creation, validation, and monitoring for Let's Encrypt wildcard certificates
"""
import subprocess
import json
import time
import hashlib
import base64
import secrets
import string
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import dns.resolver
import dns.exception


class ACMEDNSChallengeError(Exception):
    """Base exception for ACME DNS challenge operations"""
    pass


class ACMEDNSManager:
    """
    Manager for ACME DNS-01 challenges required for wildcard certificates
    Provides instructions, validation, and monitoring for DNS challenge completion
    """

    def __init__(self):
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 10
        self.resolver.lifetime = 10

    def generate_challenge_value(self, domain: str) -> Dict[str, str]:
        """
        Generate a DNS challenge value for ACME validation
        
        Args:
            domain: Domain name for the challenge
            
        Returns:
            Dictionary with challenge key and value
        """
        base_domain = self._get_base_domain(domain)
        challenge_key = f"_acme-challenge.{base_domain}"
        
        # Generate a realistic-looking challenge value
        # This simulates what Let's Encrypt would provide
        challenge_value = self._generate_acme_challenge_value()
        
        return {
            'key': challenge_key,
            'value': challenge_value,
            'domain': base_domain,
            'wildcard_domain': f"*.{base_domain}"
        }

    def _generate_acme_challenge_value(self) -> str:
        """
        Generate a realistic ACME challenge value
        ACME challenge values are typically 43 characters long and base64url encoded
        """
        # Generate 32 random bytes (256 bits)
        random_bytes = secrets.token_bytes(32)
        
        # Encode as base64url (URL-safe base64 without padding)
        challenge_value = base64.urlsafe_b64encode(random_bytes).decode('ascii').rstrip('=')
        
        return challenge_value

    def generate_challenge_instructions(
        self,
        domain: str,
        support_subdomains: bool = True,
        challenge_value: Optional[str] = None
    ) -> Dict:
        """
        Generate DNS challenge instructions for a domain

        Args:
            domain: Domain name (e.g., 'example.com')
            support_subdomains: Whether wildcard certificate is needed
            challenge_value: Optional challenge value to use instead of placeholder

        Returns:
            Dictionary with detailed DNS challenge instructions
        """
        base_domain = self._get_base_domain(domain)

        if not support_subdomains:
            # Single domain certificate - HTTP-01 challenge can be used
            return {
                'required': False,
                'challenge_type': 'HTTP-01',
                'domain': domain,
                'message': 'DNS challenge not required for single domain. HTTP-01 challenge will be used automatically.'
            }

        # Wildcard certificate requires DNS-01 challenge
        challenge_record = f"_acme-challenge.{base_domain}"
        
        # Use provided challenge value or placeholder
        display_value = challenge_value if challenge_value else '<ACME_CHALLENGE_VALUE>'
        actual_value = challenge_value if challenge_value else None

        return {
            'required': True,
            'challenge_type': 'DNS-01',
            'domain': domain,
            'base_domain': base_domain,
            'wildcard_domain': f"*.{base_domain}",
            'challenge_record': challenge_record,
            'challenge_value': actual_value,
            'display_value': display_value,
            'instructions': {
                'title': 'DNS Challenge Required for Wildcard Certificate',
                'steps': [
                    {
                        'step': 1,
                        'action': 'Access your DNS provider',
                        'description': f'Log in to your DNS provider (e.g., Cloudflare, Route53, GoDaddy) for domain {base_domain}'
                    },
                    {
                        'step': 2,
                        'action': 'Create TXT record',
                        'description': 'Add a new TXT record with the following details:',
                        'details': {
                            'Type': 'TXT',
                            'Name': challenge_record,
                            'Value': display_value,
                            'TTL': 300
                        }
                    },
                    {
                        'step': 3,
                        'action': 'Wait for DNS propagation',
                        'description': 'DNS changes can take 5-60 minutes to propagate globally',
                        'tips': [
                            'Use online DNS checker tools to verify propagation',
                            'Lower TTL values speed up propagation',
                            'Some providers propagate faster than others'
                        ]
                    },
                    {
                        'step': 4,
                        'action': 'Verify the record',
                        'description': 'Use the verification tool to check if DNS record is visible',
                        'command': f'dig TXT {challenge_record} +short'
                    },
                    {
                        'step': 5,
                        'action': 'Request certificate',
                        'description': 'Once DNS record is verified, the certificate will be issued automatically'
                    }
                ]
            },
            'dns_record_template': {
                'type': 'TXT',
                'name': challenge_record,
                'value': display_value,
                'ttl': 300,
                'priority': None
            },
            'verification_methods': {
                'command_line': f'dig TXT {challenge_record} +short',
                'online_tools': [
                    f'https://toolbox.googleapps.com/apps/dig/#TXT/{challenge_record}',
                    f'https://mxtoolbox.com/SuperTool.aspx?action=txt:{challenge_record}',
                    'https://dnschecker.org/'
                ]
            },
            'important_notes': [
                '⚠️ Wildcard certificates (*.example.com) REQUIRE DNS-01 challenge',
                '⏱️ DNS propagation can take anywhere from 5 minutes to 1 hour',
                '🔐 The challenge value will be generated by Let\'s Encrypt/ACME client',
                '📝 You must have access to your domain\'s DNS settings',
                '🔄 The TXT record can be removed after certificate issuance',
                '⏰ Let\'s Encrypt certificates are valid for 90 days and auto-renewed'
            ],
            'common_dns_providers': [
                {
                    'name': 'Cloudflare',
                    'docs_url': 'https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/',
                    'api_support': True
                },
                {
                    'name': 'AWS Route53',
                    'docs_url': 'https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-creating.html',
                    'api_support': True
                },
                {
                    'name': 'GoDaddy',
                    'docs_url': 'https://www.godaddy.com/help/add-a-txt-record-19232',
                    'api_support': True
                },
                {
                    'name': 'Namecheap',
                    'docs_url': 'https://www.namecheap.com/support/knowledgebase/article.aspx/317/2237/how-do-i-add-txtspfdkimdmarc-records-for-my-domain/',
                    'api_support': False
                },
                {
                    'name': 'Google Domains',
                    'docs_url': 'https://support.google.com/domains/answer/3290350',
                    'api_support': True
                }
            ]
        }

    def verify_dns_challenge_record(
        self,
        domain: str,
        expected_value: Optional[str] = None
    ) -> Dict:
        """
        Verify if DNS TXT record exists for ACME challenge

        Args:
            domain: Domain name
            expected_value: Expected TXT record value (if known)

        Returns:
            Dictionary with verification results
        """
        base_domain = self._get_base_domain(domain)
        challenge_record = f"_acme-challenge.{base_domain}"

        try:
            # Query TXT records
            answers = self.resolver.resolve(challenge_record, 'TXT')

            txt_records = []
            for rdata in answers:
                # Decode TXT record
                value = ''.join([s.decode('utf-8') if isinstance(s, bytes) else s for s in rdata.strings])
                txt_records.append(value)

            if not txt_records:
                return {
                    'exists': False,
                    'record': challenge_record,
                    'message': f'No TXT records found for {challenge_record}',
                    'status': 'missing'
                }

            # Check if expected value is present
            if expected_value:
                if expected_value in txt_records:
                    return {
                        'exists': True,
                        'record': challenge_record,
                        'values': txt_records,
                        'matched': True,
                        'message': f'DNS TXT record found and matches expected value',
                        'status': 'verified'
                    }
                else:
                    return {
                        'exists': True,
                        'record': challenge_record,
                        'values': txt_records,
                        'matched': False,
                        'expected': expected_value,
                        'message': f'DNS TXT record found but value does not match',
                        'status': 'mismatch'
                    }

            # No expected value provided, just confirm existence
            return {
                'exists': True,
                'record': challenge_record,
                'values': txt_records,
                'message': f'Found {len(txt_records)} TXT record(s) for {challenge_record}',
                'status': 'found'
            }

        except dns.resolver.NXDOMAIN:
            return {
                'exists': False,
                'record': challenge_record,
                'message': f'Domain {challenge_record} does not exist',
                'status': 'nxdomain',
                'help': 'The DNS record has not been created yet or DNS has not propagated'
            }
        except dns.resolver.NoAnswer:
            return {
                'exists': False,
                'record': challenge_record,
                'message': f'No TXT records found for {challenge_record}',
                'status': 'no_answer',
                'help': 'The TXT record has not been created or DNS has not propagated'
            }
        except dns.resolver.Timeout:
            return {
                'exists': False,
                'record': challenge_record,
                'message': 'DNS query timeout',
                'status': 'timeout',
                'help': 'DNS server did not respond in time. Try again later.'
            }
        except Exception as e:
            return {
                'exists': False,
                'record': challenge_record,
                'message': f'DNS verification error: {str(e)}',
                'status': 'error'
            }

    def check_dns_propagation(
        self,
        domain: str,
        expected_value: str,
        dns_servers: Optional[List[str]] = None
    ) -> Dict:
        """
        Check DNS propagation across multiple DNS servers

        Args:
            domain: Domain name
            expected_value: Expected TXT record value
            dns_servers: List of DNS servers to check (default: common public DNS)

        Returns:
            Dictionary with propagation status across servers
        """
        if dns_servers is None:
            # Common public DNS servers
            dns_servers = [
                ('8.8.8.8', 'Google DNS'),
                ('8.8.4.4', 'Google DNS Secondary'),
                ('1.1.1.1', 'Cloudflare DNS'),
                ('1.0.0.1', 'Cloudflare DNS Secondary'),
                ('9.9.9.9', 'Quad9 DNS'),
                ('208.67.222.222', 'OpenDNS'),
            ]
        else:
            dns_servers = [(server, f'Custom DNS {i+1}') for i, server in enumerate(dns_servers)]

        base_domain = self._get_base_domain(domain)
        challenge_record = f"_acme-challenge.{base_domain}"

        results = []
        propagated_count = 0

        for server_ip, server_name in dns_servers:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [server_ip]
                resolver.timeout = 5
                resolver.lifetime = 5

                answers = resolver.resolve(challenge_record, 'TXT')
                txt_records = []
                for rdata in answers:
                    value = ''.join([s.decode('utf-8') if isinstance(s, bytes) else s for s in rdata.strings])
                    txt_records.append(value)

                is_propagated = expected_value in txt_records

                results.append({
                    'server': server_name,
                    'ip': server_ip,
                    'propagated': is_propagated,
                    'values': txt_records,
                    'status': 'success'
                })

                if is_propagated:
                    propagated_count += 1

            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                results.append({
                    'server': server_name,
                    'ip': server_ip,
                    'propagated': False,
                    'values': [],
                    'status': 'not_found'
                })
            except dns.resolver.Timeout:
                results.append({
                    'server': server_name,
                    'ip': server_ip,
                    'propagated': False,
                    'status': 'timeout'
                })
            except Exception as e:
                results.append({
                    'server': server_name,
                    'ip': server_ip,
                    'propagated': False,
                    'status': 'error',
                    'error': str(e)
                })

        total_servers = len(dns_servers)
        propagation_percentage = (propagated_count / total_servers * 100) if total_servers > 0 else 0

        return {
            'record': challenge_record,
            'expected_value': expected_value,
            'total_servers_checked': total_servers,
            'propagated_servers': propagated_count,
            'propagation_percentage': round(propagation_percentage, 2),
            'fully_propagated': propagated_count == total_servers,
            'mostly_propagated': propagation_percentage >= 80,
            'results': results,
            'recommendation': self._get_propagation_recommendation(propagation_percentage)
        }

    def monitor_dns_propagation(
        self,
        domain: str,
        expected_value: str,
        max_wait_minutes: int = 60,
        check_interval_seconds: int = 30
    ) -> Dict:
        """
        Monitor DNS propagation with periodic checks until complete or timeout

        Args:
            domain: Domain name
            expected_value: Expected TXT record value
            max_wait_minutes: Maximum time to wait in minutes
            check_interval_seconds: Seconds between checks

        Returns:
            Dictionary with monitoring results
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=max_wait_minutes)
        checks = []

        base_domain = self._get_base_domain(domain)
        challenge_record = f"_acme-challenge.{base_domain}"

        while datetime.now() < end_time:
            check_time = datetime.now()
            elapsed_minutes = (check_time - start_time).total_seconds() / 60

            # Perform propagation check
            propagation_result = self.check_dns_propagation(domain, expected_value)

            check_result = {
                'timestamp': check_time.isoformat(),
                'elapsed_minutes': round(elapsed_minutes, 2),
                'propagation_percentage': propagation_result['propagation_percentage'],
                'propagated_servers': propagation_result['propagated_servers'],
                'total_servers': propagation_result['total_servers_checked']
            }

            checks.append(check_result)

            # Check if fully propagated
            if propagation_result['fully_propagated']:
                return {
                    'success': True,
                    'record': challenge_record,
                    'message': 'DNS record fully propagated across all servers',
                    'total_time_minutes': round(elapsed_minutes, 2),
                    'checks_performed': len(checks),
                    'final_propagation': propagation_result,
                    'check_history': checks
                }

            # Wait before next check
            if datetime.now() + timedelta(seconds=check_interval_seconds) < end_time:
                time.sleep(check_interval_seconds)
            else:
                break

        # Timeout reached
        return {
            'success': False,
            'record': challenge_record,
            'message': f'DNS propagation incomplete after {max_wait_minutes} minutes',
            'total_time_minutes': max_wait_minutes,
            'checks_performed': len(checks),
            'final_propagation': propagation_result,
            'check_history': checks,
            'recommendation': 'Continue waiting or check DNS provider settings'
        }

    def generate_acme_dns_script(self, domain: str, provider: str = 'generic') -> str:
        """
        Generate a shell script for automated DNS challenge with ACME client

        Args:
            domain: Domain name
            provider: DNS provider ('cloudflare', 'route53', 'generic')

        Returns:
            Shell script content
        """
        base_domain = self._get_base_domain(domain)

        if provider == 'cloudflare':
            return self._generate_cloudflare_script(base_domain)
        elif provider == 'route53':
            return self._generate_route53_script(base_domain)
        else:
            return self._generate_generic_script(base_domain)

    def _get_base_domain(self, domain: str) -> str:
        """Extract base domain from full domain"""
        if domain.startswith('www.'):
            return domain[4:]
        return domain

    def _get_propagation_recommendation(self, percentage: float) -> str:
        """Get recommendation based on propagation percentage"""
        if percentage >= 100:
            return 'DNS record fully propagated. Ready to proceed with certificate issuance.'
        elif percentage >= 80:
            return 'DNS record mostly propagated. You can proceed, but some regions may take longer.'
        elif percentage >= 50:
            return 'DNS record partially propagated. Wait a bit longer for better coverage.'
        elif percentage > 0:
            return 'DNS record starting to propagate. Wait 10-20 more minutes.'
        else:
            return 'DNS record not visible yet. Verify the TXT record was created correctly.'

    def _generate_cloudflare_script(self, domain: str) -> str:
        """Generate Cloudflare-specific ACME script"""
        return f"""#!/bin/bash
# ACME DNS Challenge Script for Cloudflare
# Domain: {domain}

# Set your Cloudflare credentials
export CF_Token="YOUR_CLOUDFLARE_API_TOKEN"
export CF_Zone_ID="YOUR_ZONE_ID"

# Install acme.sh if not already installed
if [ ! -d ~/.acme.sh ]; then
    curl https://get.acme.sh | sh
fi

# Source acme.sh
source ~/.acme.sh/acme.sh.env

# Issue wildcard certificate using Cloudflare DNS
acme.sh --issue --dns dns_cf -d {domain} -d *.{domain}

# Install certificate (adjust paths as needed)
acme.sh --install-cert -d {domain} \\
    --cert-file /path/to/cert.pem \\
    --key-file /path/to/key.pem \\
    --fullchain-file /path/to/fullchain.pem

echo "Certificate issued and installed successfully!"
"""

    def _generate_route53_script(self, domain: str) -> str:
        """Generate AWS Route53-specific ACME script"""
        return f"""#!/bin/bash
# ACME DNS Challenge Script for AWS Route53
# Domain: {domain}

# Set AWS credentials
export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_KEY"

# Install acme.sh if not already installed
if [ ! -d ~/.acme.sh ]; then
    curl https://get.acme.sh | sh
fi

# Source acme.sh
source ~/.acme.sh/acme.sh.env

# Issue wildcard certificate using Route53 DNS
acme.sh --issue --dns dns_aws -d {domain} -d *.{domain}

# Install certificate
acme.sh --install-cert -d {domain} \\
    --cert-file /path/to/cert.pem \\
    --key-file /path/to/key.pem \\
    --fullchain-file /path/to/fullchain.pem

echo "Certificate issued and installed successfully!"
"""

    def _generate_generic_script(self, domain: str) -> str:
        """Generate generic manual ACME script"""
        return f"""#!/bin/bash
# Generic ACME DNS Challenge Script
# Domain: {domain}

echo "=== ACME DNS Challenge for {domain} ==="
echo ""
echo "This script will guide you through the manual DNS challenge process."
echo ""

# Install acme.sh if not already installed
if [ ! -d ~/.acme.sh ]; then
    echo "Installing acme.sh..."
    curl https://get.acme.sh | sh
    source ~/.acme.sh/acme.sh.env
fi

echo "Starting certificate request..."
echo ""
echo "You will be prompted to create a TXT record at your DNS provider."
echo "Record name: _acme-challenge.{domain}"
echo ""

# Use manual DNS mode
~/.acme.sh/acme.sh --issue --dns -d {domain} -d *.{domain} --yes-I-know-dns-manual-mode-enough-go-ahead-please

echo ""
echo "After creating the DNS record and verifying propagation, renew with:"
echo "~/.acme.sh/acme.sh --renew -d {domain} --yes-I-know-dns-manual-mode-enough-go-ahead-please"
"""

    def format_instructions_for_display(self, instructions: Dict) -> str:
        """
        Format DNS challenge instructions for human-readable display

        Args:
            instructions: Instructions dictionary from generate_challenge_instructions

        Returns:
            Formatted string for display
        """
        if not instructions.get('required'):
            return instructions.get('message', 'No DNS challenge required')

        output = []
        output.append("=" * 80)
        output.append("DNS-01 CHALLENGE REQUIRED FOR WILDCARD CERTIFICATE")
        output.append("=" * 80)
        output.append("")
        output.append(f"Domain: {instructions['domain']}")
        output.append(f"Wildcard: {instructions['wildcard_domain']}")
        output.append(f"Challenge Record: {instructions['challenge_record']}")
        output.append("")
        output.append("-" * 80)
        output.append("INSTRUCTIONS")
        output.append("-" * 80)
        output.append("")

        for step_info in instructions['instructions']['steps']:
            output.append(f"Step {step_info['step']}: {step_info['action']}")
            output.append(f"  {step_info['description']}")
            if 'details' in step_info:
                output.append("  Details:")
                for key, value in step_info['details'].items():
                    output.append(f"    {key}: {value}")
            if 'command' in step_info:
                output.append(f"  Command: {step_info['command']}")
            output.append("")

        output.append("-" * 80)
        output.append("IMPORTANT NOTES")
        output.append("-" * 80)
        for note in instructions['important_notes']:
            output.append(f"  {note}")
        output.append("")

        return "\n".join(output)
