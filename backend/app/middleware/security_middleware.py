"""
Security Monitoring Middleware
Sprint 23: Security Hardening

Middleware for security monitoring, threat detection, and IP blacklist enforcement.
"""

import re
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from typing import Callable, Pattern, List
import asyncio

from app.core.database import AsyncSessionLocal
from app.schemas.security import SecurityEventCreate


class IPBlacklistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to block requests from blacklisted IPs.

    Checks all incoming requests against the IP blacklist and
    blocks requests from blacklisted addresses.
    """

    def __init__(self, app, excluded_paths: List[str] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json"]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Check IP blacklist before processing request"""
        # Skip for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is blacklisted
        is_blacklisted = await self._is_ip_blacklisted(client_ip)

        if is_blacklisted:
            # Log security event
            asyncio.create_task(
                self._log_blocked_request(client_ip, request.url.path)
            )

            return Response(
                content='{"detail": "Access denied"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json"
            )

        return await call_next(request)

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from blacklist checking"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check X-Forwarded-For header (for proxies/load balancers)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    async def _is_ip_blacklisted(self, ip_address: str) -> bool:
        """Check if IP is blacklisted"""
        try:
            async with AsyncSessionLocal() as db:
                from app.repositories.security_repository import SecurityRepository
                security_repo = SecurityRepository(db)
                return await security_repo.is_ip_blacklisted(ip_address)
        except Exception as e:
            print(f"Error checking IP blacklist: {e}")
            return False

    async def _log_blocked_request(self, ip_address: str, path: str):
        """Log blocked request"""
        try:
            async with AsyncSessionLocal() as db:
                from app.repositories.security_repository import SecurityRepository
                security_repo = SecurityRepository(db)

                event_data = SecurityEventCreate(
                    event_type="unauthorized_access",
                    severity="high",
                    user_id=None,
                    ip_address=ip_address,
                    user_agent=None,
                    description=f"Blocked request from blacklisted IP to {path}",
                    metadata={"path": path}
                )

                await security_repo.create_security_event(event_data)
                await db.commit()
        except Exception as e:
            print(f"Error logging blocked request: {e}")


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security monitoring and threat detection.

    Monitors requests for:
    - SQL injection attempts
    - XSS attempts
    - Path traversal attempts
    - Command injection attempts
    - Suspicious patterns
    """

    def __init__(self, app):
        super().__init__(app)

        # Compile regex patterns for threat detection
        self.sql_injection_patterns = [
            re.compile(r"(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b)", re.IGNORECASE),
            re.compile(r"('|\"|;|--|\*|\/\*|\*\/)", re.IGNORECASE),
            re.compile(r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+", re.IGNORECASE),
        ]

        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # event handlers
            re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        ]

        self.path_traversal_patterns = [
            re.compile(r"\.\.\/|\.\.\\"),
            re.compile(r"\/etc\/passwd", re.IGNORECASE),
            re.compile(r"\/windows\/system32", re.IGNORECASE),
        ]

        self.command_injection_patterns = [
            re.compile(r"[;&|`$]"),
            re.compile(r"\$\(.*\)"),
            re.compile(r"`.*`"),
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Monitor request for security threats"""
        # Get request data for analysis
        client_ip = self._get_client_ip(request)
        path = request.url.path
        query_params = str(request.query_params)
        user_agent = request.headers.get("user-agent", "")

        # Check for threats
        threats_detected = []

        # Check query parameters
        if self._detect_sql_injection(query_params):
            threats_detected.append("sql_injection_attempt")

        if self._detect_xss(query_params):
            threats_detected.append("xss_attempt")

        if self._detect_path_traversal(path):
            threats_detected.append("path_traversal_attempt")

        if self._detect_command_injection(query_params):
            threats_detected.append("command_injection_attempt")

        # Check user agent for security scanners
        if self._detect_security_scanner(user_agent):
            threats_detected.append("security_scan_detected")

        # Log threats
        if threats_detected:
            asyncio.create_task(
                self._log_security_threats(
                    client_ip,
                    threats_detected,
                    path,
                    query_params,
                    user_agent
                )
            )

            # Block obviously malicious requests
            if any(t in ["sql_injection_attempt", "command_injection_attempt"]
                   for t in threats_detected):
                return Response(
                    content='{"detail": "Malicious request detected"}',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    media_type="application/json"
                )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _detect_sql_injection(self, text: str) -> bool:
        """Detect SQL injection attempts"""
        return any(pattern.search(text) for pattern in self.sql_injection_patterns)

    def _detect_xss(self, text: str) -> bool:
        """Detect XSS attempts"""
        return any(pattern.search(text) for pattern in self.xss_patterns)

    def _detect_path_traversal(self, path: str) -> bool:
        """Detect path traversal attempts"""
        return any(pattern.search(path) for pattern in self.path_traversal_patterns)

    def _detect_command_injection(self, text: str) -> bool:
        """Detect command injection attempts"""
        return any(pattern.search(text) for pattern in self.command_injection_patterns)

    def _detect_security_scanner(self, user_agent: str) -> bool:
        """Detect security scanner user agents"""
        scanner_signatures = [
            "nmap", "nikto", "sqlmap", "metasploit", "burp", "acunetix",
            "nessus", "openvas", "w3af", "skipfish", "wapiti"
        ]
        user_agent_lower = user_agent.lower()
        return any(sig in user_agent_lower for sig in scanner_signatures)

    async def _log_security_threats(
        self,
        ip_address: str,
        threats: List[str],
        path: str,
        query_params: str,
        user_agent: str
    ):
        """Log detected security threats"""
        try:
            async with AsyncSessionLocal() as db:
                from app.repositories.security_repository import SecurityRepository
                security_repo = SecurityRepository(db)

                for threat_type in threats:
                    # Determine severity
                    critical_threats = ["sql_injection_attempt", "command_injection_attempt"]
                    severity = "critical" if threat_type in critical_threats else "high"

                    event_data = SecurityEventCreate(
                        event_type=threat_type,
                        severity=severity,
                        user_id=None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        description=f"{threat_type.replace('_', ' ').title()} detected",
                        metadata={
                            "path": path,
                            "query_params": query_params[:500],  # Limit size
                            "threat_type": threat_type
                        }
                    )

                    await security_repo.create_security_event(event_data)

                await db.commit()
        except Exception as e:
            print(f"Error logging security threat: {e}")


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF (Cross-Site Request Forgery) protection middleware.

    Validates CSRF tokens for state-changing requests (POST, PUT, DELETE, PATCH).
    """

    def __init__(self, app, excluded_paths: List[str] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json", "/auth/login", "/auth/register"
        ]
        self.safe_methods = ["GET", "HEAD", "OPTIONS"]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate CSRF token for state-changing requests"""
        # Skip for safe methods
        if request.method in self.safe_methods:
            return await call_next(request)

        # Skip for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Check CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")

        # In production, validate against session token
        # For now, just check if token exists
        if not csrf_token:
            # Log CSRF attempt
            asyncio.create_task(
                self._log_csrf_attempt(request)
            )

            # In development, allow requests without CSRF token
            # In production, this should return 403
            # return Response(
            #     content='{"detail": "CSRF token missing or invalid"}',
            #     status_code=status.HTTP_403_FORBIDDEN,
            #     media_type="application/json"
            # )

        return await call_next(request)

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from CSRF protection"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    async def _log_csrf_attempt(self, request: Request):
        """Log CSRF attempt"""
        try:
            client_ip = request.client.host if request.client else "unknown"

            async with AsyncSessionLocal() as db:
                from app.repositories.security_repository import SecurityRepository
                security_repo = SecurityRepository(db)

                event_data = SecurityEventCreate(
                    event_type="csrf_attempt",
                    severity="high",
                    user_id=None,
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    description=f"CSRF token missing for {request.method} {request.url.path}",
                    metadata={
                        "method": request.method,
                        "path": request.url.path
                    }
                )

                await security_repo.create_security_event(event_data)
                await db.commit()
        except Exception as e:
            print(f"Error logging CSRF attempt: {e}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds headers like:
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    - Content-Security-Policy
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers to response"""
        response = await call_next(request)

        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection: Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strict-Transport-Security: Force HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy: Restrict resource loading
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )

        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Control browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


class SuspiciousActivityDetectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detecting suspicious activity patterns.

    Monitors for:
    - Rapid requests (potential DDoS)
    - Unusual request patterns
    - Abnormal endpoints access
    """

    def __init__(self, app):
        super().__init__(app)
        self.request_tracking = {}  # In production, use Redis

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Monitor for suspicious activity"""
        client_ip = self._get_client_ip(request)

        # Track request rate (simplified)
        current_time = int(asyncio.get_event_loop().time())

        if client_ip not in self.request_tracking:
            self.request_tracking[client_ip] = []

        # Add current request
        self.request_tracking[client_ip].append(current_time)

        # Clean old entries (older than 60 seconds)
        self.request_tracking[client_ip] = [
            t for t in self.request_tracking[client_ip]
            if current_time - t < 60
        ]

        # Check for rapid requests (> 100 per minute)
        if len(self.request_tracking[client_ip]) > 100:
            asyncio.create_task(
                self._log_ddos_attempt(client_ip)
            )

            # Optionally block or throttle
            # return Response(
            #     content='{"detail": "Too many requests"}',
            #     status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            #     media_type="application/json"
            # )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _log_ddos_attempt(self, ip_address: str):
        """Log potential DDoS attempt"""
        try:
            async with AsyncSessionLocal() as db:
                from app.repositories.security_repository import SecurityRepository
                security_repo = SecurityRepository(db)

                event_data = SecurityEventCreate(
                    event_type="ddos_attempt",
                    severity="critical",
                    user_id=None,
                    ip_address=ip_address,
                    user_agent=None,
                    description=f"Potential DDoS attack detected from {ip_address}",
                    metadata={"request_rate": "high"}
                )

                await security_repo.create_security_event(event_data)
                await db.commit()
        except Exception as e:
            print(f"Error logging DDoS attempt: {e}")
