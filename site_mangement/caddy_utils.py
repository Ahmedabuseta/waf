"""
Utility functions for Caddy integration
"""
from .caddy_manager import CaddyManager, CaddyConfig
from .models import Site
import logging
import os

logger = logging.getLogger(__name__)

DEV_HOST_SUFFIXES = ('.local',)
DEV_HOSTS = {'localhost', '127.0.0.1', 'test.lock', 'test.lockdd'}


def is_dev_environment(site: Site) -> bool:
    env = os.environ.get('WAF_ENV') or getattr(__import__('waf_app.settings', fromlist=['settings']), 'settings', None)
    env_name = getattr(env, 'WAF_ENV', None)
    host = site.host.lower()
    if env_name == 'dev':
        return True
    if host in DEV_HOSTS or host.endswith(DEV_HOST_SUFFIXES):
        return True
    return False


def _get_fixed_upstream_from_env():
    """Return a single fixed upstream from env if defined, else None.
    Environment variables:
      - WAF_FIXED_UPSTREAM_IP (e.g., 192.168.1.10)
      - WAF_FIXED_UPSTREAM_PORT (default: 8000)
    """
    # ip = os.environ.get('WAF_FIXED_UPSTREAM_IP')
    ip = '127.0.0.1'
    if not ip:
        return None
    # port = os.environ.get('WAF_FIXED_UPSTREAM_PORT', '8000')
    port = '8000'
    try:
        port = int(port)
    except ValueError:
        port = 8000
    return {'ip_address': ip, 'port': port, 'is_allowed': True}


def sync_site_to_caddy(site: Site) -> bool:
    """
    Sync a site to Caddy server
    """
    try:
        caddy = CaddyManager()
        if not caddy.check_connection():
            logger.warning(f"Caddy not accessible - cannot sync site {site.host}")
            return False

        # Prefer a single fixed upstream from env if provided
        fixed = _get_fixed_upstream_from_env()
        addresses = []
        if fixed:
            addresses = [fixed]
            logger.info("Caddy sync using fixed upstream ip=%s port=%s", fixed['ip_address'], fixed['port'])
        else:
            # Build from DB addresses (allowed only)
            for addr in site.addresses.all():
                if addr.is_allowed:
                    addresses.append({
                        'ip_address': addr.ip_address,
                        'port': addr.port,
                        'is_allowed': True,
                    })
            logger.info("Caddy sync using %d upstream(s) from DB for host=%s", len(addresses), site.host)

        if not addresses:
            logger.warning(f"Site {site.host} has no allowed addresses - skipping Caddy sync")
            return False

        # Dev heuristics
        dev = is_dev_environment(site)
        protocol = 'http' if dev else site.protocol
        auto_ssl = False if dev else site.auto_ssl
        if dev:
            logger.info("Dev profile active for host=%s: forcing protocol=http, auto_ssl=False, disable HTTPS redirect", site.host)

        config = CaddyConfig(
            host=site.host,
            addresses=addresses,
            protocol=protocol,
            auto_ssl=auto_ssl,
            ssl_cert_path=site.ssl_certificate.path if (site.ssl_certificate and not dev) else None,
            ssl_key_path=site.ssl_key.path if (site.ssl_key and not dev) else None,
            ssl_chain_path=site.ssl_chain.path if (site.ssl_chain and not dev) else None,
            load_balancer_algorithm=(site.load_balancer.algorithm if hasattr(site, 'load_balancer') and site.load_balancer else None),
            auto_https_redirect=not dev,
        )

        # Check if site already exists in Caddy
        try:
            status = caddy.get_site_status(site.host)
        except Exception as e:
            logger.warning("Could not query Caddy site status for %s: %s", site.host, e)
            status = {"exists": False}

        exists = bool(status.get("exists"))
        logger.info("Caddy site status host=%s exists=%s", site.host, exists)

        # Update if exists, otherwise add
        if exists:
            result = caddy.update_site(config)
            action = 'update'
        else:
            result = caddy.add_site(config)
            action = 'add'

        if result:
            logger.info("Caddy %s successful for host=%s (dev=%s)", action, site.host, dev)
            return True
        logger.error("Caddy %s failed for host=%s", action, site.host)
        return False
    except Exception as e:
        logger.error(f"Error syncing site {site.host} to Caddy: {str(e)}")
        return False


def remove_site_from_caddy(site: Site) -> bool:
    """
    Remove a site from Caddy server
    
    Args:
        site: Site object to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        caddy = CaddyManager()
        
        # Check if Caddy is accessible
        if not caddy.check_connection():
            logger.warning(f"Caddy not accessible - cannot remove site {site.host}")
            return False
        
        # Remove the site
        result = caddy.remove_site(site.host)
        
        if result:
            logger.info(f"Successfully removed site {site.host} from Caddy")
            return True
        else:
            logger.error(f"Failed to remove site {site.host} from Caddy")
            return False
            
    except Exception as e:
        logger.error(f"Error removing site {site.host} from Caddy: {str(e)}")
        return False


def sync_all_sites_to_caddy() -> dict:
    """
    Sync all active sites to Caddy
    
    Returns:
        dict: Results with success/failure counts
    """
    results = {
        'synced': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    for site in Site.objects.filter(status='active'):
        if sync_site_to_caddy(site):
            results['synced'] += 1
        else:
            results['failed'] += 1
    
    return results

