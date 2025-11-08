# CelebraTech API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8000/api/v1`
**Authentication:** Bearer Token (JWT)

## Table of Contents

1. [Authentication](#authentication)
2. [Events](#events)
3. [Vendors](#vendors)
4. [Bookings](#bookings)
5. [Payments](#payments)
6. [Integration Hub](#integration-hub)
7. [Performance Monitoring](#performance-monitoring)
8. [Security](#security)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)

---

## Authentication

### Register User

```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "full_name": "John Doe",
  "password": "SecurePassword123!"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Login

```http
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Get Current User

```http
GET /auth/me
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "full_name": "John Doe",
  "role": "user"
}
```

---

## Events

### Create Event

```http
POST /events
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "Wedding Celebration",
  "description": "Beautiful wedding ceremony",
  "event_type": "wedding",
  "start_date": "2025-06-15T14:00:00Z",
  "end_date": "2025-06-15T22:00:00Z",
  "location": "Grand Hotel Ballroom",
  "budget": 50000.00,
  "guest_count": 150
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "title": "Wedding Celebration",
  "event_type": "wedding",
  "start_date": "2025-06-15T14:00:00Z",
  "status": "draft",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### List Events

```http
GET /events?status=upcoming&limit=20&offset=0
Authorization: Bearer {token}
```

**Query Parameters:**
- `status`: Filter by status (draft, upcoming, ongoing, completed, cancelled)
- `event_type`: Filter by type (wedding, corporate, birthday, etc.)
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Wedding Celebration",
      "event_type": "wedding",
      "start_date": "2025-06-15T14:00:00Z",
      "status": "upcoming"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Get Event Details

```http
GET /events/{event_id}
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "title": "Wedding Celebration",
  "description": "Beautiful wedding ceremony",
  "event_type": "wedding",
  "start_date": "2025-06-15T14:00:00Z",
  "end_date": "2025-06-15T22:00:00Z",
  "location": "Grand Hotel Ballroom",
  "budget": 50000.00,
  "guest_count": 150,
  "status": "upcoming",
  "organizer": {
    "id": "uuid",
    "full_name": "John Doe"
  }
}
```

### Update Event

```http
PUT /events/{event_id}
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "Updated Title",
  "guest_count": 175
}
```

**Response:** `200 OK`

### Delete Event

```http
DELETE /events/{event_id}
Authorization: Bearer {token}
```

**Response:** `204 No Content`

---

## Vendors

### List Vendors

```http
GET /vendors?category=catering&limit=20
Authorization: Bearer {token}
```

**Query Parameters:**
- `category`: Filter by category (catering, photography, venue, etc.)
- `service_area`: Filter by location
- `pricing_range`: Filter by price ($, $$, $$$, $$$$)
- `rating_min`: Minimum rating (1-5)
- `limit`: Number of results

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "business_name": "Gourmet Catering Co.",
      "category": "catering",
      "rating": 4.8,
      "pricing_range": "$$$",
      "service_area": "New York"
    }
  ],
  "total": 1
}
```

### Get Vendor Details

```http
GET /vendors/{vendor_id}
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "business_name": "Gourmet Catering Co.",
  "category": "catering",
  "description": "Premium catering services...",
  "rating": 4.8,
  "total_reviews": 156,
  "pricing_range": "$$$",
  "service_area": "New York",
  "services": ["Wedding Catering", "Corporate Events"],
  "portfolio": ["image1.jpg", "image2.jpg"]
}
```

---

## Integration Hub

### Create Integration

```http
POST /integrations
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "integration_type": "payment",
  "provider": "stripe",
  "credentials": {
    "api_key": "sk_test_...",
    "publishable_key": "pk_test_..."
  },
  "config": {
    "currency": "USD",
    "auto_capture": true
  }
}
```

**Response:** `201 Created`

### OAuth Authorization

```http
POST /integrations/oauth/authorize
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "provider": "google_calendar",
  "redirect_uri": "https://app.example.com/callback",
  "scope": ["calendar.readonly", "calendar.events"]
}
```

**Response:** `200 OK`
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "random_state_token"
}
```

### Create Webhook

```http
POST /integrations/webhooks
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "event_type": "event.created",
  "url": "https://your-app.com/webhooks/events",
  "secret": "webhook_secret_key"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "event_type": "event.created",
  "url": "https://your-app.com/webhooks/events",
  "active": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

## Performance Monitoring

### Record Metric

```http
POST /performance/metrics
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "metric_type": "api_latency",
  "metric_value": 125.5,
  "tags": {
    "endpoint": "/api/v1/events",
    "method": "GET"
  }
}
```

**Response:** `201 Created`

### Get Performance Dashboard

```http
GET /performance/dashboard
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "system_health": {
    "status": "healthy",
    "components": {
      "database": {"status": "healthy"},
      "redis": {"status": "healthy"},
      "api": {"status": "healthy"}
    }
  },
  "api_metrics": {
    "avg_latency_ms": 145.2,
    "p95_latency_ms": 280.5,
    "throughput_rps": 125.3
  },
  "cache_metrics": {
    "hit_rate": 82.5,
    "total_hits": 15420,
    "total_misses": 3280
  }
}
```

### Get System Health

```http
GET /performance/health
Authorization: Bearer {token}
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "avg_query_time_ms": 15.2
    },
    "redis": {
      "status": "healthy",
      "hit_rate": 85.3
    },
    "api": {
      "status": "healthy",
      "avg_response_time_ms": 142.8
    }
  }
}
```

---

## Security

### Get Security Dashboard

```http
GET /security/dashboard
Authorization: Bearer {token}
Requires: Admin role
```

**Response:** `200 OK`
```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "security_score": 87.5,
  "threat_level": "low",
  "active_threats": 2,
  "recent_events": [
    {
      "event_type": "failed_login",
      "severity": "medium",
      "ip_address": "192.168.1.100",
      "occurred_at": "2025-01-01T00:00:00Z"
    }
  ],
  "blocked_ips_count": 5,
  "rate_limit_violations": 12,
  "recommendations": [
    "Security posture is good. Continue monitoring."
  ]
}
```

### Detect Threats

```http
POST /security/threats/detect?ip_address=192.168.1.100
Authorization: Bearer {token}
Requires: Admin role
```

**Response:** `200 OK`
```json
{
  "is_threat": true,
  "threat_level": "high",
  "threat_types": ["sql_injection", "brute_force"],
  "confidence_score": 0.85,
  "details": {
    "risk_score": 85,
    "event_count": 15,
    "is_blacklisted": false
  },
  "recommended_action": "BLOCK: Immediately block this IP address"
}
```

### Add IP to Blacklist

```http
POST /security/blacklist
Authorization: Bearer {token}
Requires: Admin role
```

**Request Body:**
```json
{
  "ip_address": "192.168.1.100",
  "reason": "Multiple SQL injection attempts",
  "blocked_until": null
}
```

**Response:** `201 Created`

### Check Password Strength

```http
POST /security/password/check-strength
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "password": "MyPassword123!"
}
```

**Response:** `200 OK`
```json
{
  "strength": "strong",
  "score": 85,
  "feedback": ["Consider adding more special characters"],
  "meets_requirements": true
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2025-01-01T00:00:00Z"
}
```

### Common Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no content to return |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

---

## Rate Limiting

**Default Limits:**
- 60 requests per minute per IP
- 1000 requests per hour per IP
- 10,000 requests per day per user

**Rate Limit Headers:**
```
X-RateLimit-Limit-Minute: 60
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Hour: 892
```

**Rate Limit Exceeded Response:**
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Pagination

List endpoints support pagination:

```http
GET /events?limit=20&offset=40
```

**Response includes pagination metadata:**
```json
{
  "items": [...],
  "total": 156,
  "limit": 20,
  "offset": 40,
  "has_next": true,
  "has_prev": true
}
```

---

## Webhooks

Webhooks are signed with HMAC-SHA256. Verify signatures:

**Webhook Headers:**
```
X-Webhook-Signature: hmac_sha256_signature
X-Event-Type: event.created
X-Delivery-Id: uuid
```

**Webhook Payload:**
```json
{
  "event_type": "event.created",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    "event_id": "uuid",
    "title": "Wedding Celebration"
  }
}
```

**Verify Signature (Python):**
```python
import hmac
import hashlib
import json

def verify_webhook(payload, signature, secret):
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    expected_sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_sig)
```

---

## SDK Examples

### Python

```python
import requests

class CelebraTechAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def create_event(self, event_data):
        response = requests.post(
            f"{self.base_url}/events",
            json=event_data,
            headers=self.headers
        )
        return response.json()

    def list_events(self, status=None, limit=20):
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = requests.get(
            f"{self.base_url}/events",
            params=params,
            headers=self.headers
        )
        return response.json()

# Usage
api = CelebraTechAPI("http://localhost:8000/api/v1", "your_token")
events = api.list_events(status="upcoming")
```

### JavaScript/TypeScript

```typescript
class CelebraTechAPI {
  constructor(
    private baseUrl: string,
    private token: string
  ) {}

  private async request(endpoint: string, options: RequestInit = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        "Authorization": `Bearer ${this.token}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async createEvent(eventData: any) {
    return this.request("/events", {
      method: "POST",
      body: JSON.stringify(eventData),
    });
  }

  async listEvents(params: { status?: string; limit?: number } = {}) {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/events?${query}`);
  }
}

// Usage
const api = new CelebraTechAPI("http://localhost:8000/api/v1", "your_token");
const events = await api.listEvents({ status: "upcoming" });
```

---

## Testing

Use the provided test credentials for development:

**Test User:**
- Email: `test@celebratech.com`
- Password: `TestPassword123!`

**Test Admin:**
- Email: `admin@celebratech.com`
- Password: `AdminPassword123!`

**Test Environment:**
- Base URL: `http://localhost:8000/api/v1`
- Interactive Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Support

- Documentation: https://docs.celebratech.com
- API Status: https://status.celebratech.com
- Support Email: support@celebratech.com
- GitHub: https://github.com/celebratech/api

---

**Last Updated:** January 2025
**API Version:** 1.0.0
