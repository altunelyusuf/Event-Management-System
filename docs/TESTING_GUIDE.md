# Testing Guide

Comprehensive testing guide for the CelebraTech Event Management System.

## Table of Contents

1. [Overview](#overview)
2. [Test Setup](#test-setup)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Test Coverage](#test-coverage)
6. [Continuous Integration](#continuous-integration)

---

## Overview

### Testing Strategy

Our testing pyramid consists of:

```
          /\
         /  \    E2E Tests (5%)
        /____\
       /      \   Integration Tests (15%)
      /________\
     /          \  Unit Tests (80%)
    /____________\
```

**Test Types:**
- **Unit Tests:** Test individual functions and methods in isolation
- **Integration Tests:** Test interactions between components
- **API Tests:** Test HTTP endpoints end-to-end
- **Performance Tests:** Test response times and throughput
- **Security Tests:** Test security features and vulnerabilities

### Test Coverage Goals

- Overall coverage: **> 80%**
- Critical paths: **> 95%**
- New code: **> 90%**

---

## Test Setup

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Optional: Install for parallel execution
pip install pytest-xdist
```

### Test Configuration

**File:** `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests (skip with -m "not slow")
    security: Security tests
    performance: Performance tests

addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings

filterwarnings =
    ignore::DeprecationWarning
```

### Test Database

Tests use an in-memory SQLite database for speed:

```python
# tests/conftest.py
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with very verbose output
pytest -vv

# Stop on first failure
pytest -x

# Show local variables on failures
pytest -l

# Run last failed tests
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Running Specific Tests

```bash
# Run specific file
pytest tests/test_auth.py

# Run specific class
pytest tests/test_auth.py::TestUserLogin

# Run specific test
pytest tests/test_auth.py::TestUserLogin::test_login_success

# Run tests matching pattern
pytest -k "login"

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"
pytest -m "unit and not slow"
```

### Parallel Execution

```bash
# Run tests in parallel (auto-detect CPUs)
pytest -n auto

# Run tests on 4 CPUs
pytest -n 4
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=app

# Generate HTML report
pytest --cov=app --cov-report=html

# Generate XML report (for CI)
pytest --cov=app --cov-report=xml

# Show missing lines
pytest --cov=app --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=80
```

---

## Writing Tests

### Test Structure

```python
# tests/test_example.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
@pytest.mark.unit
class TestExampleFeature:
    """Test example feature"""

    async def test_success_case(self):
        """Test successful operation"""
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = await some_function(input_data)

        # Assert
        assert result == expected_value

    async def test_error_case(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            await some_function(invalid_data)
```

### Unit Tests

Test individual functions without external dependencies:

```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_password_hashing():
    """Test password hashing"""
    from app.core.security import get_password_hash, verify_password

    password = "SecurePassword123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)
```

### Integration Tests

Test interactions between components:

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_event_with_tasks(
    client: AsyncClient,
    auth_headers: dict
):
    """Test creating event with tasks"""
    # Create event
    event_response = await client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={
            "title": "Test Event",
            "event_type": "wedding",
            "start_date": "2025-06-15T14:00:00Z"
        }
    )

    assert event_response.status_code == 201
    event_id = event_response.json()["id"]

    # Create task for event
    task_response = await client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={
            "event_id": event_id,
            "title": "Book venue",
            "due_date": "2025-05-01T00:00:00Z"
        }
    )

    assert task_response.status_code == 201

    # Verify task is linked to event
    tasks_response = await client.get(
        f"/api/v1/events/{event_id}/tasks",
        headers=auth_headers
    )

    assert tasks_response.status_code == 200
    assert len(tasks_response.json()) == 1
```

### API Tests

Test HTTP endpoints:

```python
@pytest.mark.asyncio
async def test_api_endpoint(client: AsyncClient, auth_headers: dict):
    """Test API endpoint"""
    response = await client.get(
        "/api/v1/events",
        headers=auth_headers,
        params={"limit": 10}
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
```

### Performance Tests

```python
@pytest.mark.asyncio
@pytest.mark.performance
async def test_api_response_time(
    client: AsyncClient,
    auth_headers: dict,
    performance_timer
):
    """Test API response time"""
    performance_timer.start()

    response = await client.get(
        "/api/v1/events",
        headers=auth_headers
    )

    performance_timer.stop()

    assert response.status_code == 200
    assert performance_timer.elapsed_ms() < 200
```

### Security Tests

```python
@pytest.mark.asyncio
@pytest.mark.security
async def test_unauthorized_access(client: AsyncClient):
    """Test unauthorized access is blocked"""
    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 401

@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection_protection(client: AsyncClient):
    """Test SQL injection is prevented"""
    response = await client.get(
        "/api/v1/events?search=test' OR '1'='1"
    )

    # Should not cause database error
    assert response.status_code in [200, 400]
```

### Fixtures

Use fixtures for common test setup:

```python
# tests/conftest.py

@pytest.fixture
async def test_user(test_db_session: AsyncSession) -> User:
    """Create test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("password123")
    )
    test_db_session.add(user)
    await test_db_session.commit()
    return user

@pytest.fixture
async def auth_token(client: AsyncClient, test_user: User) -> str:
    """Get authentication token"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "password123"
        }
    )
    return response.json()["access_token"]
```

### Parameterized Tests

Test multiple scenarios with one test:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("password,expected_strength", [
    ("weak", "weak"),
    ("Better123", "fair"),
    ("Strong!Pass123", "strong"),
    ("VeryStrong!Password123", "very_strong"),
])
async def test_password_strength(
    client: AsyncClient,
    auth_headers: dict,
    password: str,
    expected_strength: str
):
    """Test password strength validation"""
    response = await client.post(
        "/api/v1/security/password/check-strength",
        headers=auth_headers,
        json={"password": password}
    )

    assert response.status_code == 200
    assert response.json()["strength"] == expected_strength
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test with mocked external service"""
    with patch("app.services.email_service.send_email") as mock_send:
        mock_send.return_value = AsyncMock(return_value=True)

        # Test code that calls send_email
        result = await some_function()

        # Verify mock was called
        mock_send.assert_called_once()
        assert result is True
```

---

## Test Coverage

### Viewing Coverage

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Configuration

**File:** `.coveragerc`

```ini
[run]
source = app
omit =
    */tests/*
    */venv/*
    */__init__.py

[report]
precision = 2
show_missing = True
skip_covered = False

exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

### Coverage Targets

**Minimum Coverage by Component:**
- API Endpoints: 90%
- Services: 85%
- Repositories: 80%
- Models: 70%
- Utilities: 95%

---

## Continuous Integration

### GitHub Actions

**File:** `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        run: |
          cd backend
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

### Pre-commit Hooks

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        args: ["-x", "-v"]
        language: system
        pass_filenames: false
        always_run: true
```

---

## Best Practices

### DO's

✅ Write tests before or alongside code (TDD)
✅ Test one thing per test
✅ Use descriptive test names
✅ Follow Arrange-Act-Assert pattern
✅ Use fixtures for common setup
✅ Test both success and failure cases
✅ Test edge cases and boundaries
✅ Keep tests fast (< 1 second each)
✅ Make tests independent
✅ Use meaningful assertions

### DON'Ts

❌ Don't test implementation details
❌ Don't have tests depend on each other
❌ Don't use production database
❌ Don't skip error case testing
❌ Don't test third-party code
❌ Don't ignore flaky tests
❌ Don't commit commented-out tests
❌ Don't test getters/setters
❌ Don't mock everything

---

## Troubleshooting

### Common Issues

**Tests fail with database errors:**
```bash
# Ensure test database is clean
pytest --create-db
```

**Import errors:**
```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

**Async warnings:**
```python
# Add to pytest.ini
asyncio_mode = auto
```

**Slow tests:**
```bash
# Find slowest tests
pytest --durations=10

# Skip slow tests
pytest -m "not slow"
```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)
- [Async Testing](https://pytest-asyncio.readthedocs.io/)
- [Test Coverage](https://coverage.readthedocs.io/)

---

**Last Updated:** January 2025
