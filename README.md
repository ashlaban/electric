# Electric

A FastAPI web application built with Python 3.11 and managed by uv.

## Features

- ⚡ FastAPI framework for high-performance APIs
- 🐍 Python 3.11
- 📦 Dependency management with uv
- ✅ Pre-configured testing with pytest
- 🔍 Linting with ruff
- 🔬 Type checking with ty (Astral)
- 🛠️ Task automation with poethepoet
- 🏗️ Modular project structure
- 🤖 GitHub Actions CI/CD

## Project Structure

```
electric/
├── app/
│   ├── api/
│   │   └── routes/         # API route handlers
│   │       └── health.py   # Health check endpoint
│   ├── core/
│   │   └── config.py       # Application configuration
│   ├── models/             # Pydantic models
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

## Endpoints

- `GET /` - Root endpoint with welcome message
- `GET /api/health` - Health check endpoint

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
