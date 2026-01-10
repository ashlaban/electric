# Electric Meter Reading System - Usage Guide

## Overview

This is an electric utility meter reading ledger system that tracks consumption across properties with physical and virtual meters.

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Run Database Migrations

The database is already initialized. If you need to reset it:

```bash
rm electric.db
uv run alembic upgrade head
```

### 3. Seed Sample Data (Optional)

```bash
uv run python scripts/seed_data.py
```

### 4. Start the Server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Core Concepts

### Property

A real estate property that contains meters and users. When created, automatically gets 4 meters:
- **total** (physical main meter)
- **gg** (physical submeter)
- **sg** (physical submeter)
- **unmetered** (virtual meter, calculated as total - gg - sg)

### Meter Types

1. **Physical Main** - The main building meter (total consumption)
2. **Physical Submeter** - Individual circuit/section meters (gg, sg)
3. **Virtual** - Calculated meters (unmetered)

### Meter Readings

- Readings can be **added, updated, and deleted**
- Updates allow correcting typos (e.g., when sending readings via text)
- Timestamps: Both `reading_timestamp` (when reading was taken) and `created_at` (when entered)
- Validation ensures readings are monotonically increasing

### Users

- Associated with a property
- Can have an optional phone number
- Can have a default meter assigned

## API Examples

### Create a Property

```bash
curl -X POST http://localhost:8000/api/properties \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Building",
    "address": "123 Main St"
  }'
```

Response includes property ID. The property will automatically have 4 meters created.

### List Meters for a Property

```bash
curl http://localhost:8000/api/properties/{property_id}/meters
```

### Add a Meter Reading

```bash
curl -X POST http://localhost:8000/api/meters/{meter_id}/readings \
  -H "Content-Type: application/json" \
  -d '{
    "reading_value": 12345.67,
    "reading_timestamp": "2026-01-10T14:30:00Z",
    "notes": "Monthly reading"
  }'
```

### Update a Reading (Correct an Error)

```bash
curl -X PATCH http://localhost:8000/api/readings/{reading_id} \
  -H "Content-Type: application/json" \
  -d '{
    "reading_value": 12345.77,
    "notes": "Corrected typo"
  }'
```

### Get Readings for a Meter

```bash
curl http://localhost:8000/api/meters/{meter_id}/readings
```

Optional query parameters:
- `start_date`: Filter readings after this date
- `end_date`: Filter readings before this date
- `skip`: Pagination offset
- `limit`: Max results (default 100)

### Get Virtual Meter Readings

For the unmetered (virtual) meter, get calculated readings:

```bash
curl http://localhost:8000/api/meters/{unmetered_meter_id}/calculated-readings
```

This returns readings calculated as: `total - gg - sg` for matching timestamps.

### Create a User

```bash
curl -X POST http://localhost:8000/api/properties/{property_id}/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "phone_number": "+46701234567",
    "default_meter_id": "{meter_id}"
  }'
```

## Database Schema

### Properties Table
- id (UUID)
- name
- address
- created_at, updated_at

### Meters Table
- id (UUID)
- property_id (FK)
- meter_code (e.g., "total", "gg", "sg", "unmetered")
- meter_type (physical_main, physical_submeter, virtual)
- description
- unit (default: "kWh")
- is_active
- created_at, updated_at

### Meter Readings Table (The Ledger)
- id (UUID)
- meter_id (FK)
- reading_value (Decimal)
- reading_timestamp (when reading was taken)
- created_at (when entered in DB)
- updated_at (when last modified)
- created_by_user_id (FK, nullable)
- notes

### Users Table
- id (UUID)
- property_id (FK)
- name
- phone_number
- default_meter_id (FK, nullable)
- is_active
- created_at, updated_at

## Running Tests

```bash
# Run all tests
uv run poe test

# Run with coverage
uv run poe test-cov

# Run all checks (lint, format, typecheck, test)
uv run poe check
```

## Data Validation

The system enforces several validation rules:

1. **Reading values must be positive**
2. **Readings must be monotonically increasing** (new reading >= previous reading)
3. **Reading timestamps cannot be in the future**
4. **Cannot add readings directly to virtual meters** (they are calculated)
5. **Cannot add readings to inactive meters**
6. **Meter codes must be unique within a property**
7. **Default meter must belong to the same property as the user**

## Virtual Meter Calculation

The `unmetered` meter is a virtual meter calculated from the three physical meters:

```
unmetered_reading = total_reading - gg_reading - sg_reading
```

Readings are only calculated for timestamps where all three physical meters have readings.

## Development

### Database Migrations

Create a new migration after changing models:

```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Rollback last migration:

```bash
uv run alembic downgrade -1
```

### Code Quality

```bash
# Format code
uv run poe format

# Lint code
uv run poe lint

# Type check
uv run poe typecheck
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

See the main README.md and METER_SYSTEM_PLAN.md for detailed architecture and implementation information.
