# Electric Meter Ledger System - Implementation Plan

## 1. Overview

The central data object is a ledger of recorded readings from electric utility meters. The system tracks four meters (gg, sg, total, unmetered) connected to properties, with users who can monitor their consumption.

## 2. Data Model

### Core Entities

#### Property
Represents a real estate property (fastighet in Swedish).

**Fields:**
- `id`: UUID (Primary Key)
- `name`: VARCHAR(255) NOT NULL
- `address`: TEXT
- `created_at`: TIMESTAMP NOT NULL DEFAULT NOW()
- `updated_at`: TIMESTAMP NOT NULL DEFAULT NOW()

#### Meter
Four types per property: gg, sg, total, and unmetered (derived).

**Fields:**
- `id`: UUID (Primary Key)
- `property_id`: UUID (Foreign Key → Property.id) NOT NULL
- `meter_type`: ENUM('gg', 'sg', 'total', 'unmetered') NOT NULL
- `is_derived`: BOOLEAN DEFAULT FALSE (TRUE for 'unmetered')
- `created_at`: TIMESTAMP NOT NULL DEFAULT NOW()
- `updated_at`: TIMESTAMP NOT NULL DEFAULT NOW()

**Constraints:**
- UNIQUE(property_id, meter_type) - One meter of each type per property

#### Reading (The Ledger)
Core data object storing meter readings with dual timestamps.

**Fields:**
- `id`: UUID (Primary Key)
- `meter_id`: UUID (Foreign Key → Meter.id) NOT NULL
- `value`: DECIMAL(10, 2) NOT NULL
- `read_at`: TIMESTAMP NOT NULL - When the reading was actually taken
- `created_at`: TIMESTAMP NOT NULL DEFAULT NOW() - When added to database
- `updated_at`: TIMESTAMP NOT NULL DEFAULT NOW()

**Indexes:**
- INDEX(meter_id, read_at) - For efficient time-series queries

#### User
Users associated with a property who can monitor meters.

**Fields:**
- `id`: UUID (Primary Key)
- `property_id`: UUID (Foreign Key → Property.id) NOT NULL
- `name`: VARCHAR(255) NOT NULL
- `email`: VARCHAR(255) UNIQUE NOT NULL
- `phone_number`: VARCHAR(20) NULLABLE
- `default_meter_id`: UUID (Foreign Key → Meter.id) NULLABLE
- `created_at`: TIMESTAMP NOT NULL DEFAULT NOW()
- `updated_at`: TIMESTAMP NOT NULL DEFAULT NOW()

### Entity Relationships

```
Property (1) ──────< (N) Meter
   │                     │
   │                     │
   │                     └───< (N) Reading
   │
   └───────────< (N) User
                     │
                     └──> (0..1) Meter (default_meter)
```

## 3. Business Logic

### Derived Meter Calculation

The `unmetered` meter is calculated as:
```
unmetered = total - gg - sg
```

**Implementation approach:**
- Application layer calculation (in service layer)
- Cannot add readings directly to unmetered meters
- Automatically calculated when querying readings
- Optionally stored as actual readings for historical tracking

### Reading Validation Rules

1. Cannot add readings for derived meters directly (unmetered)
2. `read_at` cannot be in the future
3. `read_at` should not predate the last reading (warning, not error)
4. Value must be non-negative
5. Value should typically be monotonically increasing (warning if not)

### Meter Initialization

When a property is created:
1. Automatically create 4 meters (gg, sg, total, unmetered)
2. Mark unmetered as `is_derived = true`
3. All meters active and ready for readings

## 4. Technology Stack

### Database
**PostgreSQL** - Chosen for:
- Excellent time-series support
- Strong ACID guarantees (critical for ledgers)
- UUID native support
- Advanced indexing capabilities

### ORM & Database Tools
- **SQLAlchemy 2.0** - Async ORM
- **asyncpg** - Async PostgreSQL driver
- **Alembic** - Database migrations

### API Framework
- **FastAPI** (already in use)
- **Pydantic** v2 (already in use) - Request/response validation

## 5. API Endpoints

### Properties
```
POST   /api/properties                      Create property
GET    /api/properties                      List all properties
GET    /api/properties/{id}                 Get property details
PUT    /api/properties/{id}                 Update property
DELETE /api/properties/{id}                 Delete property
POST   /api/properties/{id}/initialize-meters  Create initial 4 meters (if needed)
```

### Meters
```
GET    /api/properties/{id}/meters          List property meters
GET    /api/meters/{id}                     Get meter details
GET    /api/meters/{id}/readings            Get meter readings (paginated, filterable)
```

### Readings (The Ledger)
```
POST   /api/meters/{id}/readings            Add new reading
POST   /api/properties/{id}/readings        Add readings for multiple meters (bulk)
GET    /api/readings                        List all readings (with filters)
GET    /api/readings/{id}                   Get specific reading
PUT    /api/readings/{id}                   Update reading
DELETE /api/readings/{id}                   Delete reading
```

### Users
```
POST   /api/users                           Create user
GET    /api/users                           List all users
GET    /api/users/{id}                      Get user details
PUT    /api/users/{id}                      Update user
DELETE /api/users/{id}                      Delete user
PUT    /api/users/{id}/default-meter        Set default meter
```

### Analytics/Derived Endpoints
```
GET    /api/properties/{id}/consumption     Calculate consumption over period
GET    /api/meters/{id}/stats               Get meter statistics (min, max, avg, etc.)
GET    /api/properties/{id}/current-readings  Get latest reading for all meters
```

## 6. Implementation Phases

### Phase 1: Database Setup
**Files to create/modify:**
- `app/core/config.py` - Add database URL configuration
- `app/core/database.py` - Database session management
- `pyproject.toml` - Add dependencies
- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Migration environment

**Tasks:**
1. Add SQLAlchemy, asyncpg, alembic dependencies
2. Configure database connection string
3. Create async session factory
4. Initialize Alembic
5. Set up database connection lifecycle

### Phase 2: Models
**Files to create:**
- `app/models/property.py` - Property SQLAlchemy model
- `app/models/meter.py` - Meter SQLAlchemy model
- `app/models/reading.py` - Reading SQLAlchemy model
- `app/models/user.py` - User SQLAlchemy model
- `app/models/__init__.py` - Export all models

**Files to create (Pydantic schemas):**
- `app/schemas/property.py` - PropertyCreate, PropertyUpdate, PropertyResponse
- `app/schemas/meter.py` - MeterCreate, MeterUpdate, MeterResponse
- `app/schemas/reading.py` - ReadingCreate, ReadingUpdate, ReadingResponse
- `app/schemas/user.py` - UserCreate, UserUpdate, UserResponse
- `app/schemas/__init__.py` - Export all schemas

**Tasks:**
1. Define SQLAlchemy models with relationships
2. Create Alembic migration for initial schema
3. Define Pydantic schemas for API validation
4. Add `from_orm` support for responses

### Phase 3: Services (Business Logic)
**Files to create:**
- `app/services/property_service.py` - Property CRUD, meter initialization
- `app/services/meter_service.py` - Meter CRUD, reading queries
- `app/services/reading_service.py` - Reading CRUD, derived calculations
- `app/services/user_service.py` - User CRUD
- `app/services/__init__.py` - Export all services

**Key service methods:**

**PropertyService:**
- `create_property(data)` - Create property and initialize meters
- `get_property(id)` - Get property with meters
- `list_properties(skip, limit)` - Paginated list
- `update_property(id, data)` - Update property
- `delete_property(id)` - Delete property (cascade)

**MeterService:**
- `get_meters_by_property(property_id)` - List property meters
- `get_meter(id)` - Get meter details
- `get_meter_readings(meter_id, start_date, end_date, skip, limit)` - Query readings

**ReadingService:**
- `create_reading(meter_id, value, read_at)` - Add reading with validation
- `create_bulk_readings(readings)` - Bulk insert
- `calculate_derived_reading(property_id, timestamp)` - Calculate unmetered
- `get_reading(id)` - Get specific reading
- `update_reading(id, data)` - Update reading
- `delete_reading(id)` - Delete reading

**UserService:**
- `create_user(data)` - Create user
- `get_user(id)` - Get user details
- `list_users(property_id, skip, limit)` - List users
- `update_user(id, data)` - Update user
- `set_default_meter(user_id, meter_id)` - Set default meter
- `delete_user(id)` - Delete user

### Phase 4: API Routes
**Files to create:**
- `app/api/routes/properties.py` - Property endpoints
- `app/api/routes/meters.py` - Meter endpoints
- `app/api/routes/readings.py` - Reading endpoints
- `app/api/routes/users.py` - User endpoints

**Files to modify:**
- `app/main.py` - Register new routers

**Tasks:**
1. Implement all CRUD endpoints
2. Add request validation with Pydantic
3. Add response models
4. Add error handling
5. Add OpenAPI documentation strings

### Phase 5: Testing
**Files to create:**
- `tests/conftest.py` - Test fixtures, test database
- `tests/test_property_service.py` - Property service tests
- `tests/test_meter_service.py` - Meter service tests
- `tests/test_reading_service.py` - Reading service tests
- `tests/test_user_service.py` - User service tests
- `tests/test_api_properties.py` - Property API tests
- `tests/test_api_meters.py` - Meter API tests
- `tests/test_api_readings.py` - Reading API tests
- `tests/test_api_users.py` - User API tests

**Test scenarios:**
1. CRUD operations for all entities
2. Derived meter calculations
3. Reading validation (future dates, negative values)
4. Cascading deletes
5. Relationship constraints
6. Pagination
7. Bulk operations

### Phase 6: Documentation & Polish
**Files to modify:**
- `README.md` - Add usage instructions, API examples
- `app/api/routes/*.py` - Enhance OpenAPI descriptions

**Tasks:**
1. Add comprehensive OpenAPI descriptions
2. Add example requests/responses
3. Document environment variables
4. Add database setup instructions
5. Create sample data script

## 7. Database Schema Diagram

```
┌─────────────────────────────┐
│        Property             │
├─────────────────────────────┤
│ id (PK)                     │
│ name                        │
│ address                     │
│ created_at                  │
│ updated_at                  │
└──────────┬──────────────────┘
           │
           │ 1:N
           │
     ┌─────┴─────────────────┐
     │                       │
     ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│     Meter       │    │      User        │
├─────────────────┤    ├──────────────────┤
│ id (PK)         │    │ id (PK)          │
│ property_id(FK) │    │ property_id (FK) │
│ meter_type      │◄───┤ default_meter_id │
│ is_derived      │    │ name             │
│ created_at      │    │ email            │
│ updated_at      │    │ phone_number     │
└────────┬────────┘    │ created_at       │
         │             │ updated_at       │
         │ 1:N         └──────────────────┘
         │
         ▼
┌─────────────────┐
│    Reading      │
├─────────────────┤
│ id (PK)         │
│ meter_id (FK)   │
│ value           │
│ read_at         │  ← When reading was made
│ created_at      │  ← When added to DB
│ updated_at      │
└─────────────────┘
```

## 8. Sample Data

### Example Property with Complete Data

```json
{
  "property": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Storgatan 15",
    "address": "Storgatan 15, 111 51 Stockholm, Sweden",
    "created_at": "2026-01-10T10:00:00Z",
    "updated_at": "2026-01-10T10:00:00Z"
  },
  "meters": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "property_id": "550e8400-e29b-41d4-a716-446655440000",
      "meter_type": "gg",
      "is_derived": false,
      "created_at": "2026-01-10T10:00:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "property_id": "550e8400-e29b-41d4-a716-446655440000",
      "meter_type": "sg",
      "is_derived": false,
      "created_at": "2026-01-10T10:00:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "property_id": "550e8400-e29b-41d4-a716-446655440000",
      "meter_type": "total",
      "is_derived": false,
      "created_at": "2026-01-10T10:00:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440004",
      "property_id": "550e8400-e29b-41d4-a716-446655440000",
      "meter_type": "unmetered",
      "is_derived": true,
      "created_at": "2026-01-10T10:00:00Z"
    }
  ],
  "readings": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "meter_id": "550e8400-e29b-41d4-a716-446655440001",
      "value": 12345.67,
      "read_at": "2026-01-10T08:00:00Z",
      "created_at": "2026-01-10T14:30:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440011",
      "meter_id": "550e8400-e29b-41d4-a716-446655440002",
      "value": 8765.43,
      "read_at": "2026-01-10T08:00:00Z",
      "created_at": "2026-01-10T14:30:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440012",
      "meter_id": "550e8400-e29b-41d4-a716-446655440003",
      "value": 25000.00,
      "read_at": "2026-01-10T08:00:00Z",
      "created_at": "2026-01-10T14:30:00Z"
    }
  ],
  "derived_reading": {
    "meter_type": "unmetered",
    "calculated_value": 3888.90,
    "calculation": "25000.00 - 12345.67 - 8765.43 = 3888.90"
  },
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "property_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "phone_number": "+46701234567",
      "default_meter_id": "550e8400-e29b-41d4-a716-446655440001",
      "created_at": "2026-01-10T11:00:00Z"
    }
  ]
}
```

## 9. Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Database | PostgreSQL | Time-series support, ACID guarantees, UUID support |
| ORM | SQLAlchemy 2.0 | Async support, mature, excellent FastAPI integration |
| Primary Keys | UUID | Better for distributed systems, no sequence conflicts |
| Derived Meter | Application layer calculation | Clearer logic, easier to test, more flexible |
| Timestamps | Dual (created_at & read_at) | Audit trail + actual reading time tracking |
| Property Term | "Property" | Clear English equivalent to "fastighet" |
| Meter Types | ENUM | Prevents invalid types, clear domain constraints |
| Reading Value | DECIMAL(10,2) | Precise for financial/billing calculations |
| Cascade Deletes | Yes (Property → Meters → Readings) | Maintains referential integrity |

## 10. Environment Variables

Required environment variables (to be added to `.env`):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/electric

# Application
PROJECT_NAME=Electric
VERSION=0.1.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Optional: Database connection pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

## 11. Dependencies to Add

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.12.0",
    "pydantic-settings>=2.8.2",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.15.0",
]
```

## 12. Migration Strategy

### Initial Migration
```bash
# Initialize alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema: property, meter, reading, user"

# Apply migration
alembic upgrade head
```

### Future Migrations
- Use Alembic for all schema changes
- Always create migrations, never manual SQL
- Test migrations on development database first
- Keep migrations reversible when possible

## 13. Future Enhancements

### Phase 2 Features (Post-MVP)
- **Multi-tenancy**: Support multiple organizations
- **Authentication & Authorization**: User login, role-based access
- **Historical Archiving**: Move old readings to archive tables
- **Analytics Dashboard**: Consumption trends, forecasting
- **Alerts & Notifications**: Unusual consumption, missing readings
- **Data Export**: CSV/Excel export of readings
- **Billing Integration**: Calculate costs based on readings
- **Mobile API**: Optimize endpoints for mobile apps
- **Real-time Updates**: WebSocket support for live readings
- **Data Validation**: More sophisticated anomaly detection

### Technical Improvements
- **Caching**: Redis for frequently accessed data
- **Background Jobs**: Celery for async processing
- **API Versioning**: /api/v1/, /api/v2/
- **Rate Limiting**: Prevent API abuse
- **Monitoring**: Prometheus metrics, health checks
- **Logging**: Structured logging with correlation IDs

## 14. Success Criteria

The implementation is complete when:

1. ✓ All 4 entities (Property, Meter, Reading, User) are modeled and migrated
2. ✓ CRUD operations work for all entities via API
3. ✓ Derived meter (unmetered) calculations are correct
4. ✓ Dual timestamps (created_at, read_at) are captured
5. ✓ Users can be associated with properties and default meters
6. ✓ Phone numbers are optional and stored correctly
7. ✓ All relationships and cascades work correctly
8. ✓ Test coverage >80%
9. ✓ API documentation is complete in Swagger UI
10. ✓ README has setup and usage instructions
