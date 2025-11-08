"""
Security Hardening Repository
Sprint 23: Security Hardening

Repository layer for security events, rate limiting, IP management, and threat detection.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_, desc, update
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from app.models.security import SecurityEvent, RateLimitEntry, IPBlacklist
from app.schemas.security import (
    SecurityEventCreate, SecurityEventQuery,
    IPBlacklistCreate
)


class SecurityRepository:
    """Repository for security operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Security Event Operations
    # ========================================================================

    async def create_security_event(
        self,
        event_data: SecurityEventCreate
    ) -> SecurityEvent:
        """Create a security event"""
        event = SecurityEvent(
            event_type=event_data.event_type,
            severity=event_data.severity,
            user_id=event_data.user_id,
            ip_address=event_data.ip_address,
            user_agent=event_data.user_agent,
            description=event_data.description,
            metadata=event_data.metadata,
            occurred_at=datetime.utcnow()
        )

        self.db.add(event)
        await self.db.flush()
        return event

    async def get_security_event(
        self,
        event_id: UUID
    ) -> Optional[SecurityEvent]:
        """Get security event by ID"""
        stmt = select(SecurityEvent).where(SecurityEvent.id == event_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def query_security_events(
        self,
        query: SecurityEventQuery
    ) -> List[SecurityEvent]:
        """Query security events with filters"""
        stmt = select(SecurityEvent)

        # Apply filters
        filters = []
        if query.event_type:
            filters.append(SecurityEvent.event_type == query.event_type)
        if query.severity:
            filters.append(SecurityEvent.severity == query.severity)
        if query.user_id:
            filters.append(SecurityEvent.user_id == query.user_id)
        if query.ip_address:
            filters.append(SecurityEvent.ip_address == query.ip_address)
        if query.start_date:
            filters.append(SecurityEvent.occurred_at >= query.start_date)
        if query.end_date:
            filters.append(SecurityEvent.occurred_at <= query.end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Order by most recent
        stmt = stmt.order_by(desc(SecurityEvent.occurred_at))

        # Apply limit
        stmt = stmt.limit(query.limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_event_stats(
        self,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get security event statistics"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        # Total events
        total_stmt = select(func.count()).select_from(SecurityEvent).where(
            SecurityEvent.occurred_at >= since_date
        )
        total_result = await self.db.execute(total_stmt)
        total_events = total_result.scalar() or 0

        # Events by severity
        severity_stmt = select(
            SecurityEvent.severity,
            func.count(SecurityEvent.id)
        ).where(
            SecurityEvent.occurred_at >= since_date
        ).group_by(SecurityEvent.severity)

        severity_result = await self.db.execute(severity_stmt)
        events_by_severity = {row[0]: row[1] for row in severity_result.all()}

        # Events by type
        type_stmt = select(
            SecurityEvent.event_type,
            func.count(SecurityEvent.id)
        ).where(
            SecurityEvent.occurred_at >= since_date
        ).group_by(SecurityEvent.event_type)

        type_result = await self.db.execute(type_stmt)
        events_by_type = {row[0]: row[1] for row in type_result.all()}

        # Top attacking IPs
        ip_stmt = select(
            SecurityEvent.ip_address,
            func.count(SecurityEvent.id).label('count')
        ).where(
            SecurityEvent.occurred_at >= since_date
        ).group_by(SecurityEvent.ip_address).order_by(desc('count')).limit(10)

        ip_result = await self.db.execute(ip_stmt)
        top_attacking_ips = [
            {"ip": row[0], "count": row[1]}
            for row in ip_result.all()
        ]

        return {
            "total_events": total_events,
            "events_by_severity": events_by_severity,
            "events_by_type": events_by_type,
            "top_attacking_ips": top_attacking_ips
        }

    async def get_events_by_ip(
        self,
        ip_address: str,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get security events for a specific IP"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(SecurityEvent).where(
            and_(
                SecurityEvent.ip_address == ip_address,
                SecurityEvent.occurred_at >= since_date
            )
        ).order_by(desc(SecurityEvent.occurred_at)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_user(
        self,
        user_id: UUID,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get security events for a specific user"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(SecurityEvent).where(
            and_(
                SecurityEvent.user_id == user_id,
                SecurityEvent.occurred_at >= since_date
            )
        ).order_by(desc(SecurityEvent.occurred_at)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_old_events(
        self,
        days_to_keep: int = 90
    ) -> int:
        """Delete old security events"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        stmt = delete(SecurityEvent).where(
            SecurityEvent.occurred_at < cutoff_date
        )

        result = await self.db.execute(stmt)
        return result.rowcount

    # ========================================================================
    # Rate Limiting Operations
    # ========================================================================

    async def check_rate_limit(
        self,
        identifier: str,
        resource: str,
        window_minutes: int = 1,
        max_requests: int = 60
    ) -> Tuple[bool, int]:
        """
        Check if rate limit is exceeded.

        Returns: (allowed, remaining_requests)
        """
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        # Get or create rate limit entry
        stmt = select(RateLimitEntry).where(
            and_(
                RateLimitEntry.identifier == identifier,
                RateLimitEntry.resource == resource,
                RateLimitEntry.window_end > datetime.utcnow()
            )
        )

        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            # Create new entry
            entry = RateLimitEntry(
                identifier=identifier,
                resource=resource,
                request_count=1,
                window_start=datetime.utcnow(),
                window_end=datetime.utcnow() + timedelta(minutes=window_minutes)
            )
            self.db.add(entry)
            await self.db.flush()
            return True, max_requests - 1

        # Check if limit exceeded
        if entry.request_count >= max_requests:
            return False, 0

        # Increment counter
        entry.request_count += 1
        remaining = max_requests - entry.request_count

        return True, remaining

    async def increment_rate_limit(
        self,
        identifier: str,
        resource: str,
        window_minutes: int = 1
    ) -> int:
        """Increment rate limit counter"""
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        stmt = select(RateLimitEntry).where(
            and_(
                RateLimitEntry.identifier == identifier,
                RateLimitEntry.resource == resource,
                RateLimitEntry.window_end > datetime.utcnow()
            )
        )

        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry:
            entry.request_count += 1
            return entry.request_count
        else:
            # Create new entry
            entry = RateLimitEntry(
                identifier=identifier,
                resource=resource,
                request_count=1,
                window_start=datetime.utcnow(),
                window_end=datetime.utcnow() + timedelta(minutes=window_minutes)
            )
            self.db.add(entry)
            await self.db.flush()
            return 1

    async def get_rate_limit_stats(
        self,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        # Total entries (requests)
        total_stmt = select(func.count()).select_from(RateLimitEntry).where(
            RateLimitEntry.window_start >= since_date
        )
        total_result = await self.db.execute(total_stmt)
        total_requests = total_result.scalar() or 0

        # Entries that exceeded limit (placeholder - would need threshold config)
        # For now, consider entries with high counts
        blocked_stmt = select(func.count()).select_from(RateLimitEntry).where(
            and_(
                RateLimitEntry.window_start >= since_date,
                RateLimitEntry.request_count > 60  # Default threshold
            )
        )
        blocked_result = await self.db.execute(blocked_stmt)
        blocked_requests = blocked_result.scalar() or 0

        # Top limited IPs/users
        top_stmt = select(
            RateLimitEntry.identifier,
            func.sum(RateLimitEntry.request_count).label('total_count')
        ).where(
            RateLimitEntry.window_start >= since_date
        ).group_by(RateLimitEntry.identifier).order_by(desc('total_count')).limit(10)

        top_result = await self.db.execute(top_stmt)
        top_limited = [
            {"identifier": row[0], "count": row[1]}
            for row in top_result.all()
        ]

        return {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "block_rate": (blocked_requests / total_requests * 100) if total_requests > 0 else 0,
            "top_limited": top_limited
        }

    async def clear_expired_rate_limits(self) -> int:
        """Clear expired rate limit entries"""
        stmt = delete(RateLimitEntry).where(
            RateLimitEntry.window_end <= datetime.utcnow()
        )

        result = await self.db.execute(stmt)
        return result.rowcount

    # ========================================================================
    # IP Blacklist Operations
    # ========================================================================

    async def add_ip_to_blacklist(
        self,
        blacklist_data: IPBlacklistCreate
    ) -> IPBlacklist:
        """Add IP to blacklist"""
        # Check if already exists
        existing_stmt = select(IPBlacklist).where(
            IPBlacklist.ip_address == blacklist_data.ip_address
        )
        existing_result = await self.db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Update existing entry
            existing.reason = blacklist_data.reason
            existing.blocked_until = blacklist_data.blocked_until
            return existing

        # Create new entry
        entry = IPBlacklist(
            ip_address=blacklist_data.ip_address,
            reason=blacklist_data.reason,
            blocked_until=blacklist_data.blocked_until,
            created_at=datetime.utcnow()
        )

        self.db.add(entry)
        await self.db.flush()
        return entry

    async def remove_ip_from_blacklist(
        self,
        ip_address: str
    ) -> bool:
        """Remove IP from blacklist"""
        stmt = delete(IPBlacklist).where(IPBlacklist.ip_address == ip_address)
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def is_ip_blacklisted(
        self,
        ip_address: str
    ) -> bool:
        """Check if IP is blacklisted"""
        stmt = select(IPBlacklist).where(
            and_(
                IPBlacklist.ip_address == ip_address,
                or_(
                    IPBlacklist.blocked_until.is_(None),
                    IPBlacklist.blocked_until > datetime.utcnow()
                )
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_blacklisted_ips(
        self,
        include_expired: bool = False
    ) -> List[IPBlacklist]:
        """Get all blacklisted IPs"""
        stmt = select(IPBlacklist)

        if not include_expired:
            stmt = stmt.where(
                or_(
                    IPBlacklist.blocked_until.is_(None),
                    IPBlacklist.blocked_until > datetime.utcnow()
                )
            )

        stmt = stmt.order_by(desc(IPBlacklist.created_at))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def clear_expired_blacklist_entries(self) -> int:
        """Clear expired blacklist entries"""
        stmt = delete(IPBlacklist).where(
            and_(
                IPBlacklist.blocked_until.isnot(None),
                IPBlacklist.blocked_until <= datetime.utcnow()
            )
        )

        result = await self.db.execute(stmt)
        return result.rowcount

    # ========================================================================
    # Threat Detection Operations
    # ========================================================================

    async def detect_brute_force_attack(
        self,
        identifier: str,
        time_window_minutes: int = 15,
        threshold: int = 5
    ) -> bool:
        """Detect brute force attack pattern"""
        since_date = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        # Count failed login attempts
        stmt = select(func.count()).select_from(SecurityEvent).where(
            and_(
                or_(
                    SecurityEvent.event_type == 'failed_login',
                    SecurityEvent.event_type == 'brute_force_attempt'
                ),
                or_(
                    SecurityEvent.ip_address == identifier,
                    SecurityEvent.user_id == identifier
                ),
                SecurityEvent.occurred_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        count = result.scalar() or 0

        return count >= threshold

    async def detect_suspicious_activity(
        self,
        ip_address: str,
        hours_back: int = 1
    ) -> Dict[str, Any]:
        """Detect suspicious activity patterns"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        # Get all events for this IP
        events = await self.get_events_by_ip(ip_address, hours_back=hours_back)

        # Analyze patterns
        event_types = [e.event_type for e in events]
        severity_counts = {}
        for event in events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1

        # Calculate risk score
        risk_score = 0
        if 'sql_injection_attempt' in event_types:
            risk_score += 40
        if 'xss_attempt' in event_types:
            risk_score += 30
        if 'brute_force_attempt' in event_types:
            risk_score += 35
        if 'unauthorized_access' in event_types:
            risk_score += 25
        if severity_counts.get('critical', 0) > 0:
            risk_score += 30
        if len(events) > 100:  # High activity
            risk_score += 20

        risk_score = min(risk_score, 100)

        is_suspicious = risk_score > 50

        return {
            "is_suspicious": is_suspicious,
            "risk_score": risk_score,
            "event_count": len(events),
            "event_types": list(set(event_types)),
            "severity_counts": severity_counts,
            "indicators": self._generate_threat_indicators(events, risk_score)
        }

    def _generate_threat_indicators(
        self,
        events: List[SecurityEvent],
        risk_score: int
    ) -> List[str]:
        """Generate threat indicators from events"""
        indicators = []

        event_types = [e.event_type for e in events]

        if 'sql_injection_attempt' in event_types:
            indicators.append("SQL injection attempts detected")
        if 'xss_attempt' in event_types:
            indicators.append("Cross-site scripting attempts detected")
        if 'brute_force_attempt' in event_types:
            indicators.append("Brute force attack pattern detected")
        if len(events) > 100:
            indicators.append("Unusually high request rate")
        if risk_score > 70:
            indicators.append("High-risk activity pattern")

        return indicators

    # ========================================================================
    # Analytics Operations
    # ========================================================================

    async def get_failed_login_count(
        self,
        identifier: str,
        hours_back: int = 1
    ) -> int:
        """Get failed login count for user/IP"""
        since_date = datetime.utcnow() - timedelta(hours=hours_back)

        stmt = select(func.count()).select_from(SecurityEvent).where(
            and_(
                SecurityEvent.event_type == 'failed_login',
                or_(
                    SecurityEvent.ip_address == identifier,
                    SecurityEvent.user_id == UUID(identifier) if self._is_uuid(identifier) else False
                ),
                SecurityEvent.occurred_at >= since_date
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    def _is_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID"""
        try:
            UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
