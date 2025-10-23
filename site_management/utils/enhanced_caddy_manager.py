"""
Enhanced Caddy Manager with comprehensive SSL validation, logging, and subdomain support
Integrates with the new SSL validation system for secure certificate management
"""
import requests
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import our logging and validation systems
from site_management.caddy_logger import caddy_logger
from site_management.validators import SiteSSLValidator
from site_management.utils.certificate_checker import CertificateChecker
from site_management.utils.acme_dns_manager import ACMEDNSManager


@dataclass
class CaddyConfig:
    """Enhanced Caddy configuration for a site with comprehensive SSL support"""
    host: str
    # addresses: List[Dict[str, Any]]
    protocol: str = 'https'
    auto_ssl: bool = False
    support_subdomains: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_chain_path: Optional[str] = None
    # load_balancer_algorithm: str = 'round_robin'
    auto_https_redirect: bool = True
    # health_check_path: str = '/health'
    # health_check_interval: str = '30s'
    # health_check_timeout: str = '5s'
    # trusted_proxies: List[str] = field(default_factory=list)
    max_request_body_size: str = '10MB'

    def __post_init__(self):
        """Validate configuration after initialization"""
        # if not self.host:
        #     raise ValueError("Host is required")
        # if not self.addresses:
        #     raise ValueError("At least one address is required")
        if self.protocol not in ['http', 'https']:
            raise ValueError(f"Invalid protocol: {self.protocol}")


class CaddyAPIError(Exception):
    """Custom exception for Caddy API errors"""
    pass


class CaddyConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass


class EnhancedCaddyManager:
    """
    Enhanced Caddy manager with comprehensive logging, SSL validation,
    subdomain support, and DNS challenge management
    """

    def __init__(self,
                 api_url: str = "http://localhost:2019",
                 base_path: str = "/etc/caddy",
                 enable_logging: bool = True,
                 enable_validation: bool = True):
        self.api_url = api_url.rstrip('/')
        self.config_endpoint = f"{self.api_url}/config"
        self.load_endpoint = f"{self.api_url}/load"

        # File paths
        self.base_path = Path(base_path)
        self.sites_dir = self.base_path / "sites"
        self.certs_dir = self.base_path / "certs"
        self.acme_dir = self.base_path / "acme"
        self.main_caddyfile = self.base_path / "Caddyfile"

        # Create directories
        self.sites_dir.mkdir(parents=True, exist_ok=True)
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.acme_dir.mkdir(parents=True, exist_ok=True)

        # Logging
        self.enable_logging = enable_logging
        self.logger = caddy_logger if enable_logging else None

        # Validation
        self.enable_validation = enable_validation
        self.ssl_validator = SiteSSLValidator() if enable_validation else None
        self.cert_checker = CertificateChecker()
        self.acme_manager = ACMEDNSManager()

        # Initialize main Caddyfile
        self._ensure_main_caddyfile()

    def _ensure_main_caddyfile(self):
        """Ensure main Caddyfile exists with proper import structure"""
        if not self.main_caddyfile.exists():
            main_config = """# Caddy WAF Site Management - Main Configuration
            {
                admin localhost:2019

                # Global options
                auto_https off  # Managed per-site

                # ACME settings for Let's Encrypt
                email admin@example.com

                # Logging
                log {
                    output file /var/log/caddy/access.log
                    format json
                }
            }

            # Import all site configurations
            import sites/*.caddy
        """
            with open(self.main_caddyfile, 'w') as f:
                f.write(main_config)

            if self.logger:
                self.logger.main_logger.info("Created main Caddyfile with import structure")

    def check_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Caddy API is accessible

        Returns:
            Tuple of (is_connected, error_message)
        """
        try:
            response = requests.get(f"{self.api_url}/config/", timeout=5)

            if response.status_code == 200:
                return True, None
            else:
                return False, f"API returned status code {response.status_code}"

        except requests.ConnectionError:
            return False, "Cannot connect to Caddy API - is Caddy running?"
        except requests.Timeout:
            return False, "Caddy API connection timeout"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def validate_site_config(self, config: CaddyConfig) -> Tuple[bool, List[str]]:
        """
        Validate site configuration before applying

        Args:
            config: CaddyConfig instance to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not self.enable_validation:
            return True, []

        try:
            # Validate SSL configuration
            ssl_cert = None
            ssl_key = None

            if config.ssl_cert_path:
                with open(config.ssl_cert_path, 'rb') as f:
                    ssl_cert = f

            if config.ssl_key_path:
                with open(config.ssl_key_path, 'rb') as f:
                    ssl_key = f

            is_valid, validation_errors = self.ssl_validator.validate_site_ssl_configuration(
                protocol=config.protocol,
                auto_ssl=config.auto_ssl,
                support_subdomains=config.support_subdomains,
                host=config.host,
                ssl_certificate=ssl_cert,
                ssl_key=ssl_key,
                ssl_chain=None
            )

            if not is_valid:
                errors.extend(validation_errors)

            # Validate addresses
            # if not config.addresses:
            #     errors.append("No backend addresses configured")

            # for addr in config.addresses:
            #     if 'ip_address' not in addr or 'port' not in addr:
            #         errors.append(f"Invalid address configuration: {addr}")

            # Check DNS challenge requirements
            if config.auto_ssl and config.support_subdomains:
                dns_challenge = self.acme_manager.generate_challenge_instructions(
                    config.host, config.support_subdomains
                )
                if dns_challenge['required']:
                    # Just log - don't block, as DNS may already be configured
                    if self.logger:
                        self.logger.log_certificate_operation(
                            config.host,
                            "dns_challenge_required",
                            dns_challenge
                        )

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors

    def add_site(self, config: CaddyConfig) -> Dict:
        """
        Add a new site with comprehensive validation and logging

        Args:
            config: CaddyConfig instance

        Returns:
            Dictionary with operation result
        """
        start_time = time.time()
        operation_details = {
            "domain": config.host,
            # "addresses": config.addresses,
            "protocol": config.protocol,
            "auto_ssl": config.auto_ssl,
            "support_subdomains": config.support_subdomains
        }

        try:
            if self.logger:
                self.logger.log_site_operation(
                    config.host, "add_site_start", operation_details
                )

            # Validate configuration
            is_valid, validation_errors = self.validate_site_config(config)
            if not is_valid:
                error_msg = "; ".join(validation_errors)
                if self.logger:
                    self.logger.log_error(
                        config.host, "validation_failed", error_msg,
                        {"validation_errors": validation_errors}
                    )
                return {
                    "success": False,
                    "error": "Configuration validation failed",
                    "validation_errors": validation_errors
                }

            # Determine SSL strategy
            ssl_strategy = self._determine_ssl_strategy(config)
            operation_details["ssl_strategy"] = ssl_strategy

            # Apply SSL strategy
            self._apply_ssl_strategy(config, ssl_strategy)

            # Generate configuration
            old_config = self._get_existing_config(config.host)
            new_config = self._generate_site_config(config)

            # Write to file
            site_file = self.sites_dir / f"{config.host}.caddy"
            with open(site_file, 'w') as f:
                f.write(new_config)

            # Log configuration change
            if self.logger:
                self.logger.log_configuration_change(
                    config.host, old_config, new_config, True
                )

            # Reload Caddy
            reload_success, reload_output = self._reload_caddy()
            operation_details["reload_success"] = reload_success

            duration = time.time() - start_time
            operation_details["duration"] = duration

            if reload_success:
                # Check if DNS challenge is needed
                dns_challenge_info = None
                if config.auto_ssl and config.support_subdomains:
                    dns_challenge_info = self.acme_manager.generate_challenge_instructions(
                        config.host, config.support_subdomains
                    )

                result = {
                    "success": True,
                    "ssl_strategy": ssl_strategy,
                    "duration": duration,
                    "config_file": str(site_file),
                    "dns_challenge": dns_challenge_info
                }

                if self.logger:
                    self.logger.log_site_operation(
                        config.host, "add_site_complete", operation_details, True
                    )
                    self.logger.main_logger.info("##############################")
                    self.logger.main_logger.info(f"# CADDY ADD SITE COMPLETE: {config.host}")
                    self.logger.main_logger.info("##############################")

                return result
            else:
                result = {
                    "success": False,
                    "error": "Caddy reload failed",
                    "reload_output": reload_output
                }

                if self.logger:
                    self.logger.log_error(
                        config.host, "caddy_reload",
                        "Failed to reload Caddy after adding site",
                        {"reload_output": reload_output}
                    )
                    self.logger.main_logger.error("##############################")
                    self.logger.main_logger.error(f"# CADDY ADD SITE FAILED: {config.host}")
                    self.logger.main_logger.error("##############################")

                return result

        except Exception as e:
            duration = time.time() - start_time
            error_details = {
                "error": str(e),
                "duration": duration,
                "operation_details": operation_details
            }

            if self.logger:
                self.logger.log_error(
                    config.host, "add_site_failed", str(e), error_details
                )
                self.logger.main_logger.error("##############################")
                self.logger.main_logger.error(f"# CADDY ADD SITE ERROR: {config.host}")
                self.logger.main_logger.error(f"# ERROR: {str(e)}")
                self.logger.main_logger.error("##############################")

            return {
                "success": False,
                "error": str(e),
                "duration": duration
            }

    def remove_site(self, domain: str) -> Dict:
        """
        Remove a site with comprehensive cleanup and logging

        Args:
            domain: Domain name to remove

        Returns:
            Dictionary with operation result
        """
        start_time = time.time()

        try:
            if self.logger:
                self.logger.log_site_operation(
                    domain, "remove_site_start", {"domain": domain}
                )

            # Get existing configuration for logging
            old_config = self._get_existing_config(domain)

            # Remove site file
            site_file = self.sites_dir / f"{domain}.caddy"
            if site_file.exists():
                site_file.unlink()

            # Remove certificate directory
            cert_dir = self.certs_dir / domain
            if cert_dir.exists():
                shutil.rmtree(cert_dir)

            # Log configuration change
            if self.logger and old_config:
                self.logger.log_configuration_change(
                    domain, old_config, "", True
                )

            # Reload Caddy
            reload_success, reload_output = self._reload_caddy()

            duration = time.time() - start_time
            operation_details = {
                "domain": domain,
                "files_removed": [str(site_file), str(cert_dir)],
                "reload_success": reload_success,
                "duration": duration
            }

            if reload_success:
                if self.logger:
                    self.logger.log_site_operation(
                        domain, "remove_site_complete", operation_details, True
                    )
                    self.logger.main_logger.info("##############################")
                    self.logger.main_logger.info(f"# CADDY REMOVE SITE COMPLETE: {domain}")
                    self.logger.main_logger.info("##############################")

                return {
                    "success": True,
                    "duration": duration,
                    "files_removed": [str(site_file), str(cert_dir)]
                }
            else:
                if self.logger:
                    self.logger.log_error(
                        domain, "caddy_reload",
                        "Failed to reload Caddy after removing site",
                        {"reload_output": reload_output}
                    )
                    self.logger.main_logger.error("##############################")
                    self.logger.main_logger.error(f"# CADDY REMOVE SITE FAILED: {domain}")
                    self.logger.main_logger.error("##############################")

                return {
                    "success": False,
                    "error": "Caddy reload failed",
                    "reload_output": reload_output
                }

        except Exception as e:
            duration = time.time() - start_time

            if self.logger:
                self.logger.log_error(
                    domain, "remove_site_failed", str(e),
                    {"duration": duration}
                )
                self.logger.main_logger.error("##############################")
                self.logger.main_logger.error(f"# CADDY REMOVE SITE ERROR: {domain}")
                self.logger.main_logger.error(f"# ERROR: {str(e)}")
                self.logger.main_logger.error("##############################")

            return {
                "success": False,
                "error": str(e),
                "duration": duration
            }

    def update_site(self, config: CaddyConfig) -> Dict:
        """
        Update existing site configuration

        Args:
            config: New CaddyConfig instance

        Returns:
            Dictionary with operation result
        """
        if self.logger:
            self.logger.log_site_operation(
                config.host, "update_site_start", {"domain": config.host}
            )
            self.logger.main_logger.info("##############################")
            self.logger.main_logger.info(f"# CADDY UPDATE SITE START: {config.host}")
            self.logger.main_logger.info("##############################")

        # For updates, we overwrite the existing configuration
        return self.add_site(config)

    def get_dns_challenge_instructions(self, domain: str, support_subdomains: bool = True) -> Dict:
        """
        Get DNS challenge instructions for a domain

        Args:
            domain: Domain name
            support_subdomains: Whether wildcard certificate is needed

        Returns:
            Dictionary with DNS challenge instructions
        """
        return self.acme_manager.generate_challenge_instructions(domain, support_subdomains)

    def verify_dns_challenge(self, domain: str, expected_value: Optional[str] = None) -> Dict:
        """
        Verify DNS challenge record

        Args:
            domain: Domain name
            expected_value: Expected TXT record value

        Returns:
            Dictionary with verification results
        """
        return self.acme_manager.verify_dns_challenge_record(domain, expected_value)

    def check_dns_propagation(self, domain: str, expected_value: str) -> Dict:
        """
        Check DNS propagation across multiple servers

        Args:
            domain: Domain name
            expected_value: Expected TXT record value

        Returns:
            Dictionary with propagation status
        """
        return self.acme_manager.check_dns_propagation(domain, expected_value)

    def _determine_ssl_strategy(self, config: CaddyConfig) -> Dict:
        """
        Determine the best SSL strategy for the domain

        Args:
            config: CaddyConfig instance

        Returns:
            Dictionary describing SSL strategy
        """
        strategy = {"type": "auto", "reason": "fallback"}

        # If protocol is HTTP, no SSL needed
        if config.protocol == 'http':
            return {"type": "none", "reason": "HTTP protocol"}

        try:
            # If manual certificates provided in config
            if config.ssl_cert_path and config.ssl_key_path:
                # Validate the certificates
                cert_info = self.cert_checker.check_certificate_domains(config.ssl_cert_path)

                if 'error' not in cert_info:
                    # Check domain coverage
                    coverage = self.cert_checker.check_domain_coverage(
                        config.host, config.ssl_cert_path
                    )

                    if coverage.get('matches'):
                        strategy = {
                            "type": "manual",
                            "cert_path": config.ssl_cert_path,
                            "key_path": config.ssl_key_path,
                            "reason": "manual certificates provided and valid",
                            "cert_info": cert_info,
                            "has_wildcard": cert_info.get('has_wildcard', False)
                        }

                        if self.logger:
                            self.logger.log_certificate_operation(
                                config.host, "manual_cert_validated", cert_info
                            )
                        return strategy



            # Default to auto SSL (Let's Encrypt)
            ssl_type = "auto_wildcard" if config.support_subdomains else "auto_single"
            strategy = {
                "type": ssl_type,
                "reason": "no valid certificates found, using Let's Encrypt",
                "requires_dns_challenge": config.support_subdomains
            }

            if self.logger:
                self.logger.log_certificate_operation(
                    config.host, "auto_ssl_selected", strategy
                )

        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    config.host, "ssl_strategy_detection", str(e)
                )

        return strategy

    def _apply_ssl_strategy(self, config: CaddyConfig, strategy: Dict):
        """
        Apply SSL strategy to configuration

        Args:
            config: CaddyConfig instance to modify
            strategy: SSL strategy dictionary
        """
        strategy_type = strategy.get("type", "auto")

        if strategy_type in ["manual"]:
            config.ssl_cert_path = strategy["cert_path"]
            config.ssl_key_path = strategy["key_path"]
            config.auto_ssl = False
        elif strategy_type in ["auto_single","auto_wildcard"]:
            config.auto_ssl = True
        elif strategy_type == "none":
            config.auto_ssl = False
            config.ssl_cert_path = None
            config.ssl_key_path = None

    def _get_parent_domain(self, domain: str) -> str:
        """
        Get parent domain for subdomain

        Args:
            domain: Full domain name

        Returns:
            Parent domain
        """
        parts = domain.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return domain

    def _get_existing_config(self, domain: str) -> Optional[str]:
        """
        Get existing configuration for a domain

        Args:
            domain: Domain name

        Returns:
            Configuration content or None
        """
        site_file = self.sites_dir / f"{domain}.caddy"
        if site_file.exists():
            try:
                with open(site_file, 'r') as f:
                    return f.read()
            except Exception:
                pass
        return None

    def _generate_site_config(self, config: CaddyConfig) -> str:
        """
        Generate Caddyfile configuration for a site

        Args:
            config: CaddyConfig instance

        Returns:
            Caddyfile configuration string
        """
        lines = [
            f"# Configuration for {config.host}",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Protocol: {config.protocol}, Auto SSL: {config.auto_ssl}, Subdomains: {config.support_subdomains}",
            ""
        ]

        # Site block with optional wildcard
        if config.support_subdomains:
            lines.append(f"{config.host}, *.{config.host} {{")
        else:
            lines.append(f"{config.host} {{")

        # HTTPS redirect for HTTPS sites
        if config.auto_https_redirect and config.protocol == 'https':
            lines.extend([
                "",
                "    # HTTPS redirect",
                "    @http {",
                "        protocol http",
                "    }",
                "    redir @http https://{host}{uri} permanent"
            ])

        # Request size limit
        lines.extend([
            "",
            "    # Request size limit",
            "    request_body {{",
            f"        max_size {config.max_request_body_size}",
            "    }"
        ])

        # Reverse proxy configuration
        lines.append("")
        # if len(config.addresses) == 1:
        #     addr = config.addresses[0]
        #     lines.extend([
        #         "    # Single upstream",
        #         f"    reverse_proxy {addr['ip_address']}:{addr['port']} {{"
        #     ])
        # else:
        #     lines.extend([
        #         "    # Load balanced upstreams",
        #         f"    reverse_proxy {{"
        #     ])

        #     # Add load balancing policy
        #     lines.append(f"        lb_policy {config.load_balancer_algorithm}")

            # Add upstream servers

        lines.append("reverse_proxy 127.0.0.1:8000")

        # Health checks
        # lines.extend([
        #     "",
        #     "        # Health checks",
        #     f"        health_uri {config.health_check_path}",
        #     f"        health_interval {config.health_check_interval}",
        #     f"        health_timeout {config.health_check_timeout}"
        # ])

        # Trusted proxies
        # if config.trusted_proxies:
        #     lines.append("")
        #     lines.append("        # Trusted proxies")
        #     for proxy in config.trusted_proxies:
        #         lines.append(f"        trusted_proxies {proxy}")

        # Header pass-through
        lines.extend([
            "",
            "        # Header pass-through",
            "        header_up Host {upstream_hostport}",
            "        header_up X-Real-IP {remote_host}",
            "        header_up X-Forwarded-For {remote_host}",
            "        header_up X-Forwarded-Proto {scheme}"
        ])

        lines.append("    }")

        # SSL/TLS configuration
        lines.append("")
        if config.protocol == 'https':
            if config.ssl_cert_path and config.ssl_key_path:
                lines.extend([
                    "    # Manual SSL certificate",
                    f"    tls {config.ssl_cert_path} {config.ssl_key_path}"
                ])
                if config.ssl_chain_path:
                    lines.append(f"    # Chain: {config.ssl_chain_path}")
            elif config.auto_ssl:
                    lines.extend([
                        "    # Automatic SSL (Let's Encrypt)",
                    ])
            else:
                lines.append("    # No SSL configured")
        else:
            lines.append("    # HTTP protocol - no TLS")

        # Security headers for HTTPS
        if config.protocol == 'https':
            lines.extend([
                "",
                "    # Security headers",
                "    header {",
                "        Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\"",
                "        X-Content-Type-Options \"nosniff\"",
                "        X-Frame-Options \"SAMEORIGIN\"",
                "        Referrer-Policy \"strict-origin-when-cross-origin\"",
                "    }"
            ])

        lines.append("}")
        lines.append("")  # Empty line at end

        return '\n'.join(lines)

    def _reload_caddy(self) -> Tuple[bool, str]:
        """
        Reload Caddy configuration and log the operation

        Returns:
            Tuple of (success, output_message)
        """
        start_time = time.time()

        try:
            # Try file-based reload first
            result = subprocess.run(
                ['caddy', 'reload', '--config', str(self.main_caddyfile)],
                capture_output=True,
                text=True,
                timeout=30
            )

            duration = time.time() - start_time
            success = result.returncode == 0
            output = result.stdout + result.stderr

            if self.logger:
                self.logger.log_reload(success, duration, output)

            if success:
                return True, output
            else:
                # Try API reload as fallback
                response = requests.post(f"{self.api_url}/load", timeout=10)
                api_success = response.status_code == 200

                if self.logger:
                    self.logger.log_reload(
                        api_success,
                        time.time() - start_time,
                        f"File reload failed, API reload: {response.status_code}"
                    )

                return api_success, f"File reload failed: {output}\nAPI reload: {response.status_code}"

        except subprocess.TimeoutExpired:
            if self.logger:
                self.logger.log_reload(False, time.time() - start_time, "Reload timeout")
            return False, "Reload timeout"
        except Exception as e:
            if self.logger:
                self.logger.log_reload(False, time.time() - start_time, str(e))
            return False, str(e)

    def get_site_status(self, domain: str) -> Dict:
        """
        Get comprehensive status for a site

        Args:
            domain: Domain name

        Returns:
            Dictionary with site status
        """
        status = {
            "domain": domain,
            "config_exists": False,
            "certificates": {},
            "ssl_strategy": {},
            "dns_challenge": {},
            "last_operations": [],
            "errors": []
        }

        # Check configuration file
        site_file = self.sites_dir / f"{domain}.caddy"
        status["config_exists"] = site_file.exists()

        if site_file.exists():
            status["config_file"] = str(site_file)
            status["config_modified"] = datetime.fromtimestamp(
                site_file.stat().st_mtime
            ).isoformat()

        # Check certificates
        cert_dir = self.certs_dir / domain
        if cert_dir.exists():
            for cert_file in cert_dir.glob("*.pem"):
                try:
                    cert_info = self.cert_checker.check_certificate_domains(str(cert_file))

                    # Get validation details
                    is_valid, message, details = self.cert_checker.validate_certificate(str(cert_file))
                    cert_info['is_valid'] = is_valid
                    cert_info['validation_message'] = message
                    cert_info['days_until_expiry'] = details.get('days_until_expiry', 0)

                    status["certificates"][cert_file.name] = cert_info
                except Exception as e:
                    status["certificates"][cert_file.name] = {"error": str(e)}

        # Get logging information if available
        if self.logger:
            log_status = self.logger.get_site_status(domain)
            status.update(log_status)

        return status

    def validate_configuration(self, domain: str) -> Dict:
        """
        Validate configuration for a specific domain

        Args:
            domain: Domain name

        Returns:
            Dictionary with validation results
        """
        validation = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "certificate_status": {},
            "dns_status": {}
        }

        try:
            # Check if configuration exists
            site_file = self.sites_dir / f"{domain}.caddy"
            if not site_file.exists():
                validation["errors"].append("Configuration file does not exist")
                return validation

            # Validate Caddy syntax
            result = subprocess.run(
                ['caddy', 'validate', '--config', str(site_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                validation["errors"].append(f"Caddy validation failed: {result.stderr}")

            # Validate certificates if present
            cert_dir = self.certs_dir / domain
            if cert_dir.exists():
                for cert_file in cert_dir.glob("*.pem"):
                    try:
                        coverage = self.cert_checker.check_domain_coverage(
                            domain, str(cert_file)
                        )
                        validation["certificate_status"][cert_file.name] = coverage

                        if not coverage.get('matches'):
                            validation["warnings"].append(
                                f"Certificate {cert_file.name} does not cover domain {domain}"
                            )

                        # Check expiration
                        is_valid, message, details = self.cert_checker.validate_certificate(str(cert_file))
                        days_until_expiry = details.get('days_until_expiry', 0)

                        if days_until_expiry < 0:
                            validation["errors"].append(f"Certificate {cert_file.name} has expired")
                        elif days_until_expiry < 7:
                            validation["warnings"].append(
                                f"Certificate {cert_file.name} expires in {days_until_expiry} days"
                            )
                    except Exception as e:
                        validation["errors"].append(f"Certificate validation error: {str(e)}")

            validation["valid"] = len(validation["errors"]) == 0

        except Exception as e:
            validation["errors"].append(f"Validation error: {str(e)}")

        return validation


    def list_sites(self) -> List[Dict]:
        """
        List all managed sites with their status

        Returns:
            List of site status dictionaries
        """
        sites = []

        for site_file in self.sites_dir.glob("*.caddy"):
            domain = site_file.stem
            status = self.get_site_status(domain)
            sites.append(status)

        return sites

    def cleanup_logs(self, days: int = 30) -> Dict:
        """
        Cleanup old logs and return cleanup summary

        Args:
            days: Number of days to keep logs

        Returns:
            Dictionary with cleanup summary
        """
        if not self.logger:
            return {"error": "Logging not enabled"}

        cleaned_count = self.logger.cleanup_old_logs(days)

        return {
            "success": True,
            "cleaned_files": cleaned_count,
            "cutoff_days": days
        }

    def export_site_logs(self, domain: str, output_file: str) -> Dict:
        """
        Export logs for a specific site

        Args:
            domain: Domain name
            output_file: Output file path

        Returns:
            Dictionary with export result
        """
        if not self.logger:
            return {"error": "Logging not enabled"}

        try:
            success = self.logger.export_site_logs(domain, output_file)

            return {
                "success": success,
                "output_file": output_file,
                "domain": domain
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
