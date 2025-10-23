#!/bin/bash
# DNS TXT Record Checker for Wildcard Certificate Generation
# This script helps verify that both TXT records are properly configured

DOMAIN="${1:-p2s.tech}"
RECORD_NAME="_acme-challenge.${DOMAIN}"

echo "=================================================="
echo "DNS TXT Record Checker for Wildcard Certificates"
echo "=================================================="
echo ""
echo "Domain: $DOMAIN"
echo "Record: $RECORD_NAME"
echo ""

echo "1. Checking DNS TXT records with dig..."
echo "=================================================="
dig TXT "$RECORD_NAME" +short
echo ""

RECORD_COUNT=$(dig TXT "$RECORD_NAME" +short | wc -l)
echo "Number of TXT records found: $RECORD_COUNT"
echo ""

if [ "$RECORD_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No TXT records found!"
    echo "   Action: Add TXT records to your DNS provider"
elif [ "$RECORD_COUNT" -eq 1 ]; then
    echo "⚠️  WARNING: Only 1 TXT record found!"
    echo "   For wildcard certificates, you need 2 TXT records"
    echo "   Action: Add the SECOND TXT record to your DNS provider"
    echo ""
    echo "   Current record:"
    dig TXT "$RECORD_NAME" +short
    echo ""
    echo "   You need to ADD (not replace) a second record with"
    echo "   the same name but different value"
elif [ "$RECORD_COUNT" -eq 2 ]; then
    echo "✅ SUCCESS: 2 TXT records found!"
    echo "   Both records are configured correctly"
    echo ""
    echo "   Record 1: $(dig TXT "$RECORD_NAME" +short | sed -n '1p')"
    echo "   Record 2: $(dig TXT "$RECORD_NAME" +short | sed -n '2p')"
    echo ""
    echo "   You can now click 'Verify DNS & Generate Certificate'"
else
    echo "⚠️  NOTICE: $RECORD_COUNT TXT records found"
    echo "   (Expected 2 for wildcard certificates)"
    echo ""
    dig TXT "$RECORD_NAME" +short | nl
fi

echo ""
echo "2. Checking with nslookup..."
echo "=================================================="
nslookup -type=TXT "$RECORD_NAME" 2>/dev/null | grep "text =" || echo "No records found"
echo ""

echo "3. Checking DNS propagation across multiple servers..."
echo "=================================================="

# Array of public DNS servers
declare -A DNS_SERVERS=(
    ["Google"]="8.8.8.8"
    ["Cloudflare"]="1.1.1.1"
    ["Quad9"]="9.9.9.9"
    ["OpenDNS"]="208.67.222.222"
)

for name in "${!DNS_SERVERS[@]}"; do
    ip="${DNS_SERVERS[$name]}"
    echo -n "$name ($ip): "
    result=$(dig @"$ip" TXT "$RECORD_NAME" +short 2>/dev/null | wc -l)
    if [ "$result" -eq 0 ]; then
        echo "❌ Not found"
    elif [ "$result" -eq 1 ]; then
        echo "⚠️  Only 1 record"
    elif [ "$result" -eq 2 ]; then
        echo "✅ Both records found"
    else
        echo "⚠️  $result records found"
    fi
done

echo ""
echo "=================================================="
echo "Summary:"
echo "=================================================="

if [ "$RECORD_COUNT" -eq 2 ]; then
    echo "✅ Status: READY FOR VERIFICATION"
    echo ""
    echo "Next steps:"
    echo "1. Go to the DNS Challenge page"
    echo "2. Click 'Verify DNS & Generate Certificate'"
    echo "3. System will verify both records and generate certificate"
elif [ "$RECORD_COUNT" -eq 1 ]; then
    echo "⚠️  Status: INCOMPLETE - Need 1 more record"
    echo ""
    echo "Next steps:"
    echo "1. Go to your DNS provider"
    echo "2. ADD a second TXT record (do NOT replace the existing one)"
    echo "3. Name: _acme-challenge.$DOMAIN"
    echo "4. Type: TXT"
    echo "5. Value: [Second value from UI - different from first]"
    echo "6. Wait 5-10 minutes for DNS propagation"
    echo "7. Run this script again to verify"
elif [ "$RECORD_COUNT" -eq 0 ]; then
    echo "❌ Status: NO RECORDS FOUND"
    echo ""
    echo "Next steps:"
    echo "1. Go to DNS Challenge page and click 'Get TXT Records'"
    echo "2. Copy BOTH TXT record values"
    echo "3. Add BOTH records to your DNS provider"
    echo "4. Wait 5-10 minutes for DNS propagation"
    echo "5. Run this script again to verify"
else
    echo "⚠️  Status: UNEXPECTED NUMBER OF RECORDS ($RECORD_COUNT)"
fi

echo ""
echo "=================================================="
echo "How to add multiple TXT records:"
echo "=================================================="
echo ""
echo "Cloudflare:"
echo "  1. Click 'Add record' for first TXT record"
echo "  2. Click 'Add record' AGAIN for second TXT record"
echo "  3. Both records should have:"
echo "     - Same Name: _acme-challenge"
echo "     - Type: TXT"
echo "     - Different Content/Value"
echo ""
echo "AWS Route53:"
echo "  1. Edit the TXT record"
echo "  2. In 'Value' field, add both values on separate lines:"
echo "     \"value1\""
echo "     \"value2\""
echo ""
echo "GoDaddy/Namecheap:"
echo "  1. Add first TXT record"
echo "  2. Add second TXT record with same Host but different Value"
echo ""
echo "=================================================="
