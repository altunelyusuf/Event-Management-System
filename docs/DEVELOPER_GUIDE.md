# CelebraTech Developer Guide

Complete guide for developers working on the CelebraTech Event Management System.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Architecture Overview](#architecture-overview)
3. [Development Setup](#development-setup)
4. [Code Structure](#code-structure)
5. [Adding New Features](#adding-new-features)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (optional, for caching)
- Node.js 18+ (for frontend, if applicable)
- Git

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/Event-Management-System.git
cd Event-Management-System

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the application:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Architecture Overview

### Tech Stack

**Backend:**
- **Framework:** FastAPI (Python async web framework)
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL with UUID primary keys
- **Caching:** Redis (multi-tier L1/L2 caching)
- **Authentication:** JWT (JSON Web Tokens)
- **Validation:** Pydantic v2
- **Testing:** Pytest with async support
- **API Docs:** OpenAPI/Swagger

**Architecture Pattern:**
- Clean Architecture with 3-layer separation:
  1. **API Layer** (`app/api/v1/`) - HTTP endpoints
  2. **Service Layer** (`app/services/`) - Business logic
  3. **Repository Layer** (`app/repositories/`) - Data access

```
┌─────────────────────────────────────────────┐
│             API Layer (FastAPI)              │
│         - Routing                            │
│         - Request/Response handling          │
│         - Authentication                     │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│          Service Layer (Business Logic)      │
│         - Validation                         │
│         - Orchestration                      │
│         - Authorization                      │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│      Repository Layer (Data Access)          │
│         - Database queries                   │
│         - Data transformations               │
│         - Transaction management             │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│           Database (PostgreSQL)              │
└─────────────────────────────────────────────┘
```

---

## Development Setup

### Environment Configuration

Create `.env` file in `backend/` directory:

```env
# Application
APP_NAME=CelebraTech
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=True

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/celebratech
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# File Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760  # 10MB
```

### Database Setup

```bash
# Create database
createdb celebratech

# Run migrations
alembic upgrade head

# Create test data (optional)
python scripts/seed_data.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests in parallel (faster)
pytest -n auto
```

---

## Code Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/           # API endpoints
│   │       ├── auth.py
│   │       ├── events.py
│   │       ├── vendors.py
│   │       └── ...
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration
│   │   ├── database.py   # Database connection
│   │   ├── security.py   # Auth utilities
│   │   └── auth.py       # Auth dependencies
│   ├── models/           # SQLAlchemy models
│   │   ├── user.py
│   │   ├── event.py
│   │   └── ...
│   ├── schemas/          # Pydantic schemas
│   │   ├── user.py
│   │   ├── event.py
│   │   └── ...
│   ├── services/         # Business logic
│   │   ├── event_service.py
│   │   ├── vendor_service.py
│   │   └── ...
│   ├── repositories/     # Data access
│   │   ├── event_repository.py
│   │   ├── vendor_repository.py
│   │   └── ...
│   ├── middleware/       # Custom middleware
│   │   ├── performance_middleware.py
│   │   └── security_middleware.py
│   └── main.py           # Application entry point
├── tests/                # Test files
│   ├── conftest.py       # Test fixtures
│   ├── test_auth.py
│   ├── test_events.py
│   └── ...
├── alembic/              # Database migrations
│   ├── versions/
│   └── env.py
├── requirements.txt      # Python dependencies
└── pytest.ini            # Pytest configuration
```

---

## Adding New Features

### Step-by-Step Guide

#### 1. Create Database Model

**File:** `app/models/example.py`

```python
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class Example(Base):
    """Example model"""
    __tablename__ = "examples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2. Create Database Migration

```bash
# Generate migration
alembic revision --autogenerate -m "Add example table"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

#### 3. Create Pydantic Schemas

**File:** `app/schemas/example.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ExampleCreate(BaseModel):
    """Schema for creating example"""
    title: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class ExampleUpdate(BaseModel):
    """Schema for updating example"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class ExampleResponse(BaseModel):
    """Schema for example response"""
    id: UUID
    title: str
    description: Optional[str]
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### 4. Create Repository Layer

**File:** `app/repositories/example_repository.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from uuid import UUID

from app.models.example import Example
from app.schemas.example import ExampleCreate, ExampleUpdate

class ExampleRepository:
    """Repository for example operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ExampleCreate, user_id: UUID) -> Example:
        """Create new example"""
        example = Example(
            title=data.title,
            description=data.description,
            user_id=user_id
        )

        self.db.add(example)
        await self.db.flush()
        return example

    async def get_by_id(self, example_id: UUID) -> Optional[Example]:
        """Get example by ID"""
        stmt = select(Example).where(Example.id == example_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, limit: int = 20) -> List[Example]:
        """Get examples by user"""
        stmt = select(Example).where(
            Example.user_id == user_id
        ).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, example_id: UUID, data: ExampleUpdate) -> Optional[Example]:
        """Update example"""
        stmt = update(Example).where(
            Example.id == example_id
        ).values(**data.dict(exclude_unset=True)).returning(Example)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, example_id: UUID) -> bool:
        """Delete example"""
        stmt = delete(Example).where(Example.id == example_id)
        result = await self.db.execute(stmt)
        return result.rowcount > 0
```

#### 5. Create Service Layer

**File:** `app/services/example_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List
from uuid import UUID

from app.repositories.example_repository import ExampleRepository
from app.schemas.example import ExampleCreate, ExampleUpdate, ExampleResponse
from app.models.user import User

class ExampleService:
    """Service for example operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExampleRepository(db)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    async def create(self, data: ExampleCreate, current_user: User) -> ExampleResponse:
        """Create new example"""
        example = await self.repo.create(data, current_user.id)
        await self.db.commit()
        return ExampleResponse.from_orm(example)

    async def get_by_id(self, example_id: UUID, current_user: User) -> ExampleResponse:
        """Get example by ID"""
        example = await self.repo.get_by_id(example_id)

        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Example not found"
            )

        # Check ownership
        if example.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this example"
            )

        return ExampleResponse.from_orm(example)

    async def list_user_examples(self, current_user: User, limit: int = 20) -> List[ExampleResponse]:
        """List user's examples"""
        examples = await self.repo.get_by_user(current_user.id, limit)
        return [ExampleResponse.from_orm(e) for e in examples]

    async def update(self, example_id: UUID, data: ExampleUpdate, current_user: User) -> ExampleResponse:
        """Update example"""
        # First check ownership
        await self.get_by_id(example_id, current_user)

        example = await self.repo.update(example_id, data)
        await self.db.commit()

        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Example not found"
            )

        return ExampleResponse.from_orm(example)

    async def delete(self, example_id: UUID, current_user: User) -> None:
        """Delete example"""
        # First check ownership
        await self.get_by_id(example_id, current_user)

        success = await self.repo.delete(example_id)
        await self.db.commit()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Example not found"
            )
```

#### 6. Create API Endpoints

**File:** `app/api/v1/example.py`

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.example_service import ExampleService
from app.schemas.example import ExampleCreate, ExampleUpdate, ExampleResponse

router = APIRouter(prefix="/examples", tags=["examples"])

async def get_example_service(db: AsyncSession = Depends(get_db)) -> ExampleService:
    """Get example service instance"""
    async with ExampleService(db) as service:
        yield service

@router.post("", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    data: ExampleCreate,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """Create new example"""
    return await service.create(data, current_user)

@router.get("", response_model=List[ExampleResponse])
async def list_examples(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """List user's examples"""
    return await service.list_user_examples(current_user, limit)

@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(
    example_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """Get example by ID"""
    return await service.get_by_id(example_id, current_user)

@router.put("/{example_id}", response_model=ExampleResponse)
async def update_example(
    example_id: UUID,
    data: ExampleUpdate,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """Update example"""
    return await service.update(example_id, data, current_user)

@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """Delete example"""
    await service.delete(example_id, current_user)
```

#### 7. Register Router

**File:** `app/main.py`

```python
# Import the new router
from app.api.v1 import example

# Register the router
app.include_router(example.router, prefix=settings.API_V1_PREFIX)
```

#### 8. Write Tests

**File:** `tests/test_example.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.unit
class TestExample:
    """Test example endpoints"""

    async def test_create_example(self, client: AsyncClient, auth_headers: dict):
        """Test creating example"""
        response = await client.post(
            "/api/v1/examples",
            headers=auth_headers,
            json={
                "title": "Test Example",
                "description": "Test description"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Example"

    async def test_list_examples(self, client: AsyncClient, auth_headers: dict):
        """Test listing examples"""
        # Create some examples first
        for i in range(3):
            await client.post(
                "/api/v1/examples",
                headers=auth_headers,
                json={"title": f"Example {i}"}
            )

        # List examples
        response = await client.get(
            "/api/v1/examples",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
```

---

## Testing

### Testing Strategy

1. **Unit Tests:** Test individual functions and methods
2. **Integration Tests:** Test interactions between components
3. **API Tests:** Test HTTP endpoints
4. **Performance Tests:** Test response times and throughput

### Writing Tests

```python
# tests/test_example.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
@pytest.mark.unit
async def test_example_function():
    """Test specific function"""
    result = await some_function()
    assert result == expected_value

@pytest.mark.asyncio
@pytest.mark.integration
async def test_example_endpoint(
    client: AsyncClient,
    test_db_session: AsyncSession,
    auth_headers: dict
):
    """Test API endpoint"""
    response = await client.get(
        "/api/v1/examples",
        headers=auth_headers
    )

    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance(client: AsyncClient, performance_timer):
    """Test performance"""
    performance_timer.start()
    response = await client.get("/api/v1/examples")
    performance_timer.stop()

    assert performance_timer.elapsed_ms() < 200
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific markers
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Parallel execution
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

---

## Best Practices

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public functions
- Keep functions small and focused
- Use descriptive variable names

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: Add new feature"

# Push to remote
git push origin feature/new-feature

# Create pull request for review
```

### Commit Message Format

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

### Security Best Practices

1. Never commit secrets or credentials
2. Use environment variables for configuration
3. Validate all user input
4. Use parameterized queries (SQLAlchemy handles this)
5. Implement rate limiting
6. Enable CORS properly
7. Use HTTPS in production
8. Keep dependencies updated

### Performance Best Practices

1. Use async/await consistently
2. Implement caching for expensive operations
3. Use database indexes appropriately
4. Paginate large result sets
5. Use connection pooling
6. Monitor performance metrics
7. Profile slow endpoints

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)

---

**Last Updated:** January 2025
