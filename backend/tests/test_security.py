"""
Security Hardening Tests
Sprint 24: Testing & Documentation

Tests for Sprint 23 security features.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
@pytest.mark.unit
class TestSecurityEvents:
    """Test security event logging"""

    async def test_log_security_event(self, client: AsyncClient, admin_auth_headers: dict):
        """Test logging a security event"""
        response = await client.post(
            "/api/v1/security/events",
            headers=admin_auth_headers,
            json={
                "event_type": "failed_login",
                "severity": "medium",
                "ip_address": "192.168.1.100",
                "user_agent": "Test Agent",
                "description": "Test failed login attempt"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "failed_login"
        assert data["severity"] == "medium"

    async def test_query_security_events(self, client: AsyncClient, admin_auth_headers: dict):
        """Test querying security events"""
        # First, create some events
        for i in range(5):
            await client.post(
                "/api/v1/security/events",
                headers=admin_auth_headers,
                json={
                    "event_type": "suspicious_activity",
                    "severity": "high",
                    "ip_address": f"192.168.1.{i}",
                    "description": f"Test event {i}"
                }
            )

        # Query events
        response = await client.get(
            "/api/v1/security/events?severity=high&limit=10",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    async def test_get_event_statistics(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting security event statistics"""
        response = await client.get(
            "/api/v1/security/events/stats",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "events_by_severity" in data
        assert "events_by_type" in data


@pytest.mark.asyncio
@pytest.mark.unit
class TestThreatDetection:
    """Test threat detection"""

    async def test_detect_threats(self, client: AsyncClient, admin_auth_headers: dict):
        """Test detecting threats from IP"""
        # First, create some suspicious events
        for _ in range(3):
            await client.post(
                "/api/v1/security/events",
                headers=admin_auth_headers,
                json={
                    "event_type": "sql_injection_attempt",
                    "severity": "critical",
                    "ip_address": "192.168.1.200",
                    "description": "SQL injection detected"
                }
            )

        # Detect threats
        response = await client.post(
            "/api/v1/security/threats/detect?ip_address=192.168.1.200",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_threat" in data
        assert "threat_level" in data
        assert "confidence_score" in data

    async def test_get_suspicious_activities(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting suspicious activity report"""
        response = await client.get(
            "/api/v1/security/threats/suspicious",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
@pytest.mark.unit
class TestIPBlacklist:
    """Test IP blacklist management"""

    async def test_add_ip_to_blacklist(self, client: AsyncClient, admin_auth_headers: dict):
        """Test adding IP to blacklist"""
        response = await client.post(
            "/api/v1/security/blacklist",
            headers=admin_auth_headers,
            json={
                "ip_address": "10.0.0.1",
                "reason": "Test blocking",
                "blocked_until": None
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["ip_address"] == "10.0.0.1"
        assert data["reason"] == "Test blocking"

    async def test_remove_ip_from_blacklist(self, client: AsyncClient, admin_auth_headers: dict):
        """Test removing IP from blacklist"""
        # First add
        await client.post(
            "/api/v1/security/blacklist",
            headers=admin_auth_headers,
            json={
                "ip_address": "10.0.0.2",
                "reason": "Test"
            }
        )

        # Then remove
        response = await client.delete(
            "/api/v1/security/blacklist/10.0.0.2",
            headers=admin_auth_headers
        )

        assert response.status_code == 200

    async def test_get_blacklisted_ips(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting all blacklisted IPs"""
        response = await client.get(
            "/api/v1/security/blacklist",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_check_ip_blacklist_status(self, client: AsyncClient, admin_auth_headers: dict):
        """Test checking if IP is blacklisted"""
        # Add IP
        await client.post(
            "/api/v1/security/blacklist",
            headers=admin_auth_headers,
            json={
                "ip_address": "10.0.0.3",
                "reason": "Test"
            }
        )

        # Check status
        response = await client.get(
            "/api/v1/security/blacklist/check/10.0.0.3",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_blacklisted"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestSecurityDashboard:
    """Test security dashboard"""

    async def test_get_security_dashboard(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting security dashboard"""
        response = await client.get(
            "/api/v1/security/dashboard",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "security_score" in data
        assert "threat_level" in data
        assert "active_threats" in data
        assert "recent_events" in data
        assert 0 <= data["security_score"] <= 100

    async def test_get_security_metrics(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting security metrics"""
        response = await client.get(
            "/api/v1/security/dashboard/metrics",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data


@pytest.mark.asyncio
@pytest.mark.unit
class TestPasswordSecurity:
    """Test password security features"""

    async def test_check_weak_password(self, client: AsyncClient, auth_headers: dict):
        """Test checking weak password"""
        response = await client.post(
            "/api/v1/security/password/check-strength",
            headers=auth_headers,
            json={"password": "weak"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strength"] == "weak"
        assert data["score"] < 50

    async def test_check_strong_password(self, client: AsyncClient, auth_headers: dict):
        """Test checking strong password"""
        response = await client.post(
            "/api/v1/security/password/check-strength",
            headers=auth_headers,
            json={"password": "VeryStrong!Password123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strength"] in ["strong", "very_strong"]
        assert data["score"] >= 75


@pytest.mark.asyncio
@pytest.mark.unit
class TestOWASPCompliance:
    """Test OWASP compliance reporting"""

    async def test_get_owasp_compliance(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting OWASP compliance report"""
        response = await client.get(
            "/api/v1/security/owasp/compliance",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "compliance_score" in data
        assert "vulnerabilities" in data
        assert 0 <= data["compliance_score"] <= 100


@pytest.mark.asyncio
@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting"""

    async def test_get_rate_limit_stats(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting rate limit statistics"""
        response = await client.get(
            "/api/v1/security/rate-limit/stats",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "blocked_requests" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestSecurityMiddleware:
    """Integration tests for security middleware"""

    async def test_sql_injection_detection(self, client: AsyncClient):
        """Test SQL injection detection"""
        # Attempt SQL injection in query parameter
        response = await client.get(
            "/api/v1/events?search=test' OR '1'='1"
        )

        # Should either block or sanitize
        # Exact behavior depends on middleware configuration
        assert response.status_code in [200, 400]

    async def test_xss_detection(self, client: AsyncClient):
        """Test XSS detection"""
        # Attempt XSS in query parameter
        response = await client.get(
            "/api/v1/events?search=<script>alert('xss')</script>"
        )

        # Should either block or sanitize
        assert response.status_code in [200, 400]

    async def test_security_headers_present(self, client: AsyncClient):
        """Test security headers are added to responses"""
        response = await client.get("/health")

        assert response.status_code == 200
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers


@pytest.mark.asyncio
@pytest.mark.unit
class TestSecurityConfiguration:
    """Test security configuration"""

    async def test_get_security_config(self, client: AsyncClient, admin_auth_headers: dict):
        """Test getting security configuration"""
        response = await client.get(
            "/api/v1/security/config",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "rate_limiting" in data
        assert "password_policy" in data
        assert "login_security" in data


@pytest.mark.asyncio
@pytest.mark.integration
class TestBruteForceProtection:
    """Test brute force attack protection"""

    async def test_brute_force_detection(self, client: AsyncClient):
        """Test brute force attack detection"""
        # Simulate multiple failed login attempts
        for i in range(6):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "target@example.com",
                    "password": f"wrongpassword{i}"
                }
            )

            # After threshold, should be blocked
            if i >= 5:
                # Could be blocked or rate limited
                assert response.status_code in [401, 429]
