# Electric Meter Reading System - Implementation Plan

## Overview
A utility meter reading ledger system for tracking electric consumption across properties with physical and virtual meters.

## Domain Model

### Core Entities

#### 1. Property
- **Description**: A real estate property (Swedish: "fastighet") that contains one or more meters
- **Attributes**:
  - `id`: UUID (primary key)
  - `name`: String (e.g., "Building A", "Main Property")
  - `address`: String (optional)
  - `created_at`: DateTime
  - `updated_at`: DateTime

#### 2. Meter
- **Description**: Represents both physical meters and virtual/derived meters
- **Types**:
  - **Physical meters**: Hardware devices that record actual consumption
    - `total`: Main meter (measures total consumption)
    - `gg`: Physical submeter (specific circuit/section)
    - `sg`: Physical submeter (specific circuit/section)
  - **Virtual meters**: Calculated from other meters
    - `unmetered`: Derived as `total - gg - sg`
- **Attributes**:
  - `id`: UUID (primary key)
  - `property_id`: UUID (foreign key to Property)
  - `meter_code`: String (e.g., "gg", "sg", "total", "unmetered")
  - `meter_type`: Enum ["physical_main", "physical_submeter", "virtual"]
  - `description`: String (optional, e.g., "Ground floor circuit")
  - `unit`: String (default: "kWh")
  - `is_active`: Boolean (default: True)
  - `created_at`: DateTime
  - `updated_at`: DateTime
- **Business Rules**:
  - Each property must have exactly one "total" meter
  - Virtual meters cannot have readings directly added; they are calculated
  - Meter codes must be unique within a property

#### 3. MeterReading (Central Ledger)
- **Description**: The core data object - immutable ledger of all meter readings
- **Attributes**:
  - `id`: UUID (primary key)
  - `meter_id`: UUID (foreign key to Meter)
  - `reading_value`: Decimal (the actual meter reading, e.g., 12345.67 kWh)
  - `reading_timestamp`: DateTime (when the reading was physically taken)
  - `created_at`: DateTime (when the record was added to the database)
  - `created_by_user_id`: UUID (foreign key to User, optional)
  - `notes`: String (optional, for any comments about the reading)
- **Business Rules**:
  - Readings are immutable (append-only ledger)
  - Cannot add readings directly to virtual meters
  - Reading value must be monotonically increasing for cumulative meters
  - `reading_timestamp` must not be in the future

#### 4. User
- **Description**: Users who can view and add meter readings
- **Attributes**:
  - `id`: UUID (primary key)
  - `property_id`: UUID (foreign key to Property)
  - `name`: String
  - `phone_number`: String (optional, format: E.164 recommended)
  - `default_meter_id`: UUID (foreign key to Meter, optional)
  - `is_active`: Boolean (default: True)
  - `created_at`: DateTime
  - `updated_at`: DateTime
- **Business Rules**:
  - Default meter must belong to the same property as the user
  - Phone number should be validated if provided

## Database Schema

### Technology Choice
- **Database**: PostgreSQL (recommended for production) or SQLite (for development)
- **ORM**: SQLAlchemy 2.x with async support
- **Migrations**: Alembic

### Table Relationships

```
properties (1) ----< (N) meters
                    |
                    └----< (N) meter_readings

properties (1) ----< (N) users

meters (1) ----< (N) users (default_meter)
users (1) ----< (N) meter_readings (created_by)
```

### Indexes
- `meter_readings.meter_id` (for efficient queries by meter)
- `meter_readings.reading_timestamp` (for time-based queries)
- `meter_readings.created_at` (for audit/recent entries)
- `meters.property_id` (for property-based queries)
- `meters.meter_code` + `meters.property_id` (unique constraint)
- `users.property_id` (for property-based queries)
- `users.phone_number` (for lookup, if used for authentication)

## API Design

### RESTful Endpoints

#### Properties
- `GET /api/properties` - List all properties
- `GET /api/properties/{property_id}` - Get property details
- `POST /api/properties` - Create new property
- `PATCH /api/properties/{property_id}` - Update property
- `DELETE /api/properties/{property_id}` - Soft delete property

#### Meters
- `GET /api/properties/{property_id}/meters` - List meters for a property
- `GET /api/meters/{meter_id}` - Get meter details
- `POST /api/properties/{property_id}/meters` - Create new meter
- `PATCH /api/meters/{meter_id}` - Update meter
- `DELETE /api/meters/{meter_id}` - Deactivate meter

#### Meter Readings (Ledger)
- `GET /api/meters/{meter_id}/readings` - List readings for a meter
  - Query params: `start_date`, `end_date`, `limit`, `offset`
- `GET /api/readings/{reading_id}` - Get specific reading
- `POST /api/meters/{meter_id}/readings` - Add new reading (only for physical meters)
- `GET /api/properties/{property_id}/readings` - Get all readings for a property
  - Includes calculated readings for virtual meters

#### Virtual Meter Calculations
- `GET /api/meters/{meter_id}/calculated-readings` - Get calculated readings for virtual meter
  - Query params: `start_date`, `end_date`, `limit`, `offset`
- `GET /api/properties/{property_id}/consumption-summary` - Get consumption breakdown
  - Returns current readings for all meters including unmetered

#### Users
- `GET /api/properties/{property_id}/users` - List users for a property
- `GET /api/users/{user_id}` - Get user details
- `POST /api/properties/{property_id}/users` - Create new user
- `PATCH /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Deactivate user

## Data Validation Rules

### MeterReading Validation
1. Reading value must be positive
2. For cumulative meters, new reading must be >= previous reading
3. Reading timestamp cannot be in the future
4. Reading timestamp should be after the previous reading timestamp (warning, not error)
5. Cannot add readings to inactive meters
6. Cannot add readings directly to virtual meters

### Meter Validation
1. Meter code must be unique within a property
2. Each property must have exactly one "total" meter (enforced at application level)
3. Virtual meter formulas must reference existing meters

### User Validation
1. Phone number format validation (if provided)
2. Default meter must belong to the same property
3. Property must exist and be active

## Business Logic

### Virtual Meter Calculation (Unmetered)

For a given timestamp range, calculate unmetered consumption:

```python
unmetered_reading = total_reading - gg_reading - sg_reading
```

**Implementation approach**:
1. Query readings for all three physical meters within the time range
2. Align timestamps (use exact matches or interpolation)
3. Calculate differences
4. Return as virtual readings

### Consumption Calculation

For displaying consumption over a period:

```python
consumption = current_reading - previous_reading
```

## Implementation Steps

### Phase 1: Database Setup
1. Add dependencies to `pyproject.toml`:
   - SQLAlchemy >= 2.0
   - Alembic >= 1.13
   - asyncpg (for PostgreSQL) or aiosqlite (for SQLite)
   - psycopg2-binary (for Alembic migrations)
2. Create database configuration in `app/core/config.py`
3. Set up database connection in `app/core/database.py`
4. Initialize Alembic for migrations

### Phase 2: Database Models
1. Create SQLAlchemy models in `app/db/models/`:
   - `property.py` - Property model
   - `meter.py` - Meter model with enums
   - `meter_reading.py` - MeterReading model
   - `user.py` - User model
2. Create initial migration
3. Apply migration to create tables

### Phase 3: Pydantic Schemas
1. Create request/response schemas in `app/models/`:
   - `property.py` - PropertyCreate, PropertyUpdate, PropertyResponse
   - `meter.py` - MeterCreate, MeterUpdate, MeterResponse
   - `meter_reading.py` - MeterReadingCreate, MeterReadingResponse
   - `user.py` - UserCreate, UserUpdate, UserResponse
   - `consumption.py` - ConsumptionSummary, VirtualReading

### Phase 4: Service Layer
1. Create business logic in `app/services/`:
   - `property_service.py` - Property CRUD operations
   - `meter_service.py` - Meter CRUD + validation
   - `meter_reading_service.py` - Reading CRUD + validation + calculations
   - `user_service.py` - User CRUD operations
2. Implement virtual meter calculation logic
3. Add data validation rules

### Phase 5: API Routes
1. Create route handlers in `app/api/routes/`:
   - `properties.py` - Property endpoints
   - `meters.py` - Meter endpoints
   - `readings.py` - Reading endpoints
   - `users.py` - User endpoints
2. Register routes in `app/main.py`
3. Add proper error handling and status codes

### Phase 6: Testing
1. Create unit tests for services
2. Create integration tests for API endpoints
3. Add test fixtures for sample data
4. Test virtual meter calculations
5. Test validation rules

### Phase 7: Seed Data
1. Create seed script to initialize a property with four meters
2. Add sample users
3. Add sample readings for testing

### Phase 8: Documentation
1. Add OpenAPI/Swagger documentation to endpoints
2. Create usage examples
3. Document virtual meter calculation logic

## Initial Data Setup

When a new property is created, automatically create four meters:

1. **total** (physical_main)
   - Description: "Main meter - total consumption"
   - Unit: "kWh"

2. **gg** (physical_submeter)
   - Description: "GG circuit submeter"
   - Unit: "kWh"

3. **sg** (physical_submeter)
   - Description: "SG circuit submeter"
   - Unit: "kWh"

4. **unmetered** (virtual)
   - Description: "Unmetered consumption (total - gg - sg)"
   - Unit: "kWh"

## Example API Flows

### Flow 1: Add a new reading
```
POST /api/meters/{gg_meter_id}/readings
{
  "reading_value": 12345.67,
  "reading_timestamp": "2026-01-10T14:30:00Z",
  "notes": "Monthly reading"
}
```

### Flow 2: Get consumption summary
```
GET /api/properties/{property_id}/consumption-summary?start_date=2026-01-01&end_date=2026-01-10

Response:
{
  "property_id": "...",
  "period": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-01-10T23:59:59Z"
  },
  "meters": [
    {
      "meter_code": "total",
      "start_reading": 50000.00,
      "end_reading": 50500.00,
      "consumption": 500.00,
      "unit": "kWh"
    },
    {
      "meter_code": "gg",
      "start_reading": 20000.00,
      "end_reading": 20200.00,
      "consumption": 200.00,
      "unit": "kWh"
    },
    {
      "meter_code": "sg",
      "start_reading": 15000.00,
      "end_reading": 15150.00,
      "consumption": 150.00,
      "unit": "kWh"
    },
    {
      "meter_code": "unmetered",
      "start_reading": 15000.00,
      "end_reading": 15150.00,
      "consumption": 150.00,
      "unit": "kWh",
      "calculated": true
    }
  ]
}
```

## Security Considerations

1. **Authentication**: Add JWT or API key authentication (future phase)
2. **Authorization**: Users can only access their property's data
3. **Input Validation**: Strict validation on all inputs
4. **SQL Injection**: Prevented by using SQLAlchemy ORM
5. **Rate Limiting**: Add rate limiting to prevent abuse (future phase)

## Performance Considerations

1. **Indexing**: Proper indexes on foreign keys and timestamp columns
2. **Pagination**: All list endpoints support pagination
3. **Caching**: Consider caching latest readings (future optimization)
4. **Batch Operations**: Support bulk reading imports (future enhancement)

## Future Enhancements

1. WebSocket support for real-time reading updates
2. Data export functionality (CSV, Excel)
3. Graphing and visualization endpoints
4. Automated reading imports from smart meters
5. Alerts for unusual consumption patterns
6. Multi-property support for users
7. Historical data analytics
8. Mobile app support
