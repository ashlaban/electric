"""Tests for meter ledger functionality."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import MeterType, SubMeterKind
from app.services.meter_reading import compute_unmetered_value


@pytest.fixture(scope="module")
def client():
    """Create a test client with proper lifespan handling."""
    with TestClient(app) as c:
        yield c


class TestComputeUnmeteredValue:
    """Unit tests for the unmetered value computation."""

    def test_basic_computation(self) -> None:
        """Test basic unmetered calculation."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("500.0"),
            physical_submeter_values=[Decimal("150.0"), Decimal("120.0"), Decimal("80.0")],
        )
        assert result == Decimal("150.0")

    def test_with_no_submeters(self) -> None:
        """Test when there are no submeters - all is unmetered."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("500.0"),
            physical_submeter_values=[],
        )
        assert result == Decimal("500.0")

    def test_with_none_main_meter(self) -> None:
        """Test when main meter value is None."""
        result = compute_unmetered_value(
            main_meter_value=None,
            physical_submeter_values=[Decimal("100.0")],
        )
        assert result is None

    def test_negative_result_returns_zero(self) -> None:
        """Test that negative unmetered values are clamped to zero."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("100.0"),
            physical_submeter_values=[Decimal("150.0")],
        )
        assert result == Decimal("0")

    def test_exact_match_returns_zero(self) -> None:
        """Test when submeters exactly match main meter."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("200.0"),
            physical_submeter_values=[Decimal("100.0"), Decimal("100.0")],
        )
        assert result == Decimal("0")

    def test_decimal_precision(self) -> None:
        """Test that decimal precision is maintained."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("100.123"),
            physical_submeter_values=[Decimal("50.456"), Decimal("20.333")],
        )
        assert result == Decimal("29.334")


class TestPropertyEndpoints:
    """Tests for property API endpoints."""

    def test_create_property(self, client: TestClient) -> None:
        """Test creating a new property."""
        response = client.post(
            "/api/properties/",
            json={"display_name": "Test Property", "address": "123 Test St"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Test Property"
        assert data["address"] == "123 Test St"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_property_minimal(self, client: TestClient) -> None:
        """Test creating a property with minimal data."""
        response = client.post(
            "/api/properties/",
            json={"display_name": "Minimal Property"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Minimal Property"
        assert data["address"] is None

    def test_get_property(self, client: TestClient) -> None:
        """Test getting a property by ID."""
        # First create a property
        create_response = client.post(
            "/api/properties/",
            json={"display_name": "Get Test Property"},
        )
        property_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/properties/{property_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Get Test Property"

    def test_get_property_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent property."""
        response = client.get("/api/properties/99999")
        assert response.status_code == 404

    def test_list_properties(self, client: TestClient) -> None:
        """Test listing properties."""
        response = client.get("/api/properties/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_update_property(self, client: TestClient) -> None:
        """Test updating a property."""
        # Create a property
        create_response = client.post(
            "/api/properties/",
            json={"display_name": "Original Name"},
        )
        property_id = create_response.json()["id"]

        # Update it
        response = client.patch(
            f"/api/properties/{property_id}",
            json={"display_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    def test_property_has_main_meter(self, client: TestClient) -> None:
        """Test that creating a property auto-creates a main meter."""
        # Create a property
        create_response = client.post(
            "/api/properties/",
            json={"display_name": "Property With Meter"},
        )
        property_id = create_response.json()["id"]

        # Get its meters
        response = client.get(f"/api/properties/{property_id}/meters")
        assert response.status_code == 200
        meters = response.json()
        assert len(meters) == 1
        assert meters[0]["meter_type"] == MeterType.MAIN_METER


class TestMeterEndpoints:
    """Tests for meter API endpoints."""

    def test_create_submeter(self, client: TestClient) -> None:
        """Test creating a submeter."""
        # Create a property first
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Submeter Test Property"},
        )
        property_id = prop_response.json()["id"]

        # Create a physical submeter
        response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "sub_meter_kind": SubMeterKind.PHYSICAL,
                "name": "gg",
                "location": "Ground floor",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["meter_type"] == MeterType.SUB_METER
        assert data["sub_meter_kind"] == SubMeterKind.PHYSICAL
        assert data["name"] == "gg"
        assert data["location"] == "Ground floor"

    def test_create_virtual_submeter(self, client: TestClient) -> None:
        """Test creating a virtual submeter."""
        # Create a property first
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Virtual Submeter Property"},
        )
        property_id = prop_response.json()["id"]

        # Create a virtual submeter
        response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "sub_meter_kind": SubMeterKind.VIRTUAL,
                "name": "unmetered",
            },
        )
        assert response.status_code == 201
        assert response.json()["sub_meter_kind"] == SubMeterKind.VIRTUAL

    def test_duplicate_submeter_name_rejected(self, client: TestClient) -> None:
        """Test that duplicate submeter names are rejected."""
        # Create a property
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Duplicate Test Property"},
        )
        property_id = prop_response.json()["id"]

        # Create first submeter
        client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "sub_meter_kind": SubMeterKind.PHYSICAL,
                "name": "gg",
            },
        )

        # Try to create duplicate
        response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "sub_meter_kind": SubMeterKind.PHYSICAL,
                "name": "gg",
            },
        )
        assert response.status_code == 400

    def test_get_meter(self, client: TestClient) -> None:
        """Test getting a meter by ID."""
        # Create a property (which creates a main meter)
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Get Meter Property"},
        )
        property_id = prop_response.json()["id"]

        # Get meters for property
        meters_response = client.get(f"/api/properties/{property_id}/meters")
        meter_id = meters_response.json()[0]["id"]

        # Get the meter
        response = client.get(f"/api/meters/{meter_id}")
        assert response.status_code == 200
        assert response.json()["id"] == meter_id


class TestReadingEndpoints:
    """Tests for meter reading (ledger) API endpoints."""

    def test_create_single_reading(self, client: TestClient) -> None:
        """Test creating a single meter reading."""
        # Create property and get main meter
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Reading Test Property"},
        )
        property_id = prop_response.json()["id"]

        meters_response = client.get(f"/api/properties/{property_id}/meters")
        meter_id = meters_response.json()[0]["id"]

        # Create a reading
        response = client.post(
            "/api/readings/",
            json={
                "meter_id": meter_id,
                "reading_timestamp": "2024-01-15T10:30:00Z",
                "value": "250.5",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["meter_id"] == meter_id
        assert Decimal(data["value"]) == Decimal("250.5")

    def test_cannot_record_virtual_meter_reading(self, client: TestClient) -> None:
        """Test that recordings for virtual meters are rejected."""
        # Create property with virtual submeter
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Virtual Reading Test"},
        )
        property_id = prop_response.json()["id"]

        # Create virtual submeter
        submeter_response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "sub_meter_kind": SubMeterKind.VIRTUAL,
                "name": "unmetered",
            },
        )
        virtual_meter_id = submeter_response.json()["id"]

        # Try to create a reading for virtual meter
        response = client.post(
            "/api/readings/",
            json={
                "meter_id": virtual_meter_id,
                "reading_timestamp": "2024-01-15T10:30:00Z",
                "value": "100.0",
            },
        )
        assert response.status_code == 400

    def test_bulk_readings(self, client: TestClient) -> None:
        """Test creating bulk readings for a property."""
        # Create property with submeters
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Bulk Reading Property"},
        )
        property_id = prop_response.json()["id"]

        # Create physical submeters
        for name in ["gg", "sg"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
                    "sub_meter_kind": SubMeterKind.PHYSICAL,
                    "name": name,
                },
            )

        # Submit bulk readings
        response = client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-15T10:30:00Z",
                "main_meter_value": "500.0",
                "submeter_readings": {"gg": "150.0", "sg": "120.0"},
            },
        )
        assert response.status_code == 201
        readings = response.json()
        assert len(readings) == 3  # main + 2 submeters

    def test_get_property_reading_summary(self, client: TestClient) -> None:
        """Test getting a reading summary with computed unmetered."""
        # Create property with submeters
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Summary Test Property"},
        )
        property_id = prop_response.json()["id"]

        # Create physical submeters
        for name in ["gg", "sg"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
                    "sub_meter_kind": SubMeterKind.PHYSICAL,
                    "name": name,
                },
            )

        # Submit bulk readings
        timestamp = "2024-01-15T10:30:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": timestamp,
                "main_meter_value": "500.0",
                "submeter_readings": {"gg": "150.0", "sg": "120.0"},
            },
        )

        # Get summary
        response = client.get(
            f"/api/readings/property/{property_id}/summary",
            params={"reading_timestamp": timestamp},
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["main_meter"]) == Decimal("500.0")
        assert Decimal(data["unmetered"]) == Decimal("230.0")  # 500 - 150 - 120
        assert len(data["submeters"]) == 2

    def test_get_latest_readings(self, client: TestClient) -> None:
        """Test getting the latest readings for a property."""
        # Create property
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Latest Reading Property"},
        )
        property_id = prop_response.json()["id"]

        # Get meters (main meter)
        meters_response = client.get(f"/api/properties/{property_id}/meters")
        meter_id = meters_response.json()[0]["id"]

        # Create readings at different times
        for timestamp, value in [
            ("2024-01-15T10:00:00Z", "100.0"),
            ("2024-01-15T11:00:00Z", "200.0"),
        ]:
            client.post(
                "/api/readings/",
                json={
                    "meter_id": meter_id,
                    "reading_timestamp": timestamp,
                    "value": value,
                },
            )

        # Get latest
        response = client.get(f"/api/readings/property/{property_id}/latest")
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["main_meter"]) == Decimal("200.0")

    def test_get_meter_history(self, client: TestClient) -> None:
        """Test getting reading history for a meter."""
        # Create property
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "History Test Property"},
        )
        property_id = prop_response.json()["id"]

        # Get main meter
        meters_response = client.get(f"/api/properties/{property_id}/meters")
        meter_id = meters_response.json()[0]["id"]

        # Create multiple readings
        for i in range(5):
            client.post(
                "/api/readings/",
                json={
                    "meter_id": meter_id,
                    "reading_timestamp": f"2024-01-{15 + i}T10:00:00Z",
                    "value": str(100 + i * 10),
                },
            )

        # Get history
        response = client.get(f"/api/readings/meter/{meter_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert data["meter_id"] == meter_id
        assert data["total"] == 5
        assert len(data["readings"]) == 5
