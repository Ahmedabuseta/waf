#!/bin/bash
################################################################################
# SSL Certificate Chain Validation Script
#
# This script demonstrates how to validate SSL certificate chains using the
# certificate manager utility before deploying to production.
#
# Usage: ./validate_ssl_chain.sh <cert.pem> <key.pem> <chain.pem> <domain>
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERT_MANAGER="$PROJECT_ROOT/site_mangement/utils/certificate_manager.py"

# Check if certificate manager exists
if [ ! -f "$CERT_MANAGER" ]; then
    echo -e "${RED}❌ Certificate manager not found at: $CERT_MANAGER${NC}"
    exit 1
fi

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check arguments
if [ $# -lt 3 ]; then
    echo "Usage: $0 <cert.pem> <key.pem> <chain.pem> [domain]"
    echo ""
    echo "Examples:"
    echo "  $0 cert.pem key.pem chain.pem example.com"
    echo "  $0 /path/to/fullchain.pem /path/to/privkey.pem /path/to/chain.pem"
    exit 1
fi

CERT_FILE="$1"
KEY_FILE="$2"
CHAIN_FILE="$3"
DOMAIN="${4:-}"

# Validate input files exist
print_section "Pre-flight Checks"

if [ ! -f "$CERT_FILE" ]; then
    print_error "Certificate file not found: $CERT_FILE"
    exit 1
fi
print_success "Certificate file found: $CERT_FILE"

if [ ! -f "$KEY_FILE" ]; then
    print_error "Private key file not found: $KEY_FILE"
    exit 1
fi
print_success "Private key file found: $KEY_FILE"

if [ ! -f "$CHAIN_FILE" ]; then
    print_error "Chain file not found: $CHAIN_FILE"
    exit 1
fi
print_success "Chain file found: $CHAIN_FILE"

# Check OpenSSL availability
if ! command -v openssl &> /dev/null; then
    print_error "OpenSSL not found in PATH"
    exit 1
fi
print_success "OpenSSL is available"

################################################################################
# Step 1: Validate Certificate Chain
################################################################################
print_section "Step 1: Validating Certificate Chain"

print_info "Checking certificate chain integrity..."
if python3 "$CERT_MANAGER" check-chain "$CERT_FILE" --chain "$CHAIN_FILE"; then
    print_success "Certificate chain validation passed"
else
    print_error "Certificate chain validation failed"
    print_warning "Common issues:"
    echo "  - Missing intermediate certificates"
    echo "  - Incorrect chain order"
    echo "  - Expired certificates"
    echo "  - Untrusted CA"
    exit 1
fi

################################################################################
# Step 2: Validate Certificate Details
################################################################################
print_section "Step 2: Certificate Details"

print_info "Retrieving certificate information..."
python3 "$CERT_MANAGER" check "$CERT_FILE" --detailed

################################################################################
# Step 3: Validate Private Key
################################################################################
print_section "Step 3: Validating Private Key"

print_info "Checking if private key is valid..."
if openssl pkey -in "$KEY_FILE" -check -noout &> /dev/null; then
    print_success "Private key is valid"
else
    print_error "Private key validation failed"
    exit 1
fi

################################################################################
# Step 4: Validate Certificate-Key Match
################################################################################
print_section "Step 4: Certificate-Key Match Verification"

print_info "Verifying certificate and private key match..."
if python3 "$CERT_MANAGER" validate "$CERT_FILE" "$KEY_FILE"; then
    print_success "Certificate and private key match perfectly"
else
    print_error "Certificate and private key do not match"
    print_warning "Make sure you're using the correct key for this certificate"
    exit 1
fi

################################################################################
# Step 5: Domain Coverage Check (if domain provided)
################################################################################
if [ -n "$DOMAIN" ]; then
    print_section "Step 5: Domain Coverage Verification"

    print_info "Checking if certificate covers domain: $DOMAIN"
    if python3 "$CERT_MANAGER" domain "$DOMAIN" "$CERT_FILE"; then
        print_success "Certificate covers domain: $DOMAIN"
    else
        print_error "Certificate does not cover domain: $DOMAIN"
        print_warning "The certificate may cover different domains or use wildcards"
        exit 1
    fi
fi

################################################################################
# Step 6: Check Remote Certificate (if domain provided)
################################################################################
if [ -n "$DOMAIN" ]; then
    print_section "Step 6: Remote Certificate Check (Optional)"

    print_info "Checking currently deployed certificate on $DOMAIN..."
    if python3 "$CERT_MANAGER" remote "$DOMAIN" 2>/dev/null; then
        print_success "Remote certificate retrieved successfully"
        print_warning "Compare the remote certificate with your new certificate"
    else
        print_warning "Could not retrieve remote certificate (domain may not be deployed yet)"
    fi
fi

################################################################################
# Step 7: Chain Analysis
################################################################################
print_section "Step 7: Certificate Chain Analysis"

print_info "Analyzing certificate chain structure..."

# Count certificates in chain
if command -v awk &> /dev/null; then
    CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "$CHAIN_FILE" 2>/dev/null || echo "0")
    print_info "Chain file contains $CERT_COUNT certificate(s)"
fi

# Show certificate subjects in chain
print_info "Certificate chain hierarchy:"
echo ""
awk 'BEGIN {cert=""}
     /BEGIN CERT/ {cert=""}
     {cert=cert $0 "\n"}
     /END CERT/ {
       print cert | "openssl x509 -noout -subject -issuer 2>/dev/null"
       close("openssl x509 -noout -subject -issuer 2>/dev/null")
     }' "$CHAIN_FILE" 2>/dev/null | sed 's/^/  /'

################################################################################
# Step 8: Security Checks
################################################################################
print_section "Step 8: Security & Best Practices"

# Check key size
KEY_SIZE=$(openssl pkey -in "$KEY_FILE" -text -noout 2>/dev/null | grep -oP '(?<=Private-Key: \()[0-9]+' || echo "0")
if [ "$KEY_SIZE" -ge 2048 ]; then
    print_success "Key size is adequate: $KEY_SIZE bits"
else
    print_warning "Key size is below recommended: $KEY_SIZE bits (should be ≥2048)"
fi

# Check certificate expiration
EXPIRY_DATE=$(openssl x509 -in "$CERT_FILE" -noout -enddate 2>/dev/null | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_DATE" +%s 2>/dev/null)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
    print_error "Certificate has EXPIRED! ($DAYS_UNTIL_EXPIRY days ago)"
    exit 1
elif [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
    print_warning "Certificate expires in $DAYS_UNTIL_EXPIRY days - renewal recommended"
else
    print_success "Certificate expires in $DAYS_UNTIL_EXPIRY days"
fi

# Check signature algorithm
SIG_ALG=$(openssl x509 -in "$CERT_FILE" -noout -text 2>/dev/null | grep "Signature Algorithm" | head -1 | awk '{print $3}')
if [[ "$SIG_ALG" == *"sha256"* ]] || [[ "$SIG_ALG" == *"sha384"* ]] || [[ "$SIG_ALG" == *"sha512"* ]]; then
    print_success "Using modern signature algorithm: $SIG_ALG"
elif [[ "$SIG_ALG" == *"sha1"* ]]; then
    print_warning "Using deprecated signature algorithm: $SIG_ALG (SHA-1 is deprecated)"
else
    print_info "Signature algorithm: $SIG_ALG"
fi

################################################################################
# Step 9: File Permissions Check
################################################################################
print_section "Step 9: File Permissions"

CERT_PERMS=$(stat -c %a "$CERT_FILE" 2>/dev/null || stat -f %A "$CERT_FILE" 2>/dev/null)
KEY_PERMS=$(stat -c %a "$KEY_FILE" 2>/dev/null || stat -f %A "$KEY_FILE" 2>/dev/null)

print_info "Certificate permissions: $CERT_PERMS (recommended: 644)"
print_info "Private key permissions: $KEY_PERMS (recommended: 600 or 400)"

if [ "$KEY_PERMS" != "600" ] && [ "$KEY_PERMS" != "400" ]; then
    print_warning "Private key permissions are too permissive"
    print_info "Run: chmod 600 $KEY_FILE"
fi

################################################################################
# Summary
################################################################################
print_section "Validation Summary"

echo ""
print_success "All validations passed successfully!"
echo ""
echo "📋 Certificate Information:"
echo "   Certificate: $CERT_FILE"
echo "   Private Key: $KEY_FILE"
echo "   Chain: $CHAIN_FILE"
if [ -n "$DOMAIN" ]; then
    echo "   Domain: $DOMAIN"
fi
echo "   Key Size: $KEY_SIZE bits"
echo "   Expires: $EXPIRY_DATE ($DAYS_UNTIL_EXPIRY days)"
echo "   Signature: $SIG_ALG"
echo ""

print_success "✅ Certificate is ready for deployment!"
echo ""
echo "Next steps:"
echo "  1. Install certificate to WAF:"
echo "     python3 $CERT_MANAGER install $DOMAIN $CERT_FILE $KEY_FILE --chain $CHAIN_FILE"
echo ""
echo "  2. Sync with Caddy server"
echo ""
echo "  3. Test deployment:"
echo "     curl -vI https://$DOMAIN"
echo "     python3 $CERT_MANAGER remote $DOMAIN"
echo ""

exit 0
