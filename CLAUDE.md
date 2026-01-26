# CLAUDE.md - AI Assistant Guide for Electric

This document provides essential context for AI assistants working with the Electric codebase.

## Project Overview

Electric is a FastAPI web application for building high-performance APIs. It uses modern Python 3.11 with comprehensive tooling for code quality, testing, and CI/CD.

**Tech Stack:**
- FastAPI (web framework)
- UV (package manager)
- Ruff (linter & formatter)
- ty (type checker)
- pytest (testing)
- poethepoet (task runner)

## Project Structure

```
electric/
├── app/                    # Main application package
│   ├── __init__.py         # Package init with version
│   ├── main.py             # FastAPI app entry point
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py     # Authentication endpoints
│   │       ├── health.py   # Health check endpoints
│   │       ├── meters.py   # Meter management endpoints
│   │       ├── properties.py # Property management endpoints
│   │       └── readings.py # Meter reading endpoints
│   ├── core/
│   │   ├── config.py       # Settings management (pydantic-settings)
│   │   └── database.py     # Database connection and session
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic schemas (request/response)
│   └── services/           # Business logic layer
├── tests/
│   └── test_main.py        # Integration tests
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI pipeline
├── pyproject.toml          # Project config, dependencies, tasks
├── pytest.ini              # Pytest configuration
├── .pre-commit-config.yaml # Pre-commit hooks
└── uv.lock                 # Dependency lock file
```

## Quick Commands

All commands use `uv run poe <task>`:

| Command | Description |
|---------|-------------|
| `uv run poe test` | Run tests with verbose output |
| `uv run poe test-cov` | Run tests with HTML coverage report |
| `uv run poe lint` | Run ruff linter |
| `uv run poe lint-fix` | Auto-fix lint issues |
| `uv run poe format` | Format code with ruff |
| `uv run poe format-check` | Check formatting without changes |
| `uv run poe typecheck` | Run type checker (ty) |
| `uv run poe check` | Run all checks (lint, format, typecheck, test) |
| `uv run poe pre-commit` | Run all pre-commit hooks |

**Run the dev server:**
```bash
uv run fastapi dev app/main.py
```

## Code Style

- **Line length:** 100 characters
- **Quotes:** Double quotes
- **Indent:** Spaces (4)
- **Type hints:** Required on all functions
- **Docstrings:** Required for modules and public functions

**Ruff rules enabled:** E, W, F, I (isort), N (naming), UP (pyupgrade), B (bugbear), C4 (comprehensions), SIM (simplify), TCH (type-checking)

## Testing

Tests are in `tests/` using pytest with async support:

```bash
uv run poe test        # Run all tests
uv run poe test-cov    # Run with coverage
```

- Use `TestClient` from FastAPI for endpoint tests
- Async mode is set to "auto" - pytest handles async functions automatically
- Test files: `test_*.py`, test functions: `test_*`

## CI Pipeline

GitHub Actions runs on all pushes and PRs:
1. Install dependencies (`uv sync`)
2. Lint check (`uv run poe lint`)
3. Format check (`uv run poe format-check`)
4. Type check (`uv run poe typecheck`)
5. Tests (`uv run poe test`)

## Configuration

Settings are managed via `app/core/config.py` using pydantic-settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `PROJECT_NAME` | "Electric" | API title |
| `VERSION` | "0.1.0" | API version |
| `DEBUG` | True | Debug mode |
| `HOST` | "0.0.0.0" | Server host |
| `PORT` | 8000 | Server port |

Settings can be overridden via environment variables or `.env` file.

## API Endpoints

### General
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root - welcome message |
| GET | `/api/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc documentation |

### Authentication (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login, receive JWT token |

### Properties (`/api/properties`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/properties/` | Create property with main meter |
| GET | `/api/properties/` | List all properties (paginated) |
| GET | `/api/properties/{id}` | Get property by ID |
| PATCH | `/api/properties/{id}` | Update property |
| GET | `/api/properties/{id}/meters` | Get property's meters |
| POST | `/api/properties/{id}/users/{user_id}` | Associate user |
| DELETE | `/api/properties/{id}/users/{user_id}` | Remove user association |

### Meters (`/api/meters`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/meters/main` | Create main meter |
| POST | `/api/meters/submeter` | Create submeter |
| GET | `/api/meters/{id}` | Get meter by ID |
| PATCH | `/api/meters/{id}` | Update meter |

### Meter Readings (`/api/readings`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/readings/` | Record single reading |
| POST | `/api/readings/bulk` | Record multiple readings |
| GET | `/api/readings/property/{id}/summary` | Get readings at timestamp |
| GET | `/api/readings/property/{id}/latest` | Get latest readings |
| GET | `/api/readings/meter/{id}/history` | Get reading history (paginated) |

## Development Workflow

1. **Setup:**
   ```bash
   uv sync                              # Install dependencies
   uv run poe pre-commit-install        # Install git hooks
   ```

2. **Development:**
   - Make changes following code style conventions
   - Pre-commit hooks auto-format on commit

3. **Before committing:**
   ```bash
   uv run poe check                     # Run all checks
   ```

4. **Adding dependencies:**
   ```bash
   uv add <package>                     # Production dependency
   uv add --dev <package>               # Dev dependency
   ```

## Architecture Patterns

- **Routes** (`app/api/routes/`): HTTP endpoint handlers, thin layer
- **Services** (`app/services/`): Business logic, reusable across routes
- **Models** (`app/models/`): SQLAlchemy ORM models for database tables
- **Schemas** (`app/schemas/`): Pydantic schemas for request/response validation
- **Core** (`app/core/`): Configuration, database connection, shared utilities

## Important Notes for AI Assistants

1. **Always run `uv run poe check`** before committing to ensure all checks pass
2. **Type hints are mandatory** - the ty type checker runs in CI
3. **Pre-commit hooks are active** - code is auto-formatted on commit
4. **Use async/await** for HTTP handlers and I/O operations
5. **Follow existing patterns** - check similar files before adding new code
6. **Tests are required** - add tests for new endpoints in `tests/`
7. **Keep routes thin** - business logic belongs in services
