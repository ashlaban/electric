"""Basic API tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Test the root endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Test the health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_property() -> None:
    """Test creating a property with default meters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/properties",
            json={
                "name": "Test Property",
                "address": "123 Test Street",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Property"
    assert data["address"] == "123 Test Street"
    assert "id" in data

    # Verify the property has meters
    property_id = data["id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/properties/{property_id}/meters")
    assert response.status_code == 200
    meters = response.json()
    assert len(meters) == 4
    meter_codes = {m["meter_code"] for m in meters}
    assert meter_codes == {"total", "gg", "sg", "unmetered"}


@pytest.mark.asyncio
async def test_create_and_update_reading() -> None:
    """Test creating and updating a meter reading."""
    # Create a property first
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/properties",
            json={"name": "Test Property 2"},
        )
    property_id = response.json()["id"]

    # Get the total meter
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/properties/{property_id}/meters")
    meters = response.json()
    total_meter = next(m for m in meters if m["meter_code"] == "total")

    # Create a reading
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/meters/{total_meter['id']}/readings",
            json={
                "reading_value": 1000.50,
                "reading_timestamp": "2026-01-01T12:00:00Z",
                "notes": "Initial reading",
            },
        )
    assert response.status_code == 201
    reading = response.json()
    assert reading["reading_value"] == "1000.50"
    assert reading["notes"] == "Initial reading"

    # Update the reading (e.g., correct a typo)
    reading_id = reading["id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            f"/api/readings/{reading_id}",
            json={
                "reading_value": 1000.55,
                "notes": "Corrected reading",
            },
        )
    assert response.status_code == 200
    updated_reading = response.json()
    assert updated_reading["reading_value"] == "1000.55"
    assert updated_reading["notes"] == "Corrected reading"
