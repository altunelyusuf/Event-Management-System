"""
Security Hardening Schemas
Sprint 23: Security Hardening

Pydantic schemas for security events, rate limiting, IP management, and threat detection.
"""

from pydantic import BaseModel, Field, validator, IPvAnyAddress
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# Security Event Schemas
# ============================================================================

class SecurityEventCreate(BaseModel):
    """Schema for creating a security event"""
    event_type: str = Field(..., description="Type of security event")
    severity: str = Field(..., description="Severity level (low, medium, high, critical)")
    user_id: Optional[UUID] = None
    ip_address: str = Field(..., max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)
    description: str = Field(..., description="Event description")
    metadata: Optional[Dict[str, Any]] = None

    @validator('severity')
    def validate_severity(cls, v):
        """Validate severity level"""
        allowed = ['low', 'medium', 'high', 'critical']
        if v not in allowed:
            raise ValueError(f'Severity must be one of: {allowed}')
        return v

    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type"""
        allowed = [
            'failed_login', 'successful_login', 'password_reset',
            'rate_limit_exceeded', 'suspicious_activity', 'brute_force_attempt',
            'sql_injection_attempt', 'xss_attempt', 'csrf_attempt',
            'unauthorized_access', 'permission_escalation', 'data_breach_attempt',
            'malware_detected', 'ddos_attempt', 'account_takeover_attempt',
            'sensitive_data_access', 'configuration_change', 'security_scan_detected'
        ]
        if v not in allowed:
            raise ValueError(f'Invalid event type. Allowed: {allowed}')
        return v


class SecurityEventResponse(BaseModel):
    """Schema for security event response"""
    id: UUID
    event_type: str
    severity: str
    user_id: Optional[UUID]
    ip_address: str
    user_agent: Optional[str]
    description: str
    metadata: Optional[Dict[str, Any]]
    occurred_at: datetime

    class Config:
        from_attributes = True


class SecurityEventQuery(BaseModel):
    """Schema for querying security events"""
    event_type: Optional[str] = None
    severity: Optional[str] = None
    user_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)


class SecurityEventStats(BaseModel):
    """Schema for security event statistics"""
    total_events: int
    events_by_severity: Dict[str, int]
    events_by_type: Dict[str, int]
    top_attacking_ips: List[Dict[str, Any]]
    recent_events: List[SecurityEventResponse]


# ============================================================================
# Rate Limiting Schemas
# ============================================================================

class RateLimitConfig(BaseModel):
    """Schema for rate limit configuration"""
    resource: str = Field(..., description="Resource identifier (endpoint, user, IP)")
    requests_per_minute: int = Field(60, ge=1, le=10000)
    requests_per_hour: int = Field(1000, ge=1, le=100000)
    requests_per_day: int = Field(10000, ge=1, le=1000000)
    enabled: bool = True


class RateLimitResponse(BaseModel):
    """Schema for rate limit check response"""
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    retry_after: Optional[int] = None


class RateLimitStats(BaseModel):
    """Schema for rate limit statistics"""
    total_requests: int
    blocked_requests: int
    block_rate: float
    top_limited_ips: List[Dict[str, Any]]
    top_limited_users: List[Dict[str, Any]]


# ============================================================================
# IP Blacklist/Whitelist Schemas
# ============================================================================

class IPBlacklistCreate(BaseModel):
    """Schema for creating IP blacklist entry"""
    ip_address: str = Field(..., max_length=45)
    reason: str = Field(..., description="Reason for blacklisting")
    blocked_until: Optional[datetime] = Field(None, description="Temporary block until this time")

    @validator('ip_address')
    def validate_ip(cls, v):
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError('Invalid IP address format')
        return v


class IPBlacklistResponse(BaseModel):
    """Schema for IP blacklist response"""
    id: UUID
    ip_address: str
    reason: str
    blocked_until: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class IPWhitelistCreate(BaseModel):
    """Schema for creating IP whitelist entry"""
    ip_address: str = Field(..., max_length=45)
    description: Optional[str] = None

    @validator('ip_address')
    def validate_ip(cls, v):
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError('Invalid IP address format')
        return v


class IPWhitelistResponse(BaseModel):
    """Schema for IP whitelist response"""
    id: UUID
    ip_address: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Threat Detection Schemas
# ============================================================================

class ThreatDetectionResult(BaseModel):
    """Schema for threat detection result"""
    is_threat: bool
    threat_level: str = Field(..., description="none, low, medium, high, critical")
    threat_types: List[str]
    confidence_score: float = Field(..., ge=0, le=1)
    details: Dict[str, Any]
    recommended_action: str


class SuspiciousActivityReport(BaseModel):
    """Schema for suspicious activity report"""
    detected_at: datetime
    ip_address: str
    user_id: Optional[UUID]
    activity_type: str
    description: str
    risk_score: int = Field(..., ge=0, le=100)
    indicators: List[str]


class ThreatIntelligence(BaseModel):
    """Schema for threat intelligence data"""
    ip_address: str
    is_known_threat: bool
    threat_sources: List[str]
    reputation_score: int = Field(..., ge=0, le=100)
    last_seen: Optional[datetime]
    attack_types: List[str]


# ============================================================================
# Security Audit Schemas
# ============================================================================

class SecurityAuditRequest(BaseModel):
    """Schema for security audit request"""
    audit_type: str = Field(..., description="Type of audit to perform")
    scope: List[str] = Field(..., description="Scope of audit (endpoints, users, etc.)")
    include_archived: bool = False

    @validator('audit_type')
    def validate_audit_type(cls, v):
        """Validate audit type"""
        allowed = ['vulnerability_scan', 'permission_audit', 'access_log_review',
                   'configuration_review', 'dependency_scan', 'compliance_check']
        if v not in allowed:
            raise ValueError(f'Invalid audit type. Allowed: {allowed}')
        return v


class SecurityAuditResult(BaseModel):
    """Schema for security audit result"""
    audit_id: UUID
    audit_type: str
    started_at: datetime
    completed_at: datetime
    status: str
    findings_count: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    findings: List[Dict[str, Any]]
    recommendations: List[str]


class VulnerabilityFinding(BaseModel):
    """Schema for vulnerability finding"""
    vulnerability_id: str
    title: str
    description: str
    severity: str
    cvss_score: Optional[float] = Field(None, ge=0, le=10)
    affected_component: str
    remediation: str
    references: List[str]


class ComplianceCheckResult(BaseModel):
    """Schema for compliance check result"""
    framework: str = Field(..., description="Compliance framework (OWASP, GDPR, etc.)")
    compliant: bool
    score: float = Field(..., ge=0, le=100)
    checks_passed: int
    checks_failed: int
    findings: List[Dict[str, Any]]


# ============================================================================
# Security Configuration Schemas
# ============================================================================

class SecurityConfigUpdate(BaseModel):
    """Schema for updating security configuration"""
    password_min_length: Optional[int] = Field(None, ge=8, le=128)
    password_require_uppercase: Optional[bool] = None
    password_require_lowercase: Optional[bool] = None
    password_require_numbers: Optional[bool] = None
    password_require_special: Optional[bool] = None
    max_login_attempts: Optional[int] = Field(None, ge=3, le=10)
    lockout_duration_minutes: Optional[int] = Field(None, ge=5, le=1440)
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=1440)
    enable_2fa: Optional[bool] = None
    enable_ip_whitelist: Optional[bool] = None
    enable_rate_limiting: Optional[bool] = None


class SecurityConfigResponse(BaseModel):
    """Schema for security configuration response"""
    password_min_length: int
    password_require_uppercase: bool
    password_require_lowercase: bool
    password_require_numbers: bool
    password_require_special: bool
    max_login_attempts: int
    lockout_duration_minutes: int
    session_timeout_minutes: int
    enable_2fa: bool
    enable_ip_whitelist: bool
    enable_rate_limiting: bool
    updated_at: datetime


# ============================================================================
# Security Dashboard Schemas
# ============================================================================

class SecurityDashboard(BaseModel):
    """Schema for security dashboard"""
    timestamp: datetime
    security_score: float = Field(..., ge=0, le=100)
    threat_level: str
    active_threats: int
    recent_events: List[SecurityEventResponse]
    blocked_ips_count: int
    rate_limit_violations: int
    failed_login_attempts: int
    suspicious_activities: int
    recommendations: List[str]


class SecurityMetrics(BaseModel):
    """Schema for security metrics"""
    period_start: datetime
    period_end: datetime
    total_events: int
    critical_events: int
    blocked_attempts: int
    successful_authentications: int
    failed_authentications: int
    unique_attacking_ips: int
    average_threat_score: float


# ============================================================================
# OWASP Top 10 Schemas
# ============================================================================

class OWASPVulnerabilityCheck(BaseModel):
    """Schema for OWASP vulnerability check"""
    category: str = Field(..., description="OWASP Top 10 category")
    vulnerable: bool
    severity: str
    description: str
    mitigation_status: str
    evidence: List[str]

    @validator('category')
    def validate_category(cls, v):
        """Validate OWASP category"""
        allowed = [
            'A01:2021-Broken Access Control',
            'A02:2021-Cryptographic Failures',
            'A03:2021-Injection',
            'A04:2021-Insecure Design',
            'A05:2021-Security Misconfiguration',
            'A06:2021-Vulnerable and Outdated Components',
            'A07:2021-Identification and Authentication Failures',
            'A08:2021-Software and Data Integrity Failures',
            'A09:2021-Security Logging and Monitoring Failures',
            'A10:2021-Server-Side Request Forgery (SSRF)'
        ]
        if v not in allowed:
            raise ValueError(f'Invalid OWASP category. Allowed: {allowed}')
        return v


class OWASPComplianceReport(BaseModel):
    """Schema for OWASP compliance report"""
    generated_at: datetime
    overall_status: str
    compliance_score: float = Field(..., ge=0, le=100)
    vulnerabilities: List[OWASPVulnerabilityCheck]
    recommendations: List[str]


# ============================================================================
# Account Security Schemas
# ============================================================================

class AccountSecurityStatus(BaseModel):
    """Schema for account security status"""
    user_id: UUID
    security_score: int = Field(..., ge=0, le=100)
    two_factor_enabled: bool
    password_strength: str
    last_password_change: Optional[datetime]
    suspicious_logins: int
    active_sessions: int
    recent_security_events: List[SecurityEventResponse]
    recommendations: List[str]


class PasswordStrengthCheck(BaseModel):
    """Schema for password strength check"""
    password: str


class PasswordStrengthResult(BaseModel):
    """Schema for password strength result"""
    strength: str = Field(..., description="weak, fair, good, strong, very_strong")
    score: int = Field(..., ge=0, le=100)
    feedback: List[str]
    meets_requirements: bool


# ============================================================================
# Security Alert Schemas
# ============================================================================

class SecurityAlert(BaseModel):
    """Schema for security alert"""
    alert_type: str
    severity: str
    title: str
    description: str
    affected_resources: List[str]
    recommended_actions: List[str]
    created_at: datetime


class SecurityAlertRule(BaseModel):
    """Schema for security alert rule"""
    rule_name: str
    event_type: str
    threshold: int
    time_window_minutes: int
    severity: str
    enabled: bool


# ============================================================================
# Session Security Schemas
# ============================================================================

class ActiveSessionResponse(BaseModel):
    """Schema for active session response"""
    session_id: str
    user_id: UUID
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_current: bool


class SessionTerminateRequest(BaseModel):
    """Schema for session termination request"""
    session_ids: List[str]
    reason: Optional[str] = None
