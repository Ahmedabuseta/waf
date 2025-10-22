# Wildcard Certificate Generation with acme.sh

This guide explains how to use the CertificateManager's acme.sh integration to generate wildcard certificates for your domains.

## Overview

The `generate_wildcard_certificate_acme` method provides automatic wildcard certificate generation using acme.sh and DNS-01 challenge validation. This creates certificates that cover both the base domain and all its subdomains.

### What You Get

A wildcard certificate for `example.com` will cover:
- `*.example.com` (all subdomains like `www.example.com`, `api.example.com`, etc.)
- `example.com` (the base domain itself)

### Certificate Storage

Certificates are automatically saved to your Caddy certificate directory:
```
/etc/caddy/certs/example.com/
├── cert.pem       # The certificate
├── key.pem        # Private key (600 permissions)
├── chain.pem      # Certificate chain
└── fullchain.pem  # Full certificate chain
```

## Prerequisites

### 1. Install acme.sh

```bash
# Install acme.sh
curl https://get.acme.sh | sh -s email=your-email@example.com

# Note: acme.sh will be installed to ~/.acme.sh/
# The certificate manager automatically uses the full path, so it doesn't need to be in your PATH
```

### 2. DNS Provider Setup

You need API access to your DNS provider for DNS-01 challenge validation.

#### Cloudflare (Recommended)

```bash
# Option 1: API Token (Recommended)
export CF_Token="your_cloudflare_api_token"
export CF_Account_ID="your_cloudflare_account_id"

# Option 2: Global API Key
export CF_Key="your_cloudflare_global_api_key"
export CF_Email="your_cloudflare_email"
```

**How to get Cloudflare API Token:**
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use "Custom token" template
4. Permissions: `Zone:DNS:Edit`, `Zone:Zone:Read`
5. Zone Resources: `Include - All zones` or specific zones
6. Copy the token

#### AWS Route53

```bash
export AWS_ACCESS_KEY_ID="your_aws_access_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
```

#### NameCheap

```bash
export Namecheap_UserName="your_namecheap_username"
export Namecheap_ApiKey="your_namecheap_api_key"
export Namecheap_ClientIP="your_public_ip"  # Your public IP address
```

#### GoDaddy

```bash
export GD_Key="your_godaddy_api_key"
export GD_Secret="your_godaddy_api_secret"
```

#### Other Providers

acme.sh supports 100+ DNS providers. See the [acme.sh DNS API documentation](https://github.com/acmesh-official/acme.sh/wiki/dnsapi) for complete list and setup instructions.

## Usage

### Basic Usage

```bash
# Generate wildcard certificate for example.com
python certificate_manager.py acme-wildcard example.com admin@example.com
```

### Advanced Options

```bash
# Use specific DNS provider
python certificate_manager.py acme-wildcard example.com admin@example.com --dns-provider cloudflare

# Use Let's Encrypt staging environment (for testing)
python certificate_manager.py acme-wildcard example.com admin@example.com --staging

# Force renewal even if valid certificate exists
python certificate_manager.py acme-wildcard example.com admin@example.com --force-renew

# Combine options
python certificate_manager.py acme-wildcard example.com admin@example.com \
  --dns-provider route53 --staging --force-renew
```

### Supported DNS Providers

| Provider | Code | Required Environment Variables |
|----------|------|--------------------------------|
| Cloudflare | `cloudflare` | `CF_Token`, `CF_Account_ID` |
| Route53 | `route53` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| NameCheap | `namecheap` | `Namecheap_UserName`, `Namecheap_ApiKey` |
| GoDaddy | `godaddy` | `GD_Key`, `GD_Secret` |
| DigitalOcean | `digitalocean` | `DO_API_KEY` |
| Linode | `linode` | `LINODE_API_KEY` |
| Vultr | `vultr` | `VULTR_API_KEY` |

## Examples

### Example 1: Cloudflare with Production Certificate

```bash
# Set environment variables
export CF_Token="sdfsdfsdfljlbjkljlkjsdfoiwje"
export CF_Account_ID="cd7d068de3012345da9423ce30a62b72"

# Generate certificate
python certificate_manager.py acme-wildcard example.com admin@example.com --dns-provider cloudflare
```

### Example 2: Route53 with Staging (Testing)

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Generate staging certificate for testing
python certificate_manager.py acme-wildcard test.example.com admin@example.com \
  --dns-provider route53 --staging
```

### Example 3: Force Renewal

```bash
# Force renewal of existing certificate
python certificate_manager.py acme-wildcard example.com admin@example.com \
  --dns-provider cloudflare --force-renew
```

## Verification

After generation, verify your certificate:

```bash
# Check certificate details
python certificate_manager.py check /etc/caddy/certs/example.com/cert.pem --detailed

# Verify domain coverage
python certificate_manager.py domain "*.example.com" /etc/caddy/certs/example.com/cert.pem
python certificate_manager.py domain "example.com" /etc/caddy/certs/example.com/cert.pem

# Validate certificate and key match
python certificate_manager.py validate \
  /etc/caddy/certs/example.com/cert.pem \
  /etc/caddy/certs/example.com/key.pem
```

## Automation and Renewal

### Automatic Renewal Script

Create a renewal script for automation:

```bash
#!/bin/bash
# renew-wildcard-certs.sh

DOMAINS=(
  "example.com"
  "mysite.com"
  "anotherdomain.org"
)

EMAIL="admin@example.com"
DNS_PROVIDER="cloudflare"

for domain in "${DOMAINS[@]}"; do
  echo "Checking certificate for $domain..."
  
  # Check if certificate expires within 30 days
  if python certificate_manager.py check "/etc/caddy/certs/$domain/cert.pem" | grep -q "Expires in.*[0-2][0-9] days"; then
    echo "Certificate for $domain expires soon, renewing..."
    python certificate_manager.py acme-wildcard "$domain" "$EMAIL" \
      --dns-provider "$DNS_PROVIDER" --force-renew
  else
    echo "Certificate for $domain is still valid"
  fi
done

# Reload Caddy to use new certificates
systemctl reload caddy
```

### Cron Job Setup

```bash
# Add to crontab to run weekly
crontab -e

# Add this line to run every Sunday at 3 AM
0 3 * * 0 /path/to/renew-wildcard-certs.sh >> /var/log/cert-renewal.log 2>&1
```

## Troubleshooting

### Common Issues

1. **acme.sh not found**
   ```
   ❌ acme.sh is not installed or not available in PATH
   ```
   Solution: Install acme.sh using `curl https://get.acme.sh | sh`. It will be installed to `~/.acme.sh/` and the certificate manager will automatically detect it.

2. **DNS API credentials not set**
   ```
   ❌ acme.sh failed: DNS API credentials not configured
   ```
   Solution: Set the required environment variables for your DNS provider

3. **DNS validation timeout**
   ```
   ❌ DNS validation failed or timed out
   ```
   Solution: Check DNS provider API limits and ensure credentials are correct

4. **Certificate already exists**
   ```
   ✅ Valid wildcard certificate already exists for example.com
   ```
   Solution: Use `--force-renew` if you want to regenerate anyway

### Debug Mode

For detailed debugging, you can run acme.sh directly:

```bash
# Test DNS API
~/.acme.sh/acme.sh --issue --dns dns_cf -d example.com -d *.example.com --dry-run

# Check acme.sh logs
tail -f ~/.acme.sh/acme.sh.log
```

### DNS Provider Specific Issues

#### Cloudflare
- Ensure API token has correct permissions
- Verify Account ID is correct
- Check token hasn't expired

#### Route53
- Ensure AWS credentials have Route53 permissions
- Verify the hosted zone exists
- Check AWS region configuration

#### NameCheap
- Enable API access in NameCheap dashboard
- Whitelist your IP address
- Use your NameCheap username, not email

## Security Considerations

1. **Environment Variables**: Store API credentials securely
   ```bash
   # Use a secure file for environment variables
   echo 'export CF_Token="your_token"' >> ~/.acme_credentials
   chmod 600 ~/.acme_credentials
   source ~/.acme_credentials
   ```

2. **File Permissions**: Private keys are automatically set to 600
   ```bash
   ls -la /etc/caddy/certs/example.com/
   # key.pem should show: -rw------- (600)
   ```

3. **Staging Environment**: Always test with staging first
   ```bash
   # Test with staging environment
   python certificate_manager.py acme-wildcard example.com admin@example.com --staging
   ```

## Integration with Caddy

Once certificates are generated, configure Caddy to use them:

```caddy
# Caddyfile
*.example.com {
    tls /etc/caddy/certs/example.com/cert.pem /etc/caddy/certs/example.com/key.pem
    
    # Your site configuration
    reverse_proxy localhost:8080
}

example.com {
    tls /etc/caddy/certs/example.com/cert.pem /etc/caddy/certs/example.com/key.pem
    
    # Your site configuration
    reverse_proxy localhost:8080
}
```

## Best Practices

1. **Use staging first**: Always test with `--staging` before production
2. **Monitor expiration**: Set up automated renewal
3. **Backup certificates**: Include certificates in your backup strategy
4. **Secure credentials**: Use secure methods to store API credentials
5. **Log operations**: Monitor certificate generation and renewal logs
6. **Test coverage**: Verify certificates cover all needed domains

## Support

For issues with:
- **acme.sh**: Check [acme.sh documentation](https://github.com/acmesh-official/acme.sh)
- **DNS providers**: Check provider-specific API documentation
- **Certificate Manager**: Check the logs and verify configuration

## References

- [acme.sh GitHub Repository](https://github.com/acmesh-official/acme.sh)
- [acme.sh DNS API List](https://github.com/acmesh-official/acme.sh/wiki/dnsapi)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Caddy TLS Documentation](https://caddyserver.com/docs/caddyfile/directives/tls)