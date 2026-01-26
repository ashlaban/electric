# Electric

A FastAPI web application built with Python 3.11 and managed by uv.

## Features

- ⚡ FastAPI framework for high-performance APIs
- 🐍 Python 3.11
- 📦 Dependency management with uv
- ✅ Pre-configured testing with pytest
- 🔍 Linting with ruff
- 🔬 Type checking with ty (Astral)
- 🪝 Pre-commit hooks for automatic formatting
- 🛠️ Task automation with poethepoet
- 🏗️ Modular project structure
- 🤖 GitHub Actions CI/CD

## Project Structure

```
electric/
├── app/
│   ├── api/
│   │   └── routes/         # API route handlers
│   │       ├── auth.py     # Authentication endpoints
│   │       ├── health.py   # Health check endpoint
│   │       ├── meters.py   # Meter management endpoints
│   │       ├── properties.py # Property management endpoints
│   │       └── readings.py # Meter reading endpoints
│   ├── core/
│   │   └── config.py       # Application configuration
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── main.py             # FastAPI application entry point
├── tests/                  # Test suite
├── pyproject.toml          # Project dependencies
└── README.md
```

## Requirements

- Python 3.11
- uv (package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd electric
```

2. Install dependencies:
```bash
uv sync
```

3. Install pre-commit hooks (recommended):
```bash
uv run poe pre-commit-install
```

This will automatically run code formatting and linting checks before each commit.

## Running the Application

### Development Mode

Run the server with auto-reload:

```bash
uv run python -m app.main
```

Or using uvicorn directly:

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Commands

This project uses [poethepoet](https://poethepoet.natn.io/) for task automation. All commands are defined in `pyproject.toml`.

### Testing

Run tests:

```bash
uv run poe test
```

Run tests with coverage:

```bash
uv run poe test-cov
```

### Code Quality

Run linting:

```bash
uv run poe lint
```

Auto-fix linting issues:

```bash
uv run poe lint-fix
```

Check code formatting:

```bash
uv run poe format-check
```

Auto-format code:

```bash
uv run poe format
```

Run type checking:

```bash
uv run poe typecheck
```

### Run All Checks

Run all checks (lint, format, typecheck, test):

```bash
uv run poe check
```

### Pre-commit Hooks

Run pre-commit hooks manually on all files:

```bash
uv run poe pre-commit
```

Install pre-commit hooks (if not done during setup):

```bash
uv run poe pre-commit-install
```

Once installed, pre-commit will automatically run:
- Ruff linting (with auto-fix)
- Ruff formatting
- Trailing whitespace removal
- End-of-file fixer
- YAML validation
- Large file checks
- Merge conflict detection

## API Endpoints

### General
- `GET /` - Root endpoint with welcome message
- `GET /api/health` - Health check endpoint

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and receive a JWT access token

### Properties (`/api/properties`)
- `POST /api/properties/` - Create a new property with its main meter
- `GET /api/properties/` - List all properties (with pagination)
- `GET /api/properties/{property_id}` - Get a property by ID
- `PATCH /api/properties/{property_id}` - Update a property
- `GET /api/properties/{property_id}/meters` - Get all meters for a property
- `POST /api/properties/{property_id}/users/{user_id}` - Associate a user with a property
- `DELETE /api/properties/{property_id}/users/{user_id}` - Remove user association

### Meters (`/api/meters`)
- `POST /api/meters/main` - Create a main meter for a property
- `POST /api/meters/submeter` - Create a submeter for a property
- `GET /api/meters/{meter_id}` - Get a meter by ID
- `PATCH /api/meters/{meter_id}` - Update a meter

### Meter Readings (`/api/readings`)
- `POST /api/readings/` - Record a single meter reading
- `POST /api/readings/bulk` - Record multiple meter readings at once
- `GET /api/readings/property/{property_id}/summary` - Get readings at a specific timestamp
- `GET /api/readings/property/{property_id}/latest` - Get most recent readings
- `GET /api/readings/meter/{meter_id}/history` - Get reading history (with pagination)

## Configuration

Configuration can be customized using environment variables or a `.env` file:

- `PROJECT_NAME` - Project name (default: "Electric")
- `VERSION` - API version (default: "0.1.0")
- `DEBUG` - Debug mode (default: True)
- `HOST` - Server host (default: "0.0.0.0")
- `PORT` - Server port (default: 8000)

## Managing Dependencies

Add a new dependency:

```bash
uv add <package-name>
```

Add a dev dependency:

```bash
uv add --dev <package-name>
```

Remove a dependency:

```bash
uv remove <package-name>
```

## License

TBD
