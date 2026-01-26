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
            submeter_values=[Decimal("150.0"), Decimal("120.0"), Decimal("80.0")],
        )
        assert result == Decimal("150.0")

    def test_with_no_submeters(self) -> None:
        """Test when there are no submeters - all is unmetered."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("500.0"),
            submeter_values=[],
        )
        assert result == Decimal("500.0")

    def test_with_none_main_meter(self) -> None:
        """Test when main meter value is None."""
        result = compute_unmetered_value(
            main_meter_value=None,
            submeter_values=[Decimal("100.0")],
        )
        assert result is None

    def test_negative_result_returns_zero(self) -> None:
        """Test that negative unmetered values are clamped to zero."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("100.0"),
            submeter_values=[Decimal("150.0")],
        )
        assert result == Decimal("0")

    def test_exact_match_returns_zero(self) -> None:
        """Test when submeters exactly match main meter."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("200.0"),
            submeter_values=[Decimal("100.0"), Decimal("100.0")],
        )
        assert result == Decimal("0")

    def test_decimal_precision(self) -> None:
        """Test that decimal precision is maintained."""
        result = compute_unmetered_value(
            main_meter_value=Decimal("100.123"),
            submeter_values=[Decimal("50.456"), Decimal("20.333")],
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

        # Create a submeter (all submeters are physical now)
        response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
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
                "name": "gg",
            },
        )

        # Try to create duplicate
        response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
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

    def test_bulk_readings(self, client: TestClient) -> None:
        """Test creating bulk readings for a property."""
        # Create property with submeters
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Bulk Reading Property"},
        )
        property_id = prop_response.json()["id"]

        # Create submeters
        for name in ["gg", "sg"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
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

        # Create submeters
        for name in ["gg", "sg"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
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


class TestConsumptionEndpoints:
    """Tests for consumption calculation endpoints."""

    def test_get_property_consumption(self, client: TestClient) -> None:
        """Test calculating consumption over a period."""
        # Create property with submeters
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Consumption Test Property"},
        )
        property_id = prop_response.json()["id"]

        # Create submeters
        for name in ["apt_a", "apt_b"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
                    "name": name,
                },
            )

        # Record readings at start of month
        start_timestamp = "2024-01-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": start_timestamp,
                "main_meter_value": "1000.0",
                "submeter_readings": {"apt_a": "300.0", "apt_b": "500.0"},
            },
        )

        # Record readings at end of month
        end_timestamp = "2024-02-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": end_timestamp,
                "main_meter_value": "1500.0",
                "submeter_readings": {"apt_a": "400.0", "apt_b": "650.0"},
            },
        )

        # Get consumption
        response = client.get(
            f"/api/readings/property/{property_id}/consumption",
            params={
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Verify main meter consumption: 1500 - 1000 = 500
        assert Decimal(data["main_meter_consumption"]) == Decimal("500.0")

        # Verify submeter consumptions
        submeter_map = {s["name"]: s for s in data["submeters"]}
        # apt_a: 400 - 300 = 100
        assert Decimal(submeter_map["apt_a"]["consumption"]) == Decimal("100.0")
        # apt_b: 650 - 500 = 150
        assert Decimal(submeter_map["apt_b"]["consumption"]) == Decimal("150.0")

        # Verify total submetered: 100 + 150 = 250
        assert Decimal(data["total_submetered_consumption"]) == Decimal("250.0")

        # Verify unmetered: 500 - 250 = 250
        assert Decimal(data["unmetered_consumption"]) == Decimal("250.0")


class TestCostDistributionEndpoints:
    """Tests for cost distribution endpoints."""

    def test_distribute_costs(self, client: TestClient) -> None:
        """Test distributing costs across submeters."""
        # Create property with submeters
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Cost Distribution Property"},
        )
        property_id = prop_response.json()["id"]

        # Create submeters
        for name in ["apt_a", "apt_b"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
                    "name": name,
                },
            )

        # Record readings at start of month
        start_timestamp = "2024-01-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": start_timestamp,
                "main_meter_value": "1000.0",
                "submeter_readings": {"apt_a": "300.0", "apt_b": "500.0"},
            },
        )

        # Record readings at end of month
        end_timestamp = "2024-02-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": end_timestamp,
                "main_meter_value": "1500.0",
                "submeter_readings": {"apt_a": "400.0", "apt_b": "650.0"},
            },
        )

        # Distribute costs (total bill: $500)
        response = client.get(
            f"/api/readings/property/{property_id}/cost-distribution",
            params={
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "total_cost": "500.0",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Verify basic data
        assert Decimal(data["total_cost"]) == Decimal("500.0")
        assert Decimal(data["main_meter_consumption"]) == Decimal("500.0")
        assert Decimal(data["unmetered_consumption"]) == Decimal("250.0")

        # Verify cost distribution
        # apt_a consumption: 100, apt_b consumption: 150
        # apt_a share of submetered: 100/250 = 0.4, apt_b share: 150/250 = 0.6
        # Unmetered = 250
        # apt_a unmetered share: 0.4 * 250 = 100, apt_b: 0.6 * 250 = 150
        # apt_a total: 100 + 100 = 200, apt_b total: 150 + 150 = 300
        # Total for cost: 200 + 300 = 500
        # apt_a cost: (200/500) * 500 = 200, apt_b cost: (300/500) * 500 = 300

        submeter_map = {s["name"]: s for s in data["submeters"]}

        # apt_a
        apt_a = submeter_map["apt_a"]
        assert Decimal(apt_a["consumption"]) == Decimal("100.0")
        assert Decimal(apt_a["consumption_share"]) == Decimal("0.4")
        assert Decimal(apt_a["unmetered_share"]) == Decimal("100.0")
        assert Decimal(apt_a["total_consumption"]) == Decimal("200.0")
        assert Decimal(apt_a["cost"]) == Decimal("200.00")

        # apt_b
        apt_b = submeter_map["apt_b"]
        assert Decimal(apt_b["consumption"]) == Decimal("150.0")
        assert Decimal(apt_b["consumption_share"]) == Decimal("0.6")
        assert Decimal(apt_b["unmetered_share"]) == Decimal("150.0")
        assert Decimal(apt_b["total_consumption"]) == Decimal("300.0")
        assert Decimal(apt_b["cost"]) == Decimal("300.00")

    def test_distribute_costs_no_unmetered(self, client: TestClient) -> None:
        """Test cost distribution when there's no unmetered consumption."""
        # Create property with submeters
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "No Unmetered Cost Property"},
        )
        property_id = prop_response.json()["id"]

        # Create submeters
        for name in ["apt_a", "apt_b"]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
                    "name": name,
                },
            )

        # Record readings where submeters exactly match main meter
        start_timestamp = "2024-01-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": start_timestamp,
                "main_meter_value": "1000.0",
                "submeter_readings": {"apt_a": "400.0", "apt_b": "600.0"},
            },
        )

        end_timestamp = "2024-02-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": end_timestamp,
                "main_meter_value": "1200.0",  # 200 total consumption
                "submeter_readings": {"apt_a": "480.0", "apt_b": "720.0"},  # 80 + 120 = 200
            },
        )

        # Distribute costs
        response = client.get(
            f"/api/readings/property/{property_id}/cost-distribution",
            params={
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "total_cost": "200.0",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Verify no unmetered consumption
        assert Decimal(data["unmetered_consumption"]) == Decimal("0")

        submeter_map = {s["name"]: s for s in data["submeters"]}

        # apt_a: 80/200 * 200 = 80
        assert Decimal(submeter_map["apt_a"]["consumption"]) == Decimal("80.0")
        assert Decimal(submeter_map["apt_a"]["unmetered_share"]) == Decimal("0")
        assert Decimal(submeter_map["apt_a"]["cost"]) == Decimal("80.00")

        # apt_b: 120/200 * 200 = 120
        assert Decimal(submeter_map["apt_b"]["consumption"]) == Decimal("120.0")
        assert Decimal(submeter_map["apt_b"]["unmetered_share"]) == Decimal("0")
        assert Decimal(submeter_map["apt_b"]["cost"]) == Decimal("120.00")


class TestEndToEndWorkflow:
    """End-to-end integration tests for complete workflows."""

    def test_user_property_meters_readings_workflow(self, client: TestClient) -> None:
        """
        Test complete workflow: user creates property, adds submeters, records readings.

        Scenario:
        - User registers
        - User creates a property
        - User adds 2 submeters (gg and sg)
        - User records readings: total=100, gg=30, sg=50
        - Verify readings are associated with correct meters
        - Verify read-back shows total=100, gg=30, sg=50, unmetered=20
        """
        # Step 1: Create a user
        user_response = client.post(
            "/api/auth/register",
            json={
                "username": "meter_test_user",
                "email": "meter_test@example.com",
                "password": "securepassword123",
            },
        )
        assert user_response.status_code == 201
        user_data = user_response.json()
        assert user_data["username"] == "meter_test_user"
        user_id = user_data["id"]

        # Step 2: Create a property
        property_response = client.post(
            "/api/properties/",
            json={
                "display_name": "User's Test Property",
                "address": "123 Integration Test Lane",
            },
        )
        assert property_response.status_code == 201
        property_data = property_response.json()
        property_id = property_data["id"]
        assert property_data["display_name"] == "User's Test Property"

        # Verify property has a main meter auto-created
        meters_response = client.get(f"/api/properties/{property_id}/meters")
        assert meters_response.status_code == 200
        meters = meters_response.json()
        assert len(meters) == 1
        main_meter = meters[0]
        assert main_meter["meter_type"] == MeterType.MAIN_METER
        main_meter_id = main_meter["id"]

        # Step 3: Associate user with property
        assoc_response = client.post(f"/api/properties/{property_id}/users/{user_id}")
        assert assoc_response.status_code == 204

        # Step 4: Add submeter "gg"
        gg_response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "name": "gg",
                "location": "Ground floor",
            },
        )
        assert gg_response.status_code == 201
        gg_meter = gg_response.json()
        assert gg_meter["name"] == "gg"
        assert gg_meter["meter_type"] == MeterType.SUB_METER
        assert gg_meter["sub_meter_kind"] == SubMeterKind.PHYSICAL
        gg_meter_id = gg_meter["id"]

        # Step 5: Add submeter "sg"
        sg_response = client.post(
            "/api/meters/submeter",
            json={
                "property_id": property_id,
                "name": "sg",
                "location": "Second floor",
            },
        )
        assert sg_response.status_code == 201
        sg_meter = sg_response.json()
        assert sg_meter["name"] == "sg"
        assert sg_meter["meter_type"] == MeterType.SUB_METER
        assert sg_meter["sub_meter_kind"] == SubMeterKind.PHYSICAL
        sg_meter_id = sg_meter["id"]

        # Verify property now has 3 meters (1 main + 2 submeters)
        meters_response = client.get(f"/api/properties/{property_id}/meters")
        assert meters_response.status_code == 200
        meters = meters_response.json()
        assert len(meters) == 3

        # Step 6: Record readings using bulk endpoint
        # total=100, gg=30, sg=50
        reading_timestamp = "2024-02-01T12:00:00Z"
        bulk_response = client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": reading_timestamp,
                "main_meter_value": "100.0",
                "submeter_readings": {
                    "gg": "30.0",
                    "sg": "50.0",
                },
            },
        )
        assert bulk_response.status_code == 201
        readings_created = bulk_response.json()
        assert len(readings_created) == 3  # main + gg + sg

        # Verify each reading is associated with the correct meter
        readings_by_meter = {r["meter_id"]: Decimal(r["value"]) for r in readings_created}
        assert readings_by_meter[main_meter_id] == Decimal("100.0")
        assert readings_by_meter[gg_meter_id] == Decimal("30.0")
        assert readings_by_meter[sg_meter_id] == Decimal("50.0")

        # Step 7: Read back the summary and verify computed unmetered
        summary_response = client.get(
            f"/api/readings/property/{property_id}/summary",
            params={"reading_timestamp": reading_timestamp},
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()

        # Verify main meter reading
        assert Decimal(summary["main_meter"]) == Decimal("100.0")

        # Verify submeter readings
        submeter_values = {s["name"]: Decimal(s["value"]) for s in summary["submeters"]}
        assert submeter_values["gg"] == Decimal("30.0")
        assert submeter_values["sg"] == Decimal("50.0")

        # Verify computed unmetered: 100 - 30 - 50 = 20
        assert Decimal(summary["unmetered"]) == Decimal("20.0")

        # Step 8: Also verify via latest readings endpoint
        latest_response = client.get(f"/api/readings/property/{property_id}/latest")
        assert latest_response.status_code == 200
        latest = latest_response.json()

        assert Decimal(latest["main_meter"]) == Decimal("100.0")
        assert Decimal(latest["unmetered"]) == Decimal("20.0")
        latest_submeter_values = {s["name"]: Decimal(s["value"]) for s in latest["submeters"]}
        assert latest_submeter_values["gg"] == Decimal("30.0")
        assert latest_submeter_values["sg"] == Decimal("50.0")

        # Step 9: Verify individual meter history
        gg_history_response = client.get(f"/api/readings/meter/{gg_meter_id}/history")
        assert gg_history_response.status_code == 200
        gg_history = gg_history_response.json()
        assert gg_history["total"] == 1
        assert Decimal(gg_history["readings"][0]["value"]) == Decimal("30.0")

    def test_monthly_consumption_and_cost_distribution_workflow(self, client: TestClient) -> None:
        """
        Test complete workflow for monthly consumption and cost distribution.

        Scenario:
        - Create property with 2 apartments (submeters)
        - Record readings at start and end of month
        - Calculate consumption
        - Distribute costs based on consumption
        """
        # Create property
        prop_response = client.post(
            "/api/properties/",
            json={"display_name": "Monthly Billing Property"},
        )
        property_id = prop_response.json()["id"]

        # Create submeters for apartments
        for name, location in [("apt_101", "Apartment 101"), ("apt_102", "Apartment 102")]:
            client.post(
                "/api/meters/submeter",
                json={
                    "property_id": property_id,
                    "name": name,
                    "location": location,
                },
            )

        # Record readings at start of billing period (January 1st)
        start_timestamp = "2024-01-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": start_timestamp,
                "main_meter_value": "5000.0",
                "submeter_readings": {
                    "apt_101": "2000.0",
                    "apt_102": "2500.0",
                },
            },
        )

        # Record readings at end of billing period (February 1st)
        end_timestamp = "2024-02-01T00:00:00Z"
        client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": end_timestamp,
                "main_meter_value": "5800.0",  # 800 kWh total
                "submeter_readings": {
                    "apt_101": "2300.0",  # 300 kWh
                    "apt_102": "2900.0",  # 400 kWh
                },  # 700 kWh submetered, 100 kWh unmetered
            },
        )

        # Get consumption summary
        consumption_response = client.get(
            f"/api/readings/property/{property_id}/consumption",
            params={
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
            },
        )
        assert consumption_response.status_code == 200
        consumption = consumption_response.json()

        # Verify consumption
        assert Decimal(consumption["main_meter_consumption"]) == Decimal("800.0")
        assert Decimal(consumption["total_submetered_consumption"]) == Decimal("700.0")
        assert Decimal(consumption["unmetered_consumption"]) == Decimal("100.0")

        # Distribute the electricity bill ($240 for the month)
        cost_response = client.get(
            f"/api/readings/property/{property_id}/cost-distribution",
            params={
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "total_cost": "240.0",
            },
        )
        assert cost_response.status_code == 200
        costs = cost_response.json()

        # Verify cost distribution
        assert Decimal(costs["total_cost"]) == Decimal("240.0")

        submeter_costs = {s["name"]: s for s in costs["submeters"]}

        # apt_101: 300 kWh consumption, 300/700 share = ~42.86%
        # apt_101 unmetered share: 42.86% * 100 = ~42.86 kWh
        # apt_101 total: 300 + 42.86 = 342.86 kWh
        apt_101 = submeter_costs["apt_101"]
        assert Decimal(apt_101["consumption"]) == Decimal("300.0")

        # apt_102: 400 kWh consumption, 400/700 share = ~57.14%
        # apt_102 unmetered share: 57.14% * 100 = ~57.14 kWh
        # apt_102 total: 400 + 57.14 = 457.14 kWh
        apt_102 = submeter_costs["apt_102"]
        assert Decimal(apt_102["consumption"]) == Decimal("400.0")

        # Total costs should equal $240
        total_cost = Decimal(apt_101["cost"]) + Decimal(apt_102["cost"])
        assert total_cost == Decimal("240.00")
