"""
Security Hardening API
Sprint 23: Security Hardening

API endpoints for security management, threat detection, and monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin
from app.models.user import User
from app.services.security_service import SecurityService
from app.schemas.security import (
    SecurityEventCreate, SecurityEventResponse, SecurityEventQuery,
    SecurityEventStats, IPBlacklistCreate, IPBlacklistResponse,
    ThreatDetectionResult, SuspiciousActivityReport,
    SecurityDashboard, RateLimitStats,
    OWASPComplianceReport, PasswordStrengthCheck, PasswordStrengthResult
)

router = APIRouter(prefix="/security", tags=["security"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_security_service(
    db: AsyncSession = Depends(get_db)
) -> SecurityService:
    """Get security service instance"""
    async with SecurityService(db) as service:
        yield service


# ============================================================================
# Security Event Endpoints
# ============================================================================

@router.post("/events", response_model=SecurityEventResponse, status_code=status.HTTP_201_CREATED)
async def log_security_event(
    event_data: SecurityEventCreate,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Log a security event (admin only).

    Event types:
    - failed_login: Failed login attempt
    - successful_login: Successful login
    - password_reset: Password reset request
    - rate_limit_exceeded: Rate limit exceeded
    - suspicious_activity: Suspicious activity detected
    - brute_force_attempt: Brute force attack detected
    - sql_injection_attempt: SQL injection attempt
    - xss_attempt: Cross-site scripting attempt
    - csrf_attempt: CSRF attempt
    - unauthorized_access: Unauthorized access attempt
    - permission_escalation: Permission escalation attempt
    - data_breach_attempt: Data breach attempt
    - malware_detected: Malware detected
    - ddos_attempt: DDoS attempt
    - account_takeover_attempt: Account takeover attempt
    - sensitive_data_access: Sensitive data access
    - configuration_change: Security configuration change
    - security_scan_detected: Security scan detected

    Severity levels: low, medium, high, critical
    """
    return await security_service.log_security_event(event_data)


@router.get("/events", response_model=List[SecurityEventResponse])
async def query_security_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    ip_address: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Query security events (admin only).

    Filter by event type, severity, IP address, and time range.
    """
    from datetime import datetime, timedelta

    query = SecurityEventQuery(
        event_type=event_type,
        severity=severity,
        ip_address=ip_address,
        start_date=datetime.utcnow() - timedelta(hours=hours_back),
        limit=limit
    )

    return await security_service.query_events(query)


@router.get("/events/stats", response_model=SecurityEventStats)
async def get_event_statistics(
    hours_back: int = 24,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get security event statistics (admin only).

    Returns:
    - Total event count
    - Events by severity
    - Events by type
    - Top attacking IPs
    - Recent events
    """
    return await security_service.get_event_statistics(hours_back)


# ============================================================================
# Threat Detection Endpoints
# ============================================================================

@router.post("/threats/detect", response_model=ThreatDetectionResult)
async def detect_threats(
    ip_address: str,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Detect threats from an IP address (admin only).

    Analyzes:
    - Historical security events
    - Activity patterns
    - Blacklist status
    - Risk score

    Returns threat assessment and recommended actions.
    """
    return await security_service.detect_threats(ip_address)


@router.get("/threats/suspicious", response_model=List[SuspiciousActivityReport])
async def get_suspicious_activities(
    hours_back: int = 24,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get suspicious activity report (admin only).

    Identifies IPs with suspicious behavior patterns:
    - High request rates
    - Multiple attack attempts
    - Known attack signatures
    - Abnormal access patterns

    Returns list of suspicious activities sorted by risk score.
    """
    return await security_service.generate_suspicious_activity_report(hours_back)


# ============================================================================
# IP Blacklist Management Endpoints
# ============================================================================

@router.post("/blacklist", response_model=IPBlacklistResponse, status_code=status.HTTP_201_CREATED)
async def add_ip_to_blacklist(
    blacklist_data: IPBlacklistCreate,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Add IP to blacklist (admin only).

    Blocks all requests from the specified IP address.
    Can be temporary (with blocked_until) or permanent.
    """
    return await security_service.blacklist_ip(blacklist_data)


@router.delete("/blacklist/{ip_address}")
async def remove_ip_from_blacklist(
    ip_address: str,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Remove IP from blacklist (admin only).

    Allows requests from the specified IP address again.
    """
    success = await security_service.remove_from_blacklist(ip_address)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP address not found in blacklist"
        )

    return {"message": f"IP {ip_address} removed from blacklist"}


@router.get("/blacklist", response_model=List[IPBlacklistResponse])
async def get_blacklisted_ips(
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get all blacklisted IPs (admin only).

    Returns list of blocked IP addresses with reasons and expiration times.
    """
    return await security_service.get_blacklisted_ips()


@router.get("/blacklist/check/{ip_address}")
async def check_ip_blacklist_status(
    ip_address: str,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Check if IP is blacklisted (admin only).

    Returns blacklist status for the specified IP.
    """
    is_blocked = await security_service.is_ip_blocked(ip_address)

    return {
        "ip_address": ip_address,
        "is_blacklisted": is_blocked
    }


# ============================================================================
# Rate Limiting Endpoints
# ============================================================================

@router.get("/rate-limit/stats", response_model=RateLimitStats)
async def get_rate_limit_statistics(
    hours_back: int = 24,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get rate limiting statistics (admin only).

    Returns:
    - Total requests
    - Blocked requests
    - Block rate
    - Top limited IPs/users
    """
    return await security_service.get_rate_limit_stats(hours_back)


@router.post("/rate-limit/check")
async def check_rate_limit(
    identifier: str,
    resource: str,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Check rate limit for identifier (admin only).

    Returns whether request is allowed and remaining quota.
    """
    allowed, remaining = await security_service.check_rate_limit(identifier, resource)

    return {
        "identifier": identifier,
        "resource": resource,
        "allowed": allowed,
        "remaining_requests": remaining
    }


# ============================================================================
# Security Dashboard Endpoints
# ============================================================================

@router.get("/dashboard", response_model=SecurityDashboard)
async def get_security_dashboard(
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get security dashboard (admin only).

    Comprehensive security overview including:
    - Security score (0-100)
    - Threat level
    - Active threats count
    - Recent security events
    - Blocked IPs count
    - Rate limit violations
    - Failed login attempts
    - Suspicious activities count
    - Security recommendations
    """
    return await security_service.get_security_dashboard()


@router.get("/dashboard/metrics")
async def get_security_metrics(
    hours_back: int = 24,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get security metrics (admin only).

    Time-series metrics for security monitoring and analytics.
    """
    event_stats = await security_service.get_event_statistics(hours_back)

    return {
        "period_hours": hours_back,
        "total_events": event_stats.total_events,
        "events_by_severity": event_stats.events_by_severity,
        "events_by_type": event_stats.events_by_type,
        "top_attacking_ips": event_stats.top_attacking_ips
    }


# ============================================================================
# Password Security Endpoints
# ============================================================================

@router.post("/password/check-strength", response_model=PasswordStrengthResult)
async def check_password_strength(
    password_data: PasswordStrengthCheck,
    current_user: User = Depends(get_current_user),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Check password strength.

    Analyzes password and returns:
    - Strength level (weak, fair, good, strong, very_strong)
    - Score (0-100)
    - Improvement feedback
    - Whether it meets minimum requirements
    """
    return await security_service.check_password_strength(password_data.password)


# ============================================================================
# OWASP Compliance Endpoints
# ============================================================================

@router.get("/owasp/compliance", response_model=OWASPComplianceReport)
async def get_owasp_compliance_report(
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get OWASP Top 10 compliance report (admin only).

    Checks compliance with OWASP Top 10:
    - A01: Broken Access Control
    - A02: Cryptographic Failures
    - A03: Injection
    - A04: Insecure Design
    - A05: Security Misconfiguration
    - A06: Vulnerable and Outdated Components
    - A07: Identification and Authentication Failures
    - A08: Software and Data Integrity Failures
    - A09: Security Logging and Monitoring Failures
    - A10: Server-Side Request Forgery (SSRF)

    Returns compliance score and recommendations.
    """
    return await security_service.generate_owasp_compliance_report()


# ============================================================================
# Security Audit Endpoints
# ============================================================================

@router.post("/audit/start")
async def start_security_audit(
    audit_type: str,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Start a security audit (admin only).

    Audit types:
    - vulnerability_scan: Scan for vulnerabilities
    - permission_audit: Audit user permissions
    - access_log_review: Review access logs
    - configuration_review: Review security configuration
    - dependency_scan: Scan dependencies for vulnerabilities
    - compliance_check: Check regulatory compliance

    Returns audit ID for tracking.
    """
    # Placeholder for actual audit implementation
    from uuid import uuid4
    from datetime import datetime

    return {
        "audit_id": str(uuid4()),
        "audit_type": audit_type,
        "status": "started",
        "started_at": datetime.utcnow()
    }


@router.get("/audit/{audit_id}")
async def get_audit_results(
    audit_id: str,
    current_user: User = Depends(require_admin)
):
    """
    Get security audit results (admin only).

    Returns audit findings, recommendations, and compliance status.
    """
    # Placeholder for actual audit results
    return {
        "audit_id": audit_id,
        "status": "completed",
        "message": "Audit results would be returned here"
    }


# ============================================================================
# Maintenance Endpoints
# ============================================================================

@router.post("/maintenance/cleanup")
async def cleanup_old_security_data(
    days_to_keep: int = 90,
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Clean up old security data (admin only).

    Removes:
    - Security events older than specified days
    - Expired blacklist entries
    - Expired rate limit entries

    Default retention: 90 days
    """
    result = await security_service.cleanup_old_data(days_to_keep)

    return {
        "message": "Security data cleanup completed",
        "days_retained": days_to_keep,
        **result
    }


# ============================================================================
# Security Configuration Endpoints
# ============================================================================

@router.get("/config")
async def get_security_configuration(
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get current security configuration (admin only).

    Returns:
    - Rate limiting settings
    - Password requirements
    - Login attempt limits
    - Session timeout settings
    - Feature flags (2FA, IP whitelist, etc.)
    """
    return {
        "rate_limiting": {
            "per_minute": security_service.config["rate_limit_per_minute"],
            "per_hour": security_service.config["rate_limit_per_hour"]
        },
        "password_policy": {
            "min_length": security_service.config["password_min_length"]
        },
        "login_security": {
            "max_attempts": security_service.config["max_login_attempts"],
            "lockout_duration_minutes": security_service.config["lockout_duration_minutes"]
        },
        "threat_detection": {
            "brute_force_threshold": security_service.config["brute_force_threshold"],
            "brute_force_window_minutes": security_service.config["brute_force_window_minutes"]
        }
    }


# ============================================================================
# Real-time Security Monitoring Endpoints
# ============================================================================

@router.get("/monitoring/live")
async def get_live_security_status(
    current_user: User = Depends(require_admin),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Get real-time security status (admin only).

    Returns current security state:
    - Active threats
    - Recent events (last 5 minutes)
    - Current rate limit status
    - System security posture
    """
    from datetime import datetime, timedelta

    # Get very recent events
    recent_query = SecurityEventQuery(
        start_date=datetime.utcnow() - timedelta(minutes=5),
        limit=50
    )
    recent_events = await security_service.query_events(recent_query)

    # Get threat assessment
    suspicious_reports = await security_service.generate_suspicious_activity_report(hours_back=1)
    active_threats = [r for r in suspicious_reports if r.risk_score > 70]

    return {
        "timestamp": datetime.utcnow(),
        "status": "active",
        "recent_events_count": len(recent_events),
        "active_threats_count": len(active_threats),
        "recent_events": [
            {
                "type": e.event_type,
                "severity": e.severity,
                "ip": e.ip_address,
                "time": e.occurred_at
            }
            for e in recent_events[:10]
        ],
        "active_threats": [
            {
                "ip": t.ip_address,
                "risk_score": t.risk_score,
                "activity_type": t.activity_type
            }
            for t in active_threats[:5]
        ]
    }


# ============================================================================
# Helper Functions for Middleware
# ============================================================================

async def log_failed_login_attempt(
    request: Request,
    user_id: Optional[str],
    reason: str,
    db: AsyncSession
):
    """
    Helper function to log failed login from middleware.

    Should be called from authentication middleware.
    """
    from uuid import UUID

    security_service = SecurityService(db)

    user_uuid = UUID(user_id) if user_id else None
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    await security_service.log_failed_login(
        user_id=user_uuid,
        ip_address=ip_address,
        user_agent=user_agent,
        reason=reason
    )

    await db.commit()
    await db.close()


async def log_suspicious_request(
    request: Request,
    activity_type: str,
    description: str,
    db: AsyncSession
):
    """
    Helper function to log suspicious request from middleware.

    Should be called from security monitoring middleware.
    """
    security_service = SecurityService(db)

    ip_address = request.client.host if request.client else "unknown"

    await security_service.log_suspicious_activity(
        activity_type=activity_type,
        ip_address=ip_address,
        user_id=None,
        description=description
    )

    await db.commit()
    await db.close()
