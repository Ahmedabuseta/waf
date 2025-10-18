"""
WAF Rule Engine for threat detection and blocking
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ThreatLevel(Enum):
    """Threat level enumeration"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleAction(Enum):
    """Rule action enumeration"""
    ALLOW = "allow"
    BLOCK = "block"
    LOG = "log"


@dataclass
class RuleMatch:
    """Result of a rule match"""
    matched: bool
    rule_name: str
    threat_type: str
    threat_level: ThreatLevel
    action: RuleAction
    details: str


class WAFRule:
    """Base WAF rule class"""
    
    def __init__(self, name: str, threat_type: str, threat_level: ThreatLevel, 
                 patterns: List[str], description: str = ""):
        self.name = name
        self.threat_type = threat_type
        self.threat_level = threat_level
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        self.description = description
    
    def check(self, request_data: Dict) -> Optional[RuleMatch]:
        """Check if request matches this rule"""
        # List of headers that should not be checked for malicious patterns
        # These are standard HTTP headers that may contain keywords that trigger false positives
        SAFE_HEADERS = {
            'accept', 'accept-encoding', 'accept-language', 'accept-charset',
            'content-type', 'content-encoding', 'content-language',
            'user-agent', 'host', 'connection', 'cache-control',
            'upgrade-insecure-requests', 'sec-fetch-site', 'sec-fetch-mode',
            'sec-fetch-user', 'sec-fetch-dest', 'sec-ch-ua', 'sec-ch-ua-mobile',
            'sec-ch-ua-platform', 'dnt', 'te', 'pragma',
            'cookie', 'referer', 'origin', 'if-none-match', 'if-modified-since'
        }
        
        # Check URL
        if self._check_patterns(request_data.get('url', '')):
            return self._create_match("URL pattern matched")
        
        # Check headers (exclude safe headers)
        for header, value in request_data.get('headers', {}).items():
            if header.lower() not in SAFE_HEADERS:
                if self._check_patterns(value):
                    return self._create_match(f"Header '{header}' matched")
        
        # Check body
        if self._check_patterns(request_data.get('body', '')):
            return self._create_match("Request body matched")
        
        # Check query parameters
        for param, value in request_data.get('params', {}).items():
            if self._check_patterns(str(value)):
                return self._create_match(f"Query parameter '{param}' matched")
        
        return None
    
    def _check_patterns(self, text: str) -> bool:
        """Check if text matches any pattern"""
        return any(pattern.search(text) for pattern in self.patterns)
    
    def _create_match(self, details: str) -> RuleMatch:
        """Create a rule match result"""
        return RuleMatch(
            matched=True,
            rule_name=self.name,
            threat_type=self.threat_type,
            threat_level=self.threat_level,
            action=RuleAction.BLOCK,  # Default action, will be overridden by template
            details=details
        )


class BasicRuleSet:
    """Basic WAF rule set for common threats"""
    
    @staticmethod
    def get_rules() -> List[WAFRule]:
        return [
            # SQL Injection
            WAFRule(
                name="SQL Injection - Basic",
                threat_type="SQL Injection",
                threat_level=ThreatLevel.HIGH,
                patterns=[
                    r"'\s*(union|UNION)\s+(all\s+)?(select|SELECT)",  # UNION SELECT
                    r"(select|SELECT)\s+.*\s+(from|FROM)\s+.*\s+(where|WHERE).*[=<>]",  # SELECT with WHERE
                    r"(insert|INSERT)\s+(into|INTO)\s+\w+",  # INSERT INTO
                    r"(delete|DELETE)\s+(from|FROM)\s+\w+",  # DELETE FROM
                    r"(drop|DROP)\s+(table|TABLE|database|DATABASE)",  # DROP TABLE
                    r";\s*(drop|DROP|delete|DELETE|update|UPDATE)",  # SQL command after semicolon
                    r"--\s*$",  # SQL comment at end
                    r"'\s+(or|OR)\s+'?\d+'?\s*=\s*'?\d+",  # OR 1=1
                    r"'\s+(and|AND)\s+'?\d+'?\s*=\s*'?\d+",  # AND 1=1
                    r"\bexec(\s|\+)+(s|x)p\w+",  # EXEC sp_
                ],
                description="Detects basic SQL injection attempts"
            ),
            
            # XSS (Cross-Site Scripting)
            WAFRule(
                name="XSS - Basic",
                threat_type="Cross-Site Scripting",
                threat_level=ThreatLevel.HIGH,
                patterns=[
                    r"<script[^>]*>.*?</script>",
                    r"javascript:",
                    r"on\w+\s*=",  # onclick, onload, etc.
                    r"<iframe[^>]*>",
                    r"<embed[^>]*>",
                    r"<object[^>]*>",
                ],
                description="Detects basic XSS attempts"
            ),
            
            # Path Traversal
            WAFRule(
                name="Path Traversal",
                threat_type="Path Traversal",
                threat_level=ThreatLevel.MEDIUM,
                patterns=[
                    r"\.\./",
                    r"\.\.",
                    r"%2e%2e",
                    r"\.\.\\",
                ],
                description="Detects path traversal attempts"
            ),
            
            # Command Injection
            WAFRule(
                name="Command Injection - Basic",
                threat_type="Command Injection",
                threat_level=ThreatLevel.CRITICAL,
                patterns=[
                    r";\s*(ls|cat|wget|curl|nc|bash|sh)\s+",
                    r"\|\s*(ls|cat|wget|curl|nc|bash|sh)\s+",
                    r"`.*`",
                    r"\$\(.*\)",
                ],
                description="Detects command injection attempts"
            ),
            
            # File Inclusion
            WAFRule(
                name="File Inclusion",
                threat_type="File Inclusion",
                threat_level=ThreatLevel.HIGH,
                patterns=[
                    r"(file://|php://|data://|expect://)",
                    r"(\.\.\/.*\.(php|inc|conf|cfg))",
                ],
                description="Detects file inclusion attempts"
            ),
        ]


class AdvancedRuleSet:
    """Advanced WAF rule set for sophisticated threats"""
    
    @staticmethod
    def get_rules() -> List[WAFRule]:
        return [
            # Advanced SQL Injection
            WAFRule(
                name="SQL Injection - Advanced",
                threat_type="SQL Injection",
                threat_level=ThreatLevel.CRITICAL,
                patterns=[
                    r"(\bexec\b|\bexecute\b).*\(",
                    r"\bxp_cmdshell\b",
                    r"(\bbenchmark\b|\bsleep\b)\s*\(",
                    r"\binto\b\s+outfile\b",
                    r"\bload_file\b\s*\(",
                    r"(\bchar\b|\bchr\b|\bascii\b)\s*\(",
                    r"\bhex\b\s*\(",
                    r"\bconcat\b.*\bselect\b",
                ],
                description="Detects advanced SQL injection with evasion techniques"
            ),
            
            # Advanced XSS
            WAFRule(
                name="XSS - Advanced",
                threat_type="Cross-Site Scripting",
                threat_level=ThreatLevel.CRITICAL,
                patterns=[
                    r"expression\s*\(",  # CSS expression
                    r"@import",
                    r"vbscript:",
                    r"data:text/html",
                    r"&#\d+;",  # HTML entities
                    r"\\u[0-9a-f]{4}",  # Unicode escapes
                    r"fromCharCode",
                    r"\.innerHTML\s*=",
                ],
                description="Detects advanced XSS with encoding/obfuscation"
            ),
            
            # XML/XXE Injection
            WAFRule(
                name="XXE Injection",
                threat_type="XML External Entity",
                threat_level=ThreatLevel.HIGH,
                patterns=[
                    r"<!ENTITY",
                    r"<!DOCTYPE.*\[",
                    r"SYSTEM\s+['\"]",
                ],
                description="Detects XXE injection attempts"
            ),
            
            # LDAP Injection
            WAFRule(
                name="LDAP Injection",
                threat_type="LDAP Injection",
                threat_level=ThreatLevel.HIGH,
                patterns=[
                    r"\*\)\(.*=",
                    r"\)\(.*\|",
                    r".*\)\(&\(",
                ],
                description="Detects LDAP injection attempts"
            ),
            
            # NoSQL Injection
            WAFRule(
                name="NoSQL Injection",
                threat_type="NoSQL Injection",
                threat_level=ThreatLevel.HIGH,
                patterns=[
                    r"\$where",
                    r"\$ne",
                    r"\$gt",
                    r"\$regex",
                    r"{\s*\$",
                ],
                description="Detects NoSQL injection attempts"
            ),
            
            # Server-Side Template Injection
            WAFRule(
                name="SSTI",
                threat_type="Server-Side Template Injection",
                threat_level=ThreatLevel.CRITICAL,
                patterns=[
                    r"{{\s*.*\s*}}",
                    r"<%.*%>",
                    r"\${\s*.*\s*}",
                    r"{{.*config.*}}",
                    r"{{.*request.*}}",
                ],
                description="Detects Server-Side Template Injection"
            ),
            
            # HTTP Response Splitting
            WAFRule(
                name="HTTP Response Splitting",
                threat_type="HTTP Response Splitting",
                threat_level=ThreatLevel.MEDIUM,
                patterns=[
                    r"%0d%0a",
                    r"\r\n",
                    r"\\r\\n",
                ],
                description="Detects HTTP response splitting attempts"
            ),
        ]


class WAFRuleEngine:
    """Main WAF rule engine"""
    
    def __init__(self, template_type: str = "basic"):
        self.template_type = template_type
        self.rules = self._load_rules(template_type)
    
    def _load_rules(self, template_type: str) -> List[WAFRule]:
        """Load rules based on template type"""
        if template_type == "basic":
            return BasicRuleSet.get_rules()
        elif template_type == "advanced":
            return BasicRuleSet.get_rules() + AdvancedRuleSet.get_rules()
        else:
            return BasicRuleSet.get_rules()
    
    def evaluate(self, request_data: Dict) -> Tuple[RuleAction, Optional[RuleMatch]]:
        """
        Evaluate request against all rules
        Returns: (action, match_result)
        """
        matches = []
        
        for rule in self.rules:
            match = rule.check(request_data)
            if match:
                matches.append(match)
        
        if not matches:
            return RuleAction.ALLOW, None
        
        # Get highest severity match
        highest_match = max(matches, key=lambda m: self._severity_score(m.threat_level))
        return RuleAction.BLOCK, highest_match
    
    def _severity_score(self, threat_level: ThreatLevel) -> int:
        """Get numeric score for threat level"""
        scores = {
            ThreatLevel.NONE: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }
        return scores.get(threat_level, 0)
    
    def get_rule_summary(self) -> Dict:
        """Get summary of loaded rules"""
        return {
            'template_type': self.template_type,
            'total_rules': len(self.rules),
            'rules_by_threat': self._group_by_threat(),
            'rules_by_severity': self._group_by_severity(),
        }
    
    def _group_by_threat(self) -> Dict[str, int]:
        """Group rules by threat type"""
        groups = {}
        for rule in self.rules:
            groups[rule.threat_type] = groups.get(rule.threat_type, 0) + 1
        return groups
    
    def _group_by_severity(self) -> Dict[str, int]:
        """Group rules by severity"""
        groups = {}
        for rule in self.rules:
            level = rule.threat_level.value
            groups[level] = groups.get(level, 0) + 1
        return groups


def create_rule_engine(waf_template) -> WAFRuleEngine:
    """Factory function to create rule engine from WAF template"""
    if not waf_template:
        return WAFRuleEngine("basic")
    return WAFRuleEngine(waf_template.template_type)

