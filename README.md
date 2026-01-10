# Electric

A FastAPI web application built with Python 3.11 and managed by uv.

## Features

- ⚡ FastAPI framework for high-performance APIs
- 🐍 Python 3.11
- 📦 Dependency management with uv
- ✅ Pre-configured testing with pytest
- 🏗️ Modular project structure

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

## Testing

Run tests with pytest:

```bash
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=app
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

## Development

### Adding New Dependencies

```bash
uv add <package-name>
```

### Adding Dev Dependencies

```bash
uv add --dev <package-name>
```

## License

TBD
