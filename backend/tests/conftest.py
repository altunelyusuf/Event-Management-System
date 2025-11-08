"""
Test Configuration and Fixtures
Sprint 24: Testing & Documentation

Pytest configuration and shared fixtures for testing.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from datetime import datetime, timedelta
from uuid import uuid4

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.core.security import get_password_hash


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db_session: AsyncSession) -> User:
    """Create test user"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    return user


@pytest.fixture
async def admin_user(test_db_session: AsyncSession) -> User:
    """Create test admin user"""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_verified=True,
        role="admin",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    return user


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """Get authentication headers for test user"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123"
        }
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_auth_headers(client: AsyncClient, admin_user: User) -> dict:
    """Get authentication headers for admin user"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": admin_user.email,
            "password": "adminpassword123"
        }
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# Sample test data factories

@pytest.fixture
def sample_event_data():
    """Sample event data for testing"""
    return {
        "title": "Test Event",
        "description": "Test event description",
        "event_type": "wedding",
        "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "end_date": (datetime.utcnow() + timedelta(days=31)).isoformat(),
        "location": "Test Location",
        "budget": 10000.00,
        "guest_count": 100
    }


@pytest.fixture
def sample_vendor_data():
    """Sample vendor data for testing"""
    return {
        "business_name": "Test Vendor",
        "category": "catering",
        "description": "Test vendor description",
        "service_area": "Test City",
        "pricing_range": "$$",
        "contact_email": "vendor@example.com",
        "contact_phone": "+1234567890"
    }


@pytest.fixture
def sample_booking_data():
    """Sample booking data for testing"""
    return {
        "service_type": "catering",
        "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "guest_count": 100,
        "budget": 5000.00,
        "special_requirements": "Test requirements"
    }


# Mock data helpers

class MockData:
    """Helper class for generating mock test data"""

    @staticmethod
    def user_data(email: str = None, role: str = "user") -> dict:
        """Generate mock user data"""
        return {
            "email": email or f"user_{uuid4().hex[:8]}@example.com",
            "username": f"user_{uuid4().hex[:8]}",
            "full_name": "Test User",
            "password": "testpassword123",
            "role": role
        }

    @staticmethod
    def event_data(user_id: str = None) -> dict:
        """Generate mock event data"""
        return {
            "title": f"Test Event {uuid4().hex[:8]}",
            "description": "Test event description",
            "event_type": "wedding",
            "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=31)).isoformat(),
            "location": "Test Location",
            "budget": 10000.00,
            "guest_count": 100,
            "organizer_id": user_id
        }

    @staticmethod
    def vendor_data() -> dict:
        """Generate mock vendor data"""
        return {
            "business_name": f"Test Vendor {uuid4().hex[:8]}",
            "category": "catering",
            "description": "Test vendor description",
            "service_area": "Test City",
            "pricing_range": "$$"
        }


@pytest.fixture
def mock_data():
    """Provide MockData helper"""
    return MockData


# Pytest configuration

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Async test helpers

async def create_test_event(session: AsyncSession, user_id: str, **kwargs):
    """Helper to create test event"""
    from app.models.event import Event

    event_data = {
        "title": "Test Event",
        "description": "Test Description",
        "event_type": "wedding",
        "start_date": datetime.utcnow() + timedelta(days=30),
        "end_date": datetime.utcnow() + timedelta(days=31),
        "location": "Test Location",
        "organizer_id": user_id,
        **kwargs
    }

    event = Event(**event_data)
    session.add(event)
    await session.commit()
    await session.refresh(event)

    return event


async def create_test_vendor(session: AsyncSession, user_id: str, **kwargs):
    """Helper to create test vendor"""
    from app.models.vendor import Vendor

    vendor_data = {
        "business_name": "Test Vendor",
        "category": "catering",
        "description": "Test Description",
        "owner_id": user_id,
        **kwargs
    }

    vendor = Vendor(**vendor_data)
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    return vendor


# Performance testing utilities

@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

    return Timer()


# Coverage helpers

@pytest.fixture
def coverage_report():
    """Generate coverage report after tests"""
    # This would be configured with pytest-cov
    pass
