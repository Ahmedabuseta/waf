"""
Caddy API Manager for dynamic site configuration
"""
import requests
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import subprocess
from datetime import datetime
from .utils.certificate_checker import CertificateChecker


@dataclass
class CaddyConfig:
    """Caddy configuration for a site"""
    host: str
    addresses: List[Dict[str, Any]]
    protocol: str
    auto_ssl: bool
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_chain_path: Optional[str] = None
    load_balancer_algorithm: Optional[str] = None
    auto_https_redirect: bool = True


class CaddyAPIError(Exception):
    """Custom exception for Caddy API errors"""
    pass


class CaddyManager:
    """Manager for Caddy API operations"""

    def __init__(self, api_url: str = "http://localhost:2019"):
        self.api_url = api_url.rstrip('/')
        self.config_endpoint = f"{self.api_url}/config"
        self.load_endpoint = f"{self.api_url}/load"
        # Optional persistence path (JSON file) to store last applied config
        # Prefer Django settings if available, fallback to env var or default
        try:
            from django.conf import settings  # type: ignore
            self.persist_path = getattr(settings, 'CADDY_PERSIST_PATH', os.environ.get('CADDY_PERSIST_PATH', '/etc/caddy/managed_config.json'))
        except Exception:
            self.persist_path = os.environ.get('CADDY_PERSIST_PATH', '/etc/caddy/managed_config.json')

        # Initialize certificate checker
        self.cert_checker = CertificateChecker()

    def check_connection(self) -> bool:
        """Check if Caddy API is accessible"""
        try:
            response = requests.get(f"{self.api_url}/config/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_current_config(self) -> Dict:
        """Get current Caddy configuration"""
        try:
            response = requests.get(self.config_endpoint)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise CaddyAPIError(f"Failed to get config: {str(e)}")

    def create_site_config(self, config: CaddyConfig) -> Dict:
        """Create Caddy configuration for a site"""

        # Build upstream targets
        upstreams = []
        for addr in config.addresses:
            if addr.get('is_allowed', True):  # Only use allowed addresses
                upstreams.append({
                    "dial": f"{addr['ip_address']}:{addr['port']}"
                })

        if not upstreams:
            raise CaddyAPIError("No valid upstream addresses configured")

        # Base server configuration
        site_config = {
            "match": [{"host": [config.host]}],
            "handle": []
        }

        # Add HTTPS redirect if enabled and using HTTP
        if config.auto_https_redirect and config.protocol == 'http':
            site_config["handle"].append({
                "@id": "https_redirect",
                "handler": "static_response",
                "status_code": 301,
                "headers": {
                    "Location": [f"https://{config.host}{{http.request.uri}}"]
                }
            })

        # Add reverse proxy handler
        reverse_proxy_handler = {
            "@id": "reverse_proxy",
            "handler": "reverse_proxy",
            "upstreams": upstreams
        }

        # Add load balancing if multiple upstreams
        if len(upstreams) > 1 and config.load_balancer_algorithm:
            lb_policy = self._get_lb_policy(config.load_balancer_algorithm)
            reverse_proxy_handler["load_balancing"] = lb_policy

            # Add health checks
            reverse_proxy_handler["health_checks"] = {
                "active": {
                    "interval": "30s",
                    "timeout": "5s"
                }
            }

        site_config["handle"].append(reverse_proxy_handler)

        # TLS configuration
        tls_config = self._build_tls_config(config)

        return {
            "routes": [site_config],
            "tls": tls_config
        }

    def _get_lb_policy(self, algorithm: str) -> Dict:
        """Get load balancing policy configuration"""
        policies = {
            'round_robin': {"policy": "round_robin"},
            'least_connections': {"policy": "least_conn"},
            'ip_hash': {"policy": "ip_hash"}
        }
        return policies.get(algorithm, policies['round_robin'])

    def _build_tls_config(self, config: CaddyConfig) -> Dict:
        """Build TLS configuration"""
        tls_config = {}

        # if config.auto_ssl:
        #     # Use automatic HTTPS with Let's Encrypt
        #     tls_config = {
        #         "automation": {
        #             "policies": [{
        #                 "subjects": [config.host],
        #                 "issuers": [{
        #                     "module": "acme"
        #                 }]
        #             }]
        #         }
        #     }
        # elif config.ssl_cert_path and config.ssl_key_path:
        #     # Use provided SSL certificates
        #     tls_config = {
        #         "certificates": {
        #             "load_files": [{
        #                 "certificate": config.ssl_cert_path,
        #                 "key": config.ssl_key_path,
        #                 "tags": [config.host]
        #             }]
        #         }
        #     }

        #     # Add chain if provided
        #     if config.ssl_chain_path:
        #         tls_config["certificates"]["load_files"][0]["chain"] = config.ssl_chain_path

        return tls_config

    def add_site(self, config: CaddyConfig) -> bool:
        """Add a new site to Caddy"""
        try:
            current_config = self.get_current_config()
            site_config = self.create_site_config(config)

            # Initialize apps if not exist
            if "apps" not in current_config:
                current_config["apps"] = {}

            if "http" not in current_config["apps"]:
                current_config["apps"]["http"] = {"servers": {}}

            if "servers" not in current_config["apps"]["http"]:
                current_config["apps"]["http"]["servers"] = {}

            # Add site to a shared server to avoid duplicate listener conflicts
            # Use one server for HTTP and one for HTTPS
            server_name = "srv_tls" if config.protocol == 'https' else "srv0"

            if server_name not in current_config["apps"]["http"]["servers"]:
                current_config["apps"]["http"]["servers"][server_name] = {
                    "listen": [f":{443 if config.protocol == 'https' else 80}"],
                    "routes": []
                }

            # Add routes
            current_config["apps"]["http"]["servers"][server_name]["routes"].extend(
                site_config["routes"]
            )

            # Update TLS config only once in shared app scope
            if site_config.get("tls"):
                if "tls" not in current_config["apps"]:
                    current_config["apps"]["tls"] = {}

                if "automation" in site_config["tls"]:
                    if "automation" not in current_config["apps"]["tls"]:
                        current_config["apps"]["tls"]["automation"] = {"policies": []}
                    for pol in site_config["tls"]["automation"]["policies"]:
                        if pol not in current_config["apps"]["tls"]["automation"]["policies"]:
                            current_config["apps"]["tls"]["automation"]["policies"].append(pol)

                if "certificates" in site_config["tls"]:
                    if "certificates" not in current_config["apps"]["tls"]:
                        current_config["apps"]["tls"]["certificates"] = {"load_files": []}
                    for lf in site_config["tls"]["certificates"].get("load_files", []):
                        if lf not in current_config["apps"]["tls"]["certificates"]["load_files"]:
                            current_config["apps"]["tls"]["certificates"]["load_files"].append(lf)

            # Apply configuration
            return self._apply_config(current_config)

        except Exception as e:
            raise CaddyAPIError(f"Failed to add site: {str(e)}")

    def update_site(self, config: CaddyConfig) -> bool:
        """Update existing site configuration"""
        try:
            # Remove old config
            self.remove_site(config.host)
            # Add new config
            return self.add_site(config)
        except Exception as e:
            raise CaddyAPIError(f"Failed to update site: {str(e)}")

    def remove_site(self, host: str) -> bool:
        """Remove a site's routes and TLS for the given host from Caddy."""
        try:
            current_config = self.get_current_config()

            if "apps" not in current_config or "http" not in current_config["apps"]:
                return True  # Nothing to remove

            # Remove routes matching this host across all servers
            if "servers" in current_config["apps"]["http"]:
                for server_name, server_cfg in list(current_config["apps"]["http"]["servers"].items()):
                    routes = server_cfg.get("routes", [])
                    filtered_routes = []
                    for route in routes:
                        matched_host = False
                        for matcher in route.get("match", []):
                            hosts = matcher.get("host") or matcher.get("hosts")
                            if hosts and host in hosts:
                                matched_host = True
                                break
                        if not matched_host:
                            filtered_routes.append(route)
                    server_cfg["routes"] = filtered_routes

            # Remove TLS config for this host
            if "tls" in current_config["apps"]:
                if "automation" in current_config["apps"]["tls"]:
                    policies = current_config["apps"]["tls"]["automation"].get("policies", [])
                    current_config["apps"]["tls"]["automation"]["policies"] = [
                        p for p in policies if host not in p.get("subjects", [])
                    ]

                if "certificates" in current_config["apps"]["tls"]:
                    certs = current_config["apps"]["tls"]["certificates"].get("load_files", [])
                    current_config["apps"]["tls"]["certificates"]["load_files"] = [
                        c for c in certs if host not in c.get("tags", [])
                    ]

            return self._apply_config(current_config)

        except Exception as e:
            raise CaddyAPIError(f"Failed to remove site: {str(e)}")

    def _apply_config(self, config: Dict) -> bool:
        """Apply configuration to Caddy and persist it to disk."""
        try:
            response = requests.post(
                self.load_endpoint,
                json=config,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()

            # Persist to disk for permanence across restarts (best-effort)
            try:
                persist_dir = os.path.dirname(self.persist_path)
                if persist_dir and not os.path.exists(persist_dir):
                    os.makedirs(persist_dir, exist_ok=True)
                tmp_path = f"{self.persist_path}.tmp"
                with open(tmp_path, 'w') as f:
                    json.dump(config, f, indent=2)
                os.replace(tmp_path, self.persist_path)
            except Exception as persist_err:
                # Do not fail the API apply due to persistence error; raise a typed error for logs
                # Consumers can choose to handle/log it
                raise CaddyAPIError(f"Applied to Caddy but failed to persist atomically: {persist_err}")

            return True
        except requests.RequestException as e:
            raise CaddyAPIError(f"Failed to apply config: {str(e)}")

    def reload_config(self) -> bool:
        """Reload Caddy configuration"""
        try:
            response = requests.post(f"{self.api_url}/load")
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            raise CaddyAPIError(f"Failed to reload: {str(e)}")

    def get_site_status(self, host: str) -> Dict:
        """Get status of a specific site"""
        try:
            config = self.get_current_config()
            server_name = f"srv_{host.replace('.', '_')}"

            if "apps" in config and "http" in config["apps"]:
                servers = config["apps"]["http"].get("servers", {})
                if server_name in servers:
                    return {
                        "exists": True,
                        "active": True,
                        "routes": len(servers[server_name].get("routes", [])),
                        "listen": servers[server_name].get("listen", [])
                    }

            return {"exists": False, "active": False}
        except Exception as e:
            raise CaddyAPIError(f"Failed to get site status: {str(e)}")


class SSLValidator:
    """Validator for SSL certificates - wrapper around CertificateChecker for backward compatibility"""

    def __init__(self):
        self.cert_checker = CertificateChecker()

    def validate_certificate(self, cert_path: str) -> Tuple[bool, str, Dict]:
        """
        Validate SSL certificate using CertificateChecker
        Returns: (is_valid, message, details)
        """
        return self.cert_checker.validate_certificate(cert_path)

    def validate_private_key(self, key_path: str) -> Tuple[bool, str]:
        """Validate private key using CertificateChecker"""
        return self.cert_checker.validate_private_key(key_path)

    def validate_certificate_key_match(self, cert_path: str, key_path: str) -> Tuple[bool, str]:
        """Validate that certificate and key match using CertificateChecker"""
        return self.cert_checker.validate_certificate_key_match(cert_path, key_path)

    def get_certificate_info(self, cert_path: str) -> Dict:
        """Get detailed certificate information using CertificateChecker"""
        cert_domains = self.cert_checker.check_certificate_domains(cert_path)
        if "error" in cert_domains:
            return {
                'valid': False,
                'message': cert_domains['error'],
                'details': {}
            }

        is_valid, message, details = self.cert_checker.validate_certificate(cert_path)

        return {
            'valid': is_valid,
            'message': message,
            'details': details,
            'domains': cert_domains
        }

    @staticmethod
    def validate_certificate_static(cert_path: str) -> Tuple[bool, str, Dict]:
        """Static method for backward compatibility"""
        checker = CertificateChecker()
        return checker.validate_certificate(cert_path)

    @staticmethod
    def validate_private_key_static(key_path: str) -> Tuple[bool, str]:
        """Static method for backward compatibility"""
        checker = CertificateChecker()
        return checker.validate_private_key(key_path)

    @staticmethod
    def validate_certificate_key_match_static(cert_path: str, key_path: str) -> Tuple[bool, str]:
        """Static method for backward compatibility"""
        checker = CertificateChecker()
        return checker.validate_certificate_key_match(cert_path, key_path)

    @staticmethod
    def get_certificate_info_static(cert_path: str) -> Dict:
        """Static method for backward compatibility"""
        validator = SSLValidator()
        return validator.get_certificate_info(cert_path)


class SubdomainCaddyManager(CaddyManager):
    """Enhanced Caddy manager with subdomain SSL support and file-based configuration"""

    def __init__(self, api_url: str = "http://localhost:2019", base_path: str = "/etc/caddy"):
        super().__init__(api_url)

        # File paths for permanent configuration
        self.base_path = Path(base_path)
        self.sites_dir = self.base_path / "sites"
        self.certs_dir = self.base_path / "certs"
        self.main_caddyfile = self.base_path / "Caddyfile"

        # Create directories
        self.sites_dir.mkdir(parents=True, exist_ok=True)
        self.certs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize main Caddyfile if it doesn't exist
        self._ensure_main_caddyfile()

    def _ensure_main_caddyfile(self):
        """Ensure main Caddyfile exists with proper import structure"""
        if not self.main_caddyfile.exists():
            main_config = """# Caddy WAF Site Management - Main Configuration
{
    admin localhost:2019
    auto_https off  # Managed per-tenant
}

# Import all tenant configurations
import sites/*.caddy
"""
            with open(self.main_caddyfile, 'w') as f:
                f.write(main_config)

    def add_subdomain_site(self, config: CaddyConfig) -> Dict:
        """Add site with automatic subdomain SSL detection and file-based storage"""
        result = {"success": False, "ssl_type": None, "certificate_used": None}

        try:
            # Determine SSL strategy
            ssl_strategy = self._determine_ssl_strategy(config.host)
            result["ssl_type"] = ssl_strategy["type"]

            if ssl_strategy["type"] == "wildcard":
                # Use existing wildcard certificate
                result["certificate_used"] = ssl_strategy["cert_path"]
                config.ssl_cert_path = ssl_strategy["cert_path"]
                config.ssl_key_path = ssl_strategy["key_path"]

            elif ssl_strategy["type"] == "individual":
                # Use domain-specific certificate
                result["certificate_used"] = ssl_strategy["cert_path"]
                config.ssl_cert_path = ssl_strategy["cert_path"]
                config.ssl_key_path = ssl_strategy["key_path"]

            elif ssl_strategy["type"] == "auto":
                # Let's Encrypt automatic
                config.auto_ssl = True
                result["certificate_used"] = "auto_letsencrypt"

            # Generate configuration and write to file
            config_content = self._generate_subdomain_config(config, ssl_strategy)
            tenant_file = self.sites_dir / f"{config.host}.caddy"

            with open(tenant_file, 'w') as f:
                f.write(config_content)

            # Reload Caddy
            if self._reload_caddy():
                result["success"] = True
                result["config_file"] = str(tenant_file)

        except Exception as e:
            result["error"] = str(e)

        return result

    def remove_site_from_caddyfile(self, host: str) -> bool:
        """Remove site from Caddyfile permanently"""
        try:
            # Remove site file
            site_file = self.sites_dir / f"{host}.caddy"
            if site_file.exists():
                site_file.unlink()

            # Remove certificate directory (optional)
            cert_dir = self.certs_dir / host
            if cert_dir.exists():
                import shutil
                shutil.rmtree(cert_dir)

            # Reload Caddy
            return self._reload_caddy()

        except Exception as e:
            raise CaddyAPIError(f"Failed to remove site from Caddyfile: {str(e)}")

    def _determine_ssl_strategy(self, domain: str) -> Dict:
        """Determine the best SSL strategy for the domain"""
        strategy = {"type": "auto", "reason": "fallback"}

        try:
            # Check for wildcard certificate
            parent_domain = self._get_parent_domain(domain)
            wildcard_cert = self.certs_dir / parent_domain / "wildcard.pem"
            wildcard_key = self.certs_dir / parent_domain / "wildcard.key"

            if wildcard_cert.exists() and wildcard_key.exists():
                match_result = self.cert_checker.domain_matches_certificate(
                    domain, str(wildcard_cert)
                )
                if match_result["matches"] and match_result["type"] == "wildcard":
                    return {
                        "type": "wildcard",
                        "cert_path": str(wildcard_cert),
                        "key_path": str(wildcard_key),
                        "reason": "wildcard certificate found and valid",
                        "cert_info": match_result["cert_info"]
                    }

            # Check for individual domain certificate
            domain_cert = self.certs_dir / domain / "cert.pem"
            domain_key = self.certs_dir / domain / "key.pem"

            if domain_cert.exists() and domain_key.exists():
                match_result = self.cert_checker.domain_matches_certificate(
                    domain, str(domain_cert)
                )
                if match_result["matches"]:
                    return {
                        "type": "individual",
                        "cert_path": str(domain_cert),
                        "key_path": str(domain_key),
                        "reason": "individual certificate found and valid",
                        "cert_info": match_result["cert_info"]
                    }

        except Exception:
            pass

        return strategy

    def _get_parent_domain(self, domain: str) -> str:
        """Get parent domain for subdomain (e.g., sub.example.com -> example.com)"""
        parts = domain.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return domain

    def _generate_subdomain_config(self, config: CaddyConfig, ssl_strategy: Dict) -> str:
        """Generate configuration with subdomain-aware SSL"""
        lines = [f"# Configuration for {config.host}"]
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append(f"# SSL Strategy: {ssl_strategy['type']}")
        lines.append(f"{config.host} {{")

        # HTTPS redirect
        if config.auto_https_redirect:
            lines.extend([
                "    @http {",
                "        protocol http",
                "    }",
                "    redir @http https://{host}{uri} permanent",
                ""
            ])

        # Reverse proxy configuration
        valid_addresses = [addr for addr in config.addresses if addr.get('is_allowed', True)]

        if len(valid_addresses) == 1:
            addr = valid_addresses[0]
            lines.append(f"    reverse_proxy {addr['ip_address']}:{addr['port']}")
        else:
            lines.append("    reverse_proxy {")
            for addr in valid_addresses:
                lines.append(f"        to {addr['ip_address']}:{addr['port']}")

            # Load balancing
            if config.load_balancer_algorithm:
                lb_map = {
                    'round_robin': 'round_robin',
                    'least_connections': 'least_conn',
                    'ip_hash': 'ip_hash'
                }
                lines.append(f"        lb_policy {lb_map.get(config.load_balancer_algorithm, 'round_robin')}")

            lines.append("        health_check /health")
            lines.append("    }")

        # SSL configuration
        lines.append("")
        if ssl_strategy["type"] == "wildcard":
            lines.extend([
                "    # Using wildcard certificate",
                f"    tls {ssl_strategy['cert_path']} {ssl_strategy['key_path']}"
            ])
        elif ssl_strategy["type"] == "individual":
            lines.extend([
                "    # Using domain-specific certificate",
                f"    tls {ssl_strategy['cert_path']} {ssl_strategy['key_path']}"
            ])
        elif ssl_strategy["type"] == "auto":
            lines.extend([
                "    # Using automatic Let's Encrypt",
                "    tls {",
                "        dns cloudflare {env.CLOUDFLARE_API_TOKEN}",
                "    }"
            ])

        lines.append("}")
        lines.append("")  # Empty line at end

        return '\n'.join(lines)

    def _reload_caddy(self) -> bool:
        """Reload Caddy configuration from file"""
        try:
            # Try file-based reload first
            result = subprocess.run(
                ['caddy', 'reload', '--config', str(self.main_caddyfile)],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return True

            # Fallback to API reload
            response = requests.post(f"{self.api_url}/load", timeout=10)
            return response.status_code == 200

        except Exception:
            # Final fallback to parent method
            return super().reload_config()

    def get_site_status_enhanced(self, domain: str) -> Dict:
        """Get enhanced status for a site including file-based info"""
        status = super().get_site_status(domain)

        # Add file-based information
        site_file = self.sites_dir / f"{domain}.caddy"
        status["config_file_exists"] = site_file.exists()

        if site_file.exists():
            status["config_file_path"] = str(site_file)
            status["config_file_modified"] = datetime.fromtimestamp(
                site_file.stat().st_mtime
            ).isoformat()

        # Check certificates
        cert_dir = self.certs_dir / domain
        status["certificates"] = {}

        if cert_dir.exists():
            for cert_file in cert_dir.glob("*.pem"):
                cert_info = self.cert_checker.check_certificate_domains(str(cert_file))
                status["certificates"][cert_file.name] = cert_info

        return status

    def validate_domain_certificate(self, domain: str) -> Dict:
        """Validate if domain has proper certificate coverage"""
        validation = {"valid": False, "certificates": [], "issues": []}

        cert_dir = self.certs_dir / domain
        if not cert_dir.exists():
            validation["issues"].append("No certificate directory found")
            return validation

        cert_files = list(cert_dir.glob("*.pem"))
        if not cert_files:
            validation["issues"].append("No certificate files found")
            return validation

        for cert_file in cert_files:
            cert_validation = self.cert_checker.domain_matches_certificate(
                domain, str(cert_file)
            )

            cert_result = {
                "file": cert_file.name,
                "matches": cert_validation["matches"],
                "type": cert_validation.get("type"),
                "cert_info": cert_validation.get("cert_info", {})
            }

            if not cert_validation["matches"]:
                cert_result["reason"] = cert_validation.get("reason")
                validation["issues"].append(f"{cert_file.name}: {cert_validation.get('reason')}")

            validation["certificates"].append(cert_result)

        # Check if any certificate matches
        validation["valid"] = any(cert["matches"] for cert in validation["certificates"])

        return validation
