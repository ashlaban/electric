"""Tests for v2 API: readings with absolute/relative types and formula-based billing."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import MeterType, ReadingType


@pytest.fixture(scope="module")
def client():
    """Create a test client with proper lifespan handling."""
    with TestClient(app) as c:
        yield c


def _create_property_with_submeters(
    client: TestClient,
    display_name: str,
    submeter_names: list[str],
) -> tuple[int, dict[str, int]]:
    """Helper: create a property with submeters, return (property_id, meter_ids_by_name)."""
    prop_response = client.post(
        "/api/properties/",
        json={"display_name": display_name},
    )
    assert prop_response.status_code == 201
    property_id = prop_response.json()["id"]

    meter_ids: dict[str, int] = {}
    # Get main meter id
    meters_response = client.get(f"/api/properties/{property_id}/meters")
    main_meter = next(m for m in meters_response.json() if m["meter_type"] == MeterType.MAIN_METER)
    meter_ids["_main"] = main_meter["id"]

    for name in submeter_names:
        resp = client.post(
            "/api/meters/submeter",
            json={"property_id": property_id, "name": name},
        )
        assert resp.status_code == 201
        meter_ids[name] = resp.json()["id"]

    return property_id, meter_ids


class TestV2AbsoluteReadings:
    """Tests for v2 API with absolute readings (backward-compatible with v1 behavior)."""

    def test_create_single_absolute_reading(self, client: TestClient) -> None:
        """Test creating a single absolute reading via v2 API."""
        property_id, meter_ids = _create_property_with_submeters(client, "V2 Absolute Single", [])

        response = client.post(
            "/api/v2/readings/",
            json={
                "meter_id": meter_ids["_main"],
                "reading_timestamp": "2024-01-15T10:00:00Z",
                "value": "500.0",
                "reading_type": "absolute",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["meter_id"] == meter_ids["_main"]
        assert Decimal(data["value"]) == Decimal("500.0")
        assert data["reading_type"] == ReadingType.ABSOLUTE

    def test_create_bulk_absolute_readings(self, client: TestClient) -> None:
        """Test creating bulk absolute readings via v2 API."""
        property_id, meter_ids = _create_property_with_submeters(
            client, "V2 Absolute Bulk", ["apt_a", "apt_b"]
        )

        response = client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-15T10:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1000.0",
                "submeter_readings": {"apt_a": "300.0", "apt_b": "500.0"},
            },
        )
        assert response.status_code == 201
        readings = response.json()
        assert len(readings) == 3
        for r in readings:
            assert r["reading_type"] == ReadingType.ABSOLUTE

    def test_absolute_consumption_calculation(self, client: TestClient) -> None:
        """Test consumption calculation from absolute readings."""
        property_id, meter_ids = _create_property_with_submeters(
            client, "V2 Absolute Consumption", ["apt_a", "apt_b"]
        )

        # Start of period
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1000.0",
                "submeter_readings": {"apt_a": "300.0", "apt_b": "500.0"},
            },
        )

        # End of period
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1500.0",
                "submeter_readings": {"apt_a": "420.0", "apt_b": "680.0"},
            },
        )

        response = client.get(
            f"/api/v2/readings/property/{property_id}/consumption",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Main: 1500 - 1000 = 500
        assert Decimal(data["main_meter_consumption"]) == Decimal("500.0")
        # apt_a: 420 - 300 = 120, apt_b: 680 - 500 = 180
        assert Decimal(data["total_submetered_consumption"]) == Decimal("300.0")
        # Unmetered: 500 - 300 = 200
        assert Decimal(data["unmetered_consumption"]) == Decimal("200.0")

        # Check that unmetered appears as virtual submeter
        virtual = [s for s in data["submeters"] if s["is_virtual"]]
        assert len(virtual) == 1
        assert virtual[0]["name"] == "_unmetered"
        assert Decimal(virtual[0]["consumption"]) == Decimal("200.0")


class TestV2RelativeReadings:
    """Tests for v2 API with relative readings (period consumption values)."""

    def test_create_single_relative_reading(self, client: TestClient) -> None:
        """Test creating a single relative reading."""
        property_id, meter_ids = _create_property_with_submeters(client, "V2 Relative Single", [])

        response = client.post(
            "/api/v2/readings/",
            json={
                "meter_id": meter_ids["_main"],
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "value": "350.0",
                "reading_type": "relative",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["reading_type"] == ReadingType.RELATIVE
        assert Decimal(data["value"]) == Decimal("350.0")

    def test_relative_consumption_calculation(self, client: TestClient) -> None:
        """Test consumption from relative readings is summed over the period."""
        property_id, meter_ids = _create_property_with_submeters(
            client, "V2 Relative Consumption", ["apt_a", "apt_b"]
        )

        # Record relative readings for January (consumption for the month)
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "relative",
                "main_meter_value": "500.0",
                "submeter_readings": {"apt_a": "120.0", "apt_b": "180.0"},
            },
        )

        response = client.get(
            f"/api/v2/readings/property/{property_id}/consumption",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Relative readings are summed in the period
        assert Decimal(data["main_meter_consumption"]) == Decimal("500.0")
        assert Decimal(data["total_submetered_consumption"]) == Decimal("300.0")
        assert Decimal(data["unmetered_consumption"]) == Decimal("200.0")


class TestV2ReadingSummary:
    """Tests for reading summary and history endpoints."""

    def test_property_reading_summary(self, client: TestClient) -> None:
        """Test getting a reading summary at a specific timestamp."""
        property_id, meter_ids = _create_property_with_submeters(
            client, "V2 Summary Test", ["sub_a", "sub_b"]
        )

        timestamp = "2024-03-01T12:00:00Z"
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": timestamp,
                "main_meter_value": "800.0",
                "submeter_readings": {"sub_a": "200.0", "sub_b": "350.0"},
            },
        )

        response = client.get(
            f"/api/v2/readings/property/{property_id}/summary",
            params={"reading_timestamp": timestamp},
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["main_meter"]) == Decimal("800.0")
        assert Decimal(data["unmetered"]) == Decimal("250.0")
        assert len(data["submeters"]) == 2

    def test_latest_readings(self, client: TestClient) -> None:
        """Test getting latest readings for a property."""
        property_id, meter_ids = _create_property_with_submeters(client, "V2 Latest Test", [])

        for ts, val in [
            ("2024-01-01T00:00:00Z", "100.0"),
            ("2024-02-01T00:00:00Z", "200.0"),
        ]:
            client.post(
                "/api/v2/readings/",
                json={
                    "meter_id": meter_ids["_main"],
                    "reading_timestamp": ts,
                    "value": val,
                },
            )

        response = client.get(f"/api/v2/readings/property/{property_id}/latest")
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["main_meter"]) == Decimal("200.0")

    def test_meter_history(self, client: TestClient) -> None:
        """Test getting reading history for a meter."""
        property_id, meter_ids = _create_property_with_submeters(client, "V2 History Test", [])

        for i in range(5):
            client.post(
                "/api/v2/readings/",
                json={
                    "meter_id": meter_ids["_main"],
                    "reading_timestamp": f"2024-01-{10 + i}T00:00:00Z",
                    "value": str(100 + i * 50),
                },
            )

        response = client.get(f"/api/v2/readings/meter/{meter_ids['_main']}/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["readings"]) == 5


class TestV2CostFormulas:
    """Tests for cost formula CRUD operations."""

    def test_create_formula(self, client: TestClient) -> None:
        """Test creating a cost formula."""
        property_id, _ = _create_property_with_submeters(client, "Formula CRUD Create", ["sub_a"])

        response = client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "tenant_1"
        assert data["property_id"] == property_id
        assert Decimal(data["terms"]["sub_a"]) == Decimal("1.0")
        assert data["is_active"] is True

    def test_duplicate_formula_name_rejected(self, client: TestClient) -> None:
        """Test that duplicate formula names are rejected."""
        property_id, _ = _create_property_with_submeters(client, "Formula CRUD Dup", ["sub_a"])

        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )

        response = client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "0.5"},
            },
        )
        assert response.status_code == 400

    def test_get_formula(self, client: TestClient) -> None:
        """Test getting a formula by ID."""
        property_id, _ = _create_property_with_submeters(client, "Formula CRUD Get", ["sub_a"])

        create_resp = client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )
        formula_id = create_resp.json()["id"]

        response = client.get(f"/api/v2/billing/formulas/{formula_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "tenant_1"

    def test_list_formulas(self, client: TestClient) -> None:
        """Test listing formulas for a property."""
        property_id, _ = _create_property_with_submeters(
            client, "Formula CRUD List", ["sub_a", "sub_b"]
        )

        for name, terms in [
            ("tenant_1", {"sub_a": "1.0"}),
            ("tenant_2", {"sub_b": "1.0"}),
        ]:
            client.post(
                "/api/v2/billing/formulas/",
                json={
                    "property_id": property_id,
                    "name": name,
                    "terms": terms,
                },
            )

        response = client.get(f"/api/v2/billing/formulas/property/{property_id}")
        assert response.status_code == 200
        formulas = response.json()
        assert len(formulas) == 2
        names = {f["name"] for f in formulas}
        assert names == {"tenant_1", "tenant_2"}

    def test_update_formula(self, client: TestClient) -> None:
        """Test updating a formula's terms."""
        property_id, _ = _create_property_with_submeters(client, "Formula CRUD Update", ["sub_a"])

        create_resp = client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )
        formula_id = create_resp.json()["id"]

        response = client.patch(
            f"/api/v2/billing/formulas/{formula_id}",
            json={"terms": {"sub_a": "0.8", "_unmetered": "0.2"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["terms"]["sub_a"]) == Decimal("0.8")
        assert Decimal(data["terms"]["_unmetered"]) == Decimal("0.2")

    def test_delete_formula(self, client: TestClient) -> None:
        """Test soft-deleting a formula."""
        property_id, _ = _create_property_with_submeters(client, "Formula CRUD Delete", ["sub_a"])

        create_resp = client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )
        formula_id = create_resp.json()["id"]

        response = client.delete(f"/api/v2/billing/formulas/{formula_id}")
        assert response.status_code == 204

        # Should no longer appear in active list
        list_resp = client.get(f"/api/v2/billing/formulas/property/{property_id}")
        assert len(list_resp.json()) == 0

        # But can still be retrieved directly
        get_resp = client.get(f"/api/v2/billing/formulas/{formula_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is False


class TestV2CostDistribution:
    """Tests for formula-based cost distribution."""

    def test_simple_proportional_distribution(self, client: TestClient) -> None:
        """Test cost distribution where each tenant has a single submeter."""
        property_id, _ = _create_property_with_submeters(
            client, "V2 Cost Simple", ["sub_a", "sub_b"]
        )

        # Record absolute readings
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1000.0",
                "submeter_readings": {"sub_a": "300.0", "sub_b": "500.0"},
            },
        )
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1800.0",
                "submeter_readings": {"sub_a": "600.0", "sub_b": "900.0"},
            },
        )

        # Main consumed: 800, sub_a: 300, sub_b: 400, unmetered: 100

        # Create formulas: each tenant gets their submeter consumption
        # tenant_1 = total_cost * sub_a / main
        # tenant_2 = total_cost * sub_b / main
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_2",
                "terms": {"sub_b": "1.0"},
            },
        )

        response = client.get(
            f"/api/v2/billing/property/{property_id}/distribute",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
                "total_cost": "800.0",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert Decimal(data["total_cost"]) == Decimal("800.0")
        assert Decimal(data["main_meter_consumption"]) == Decimal("800.0")
        assert Decimal(data["unmetered_consumption"]) == Decimal("100.0")

        shares = {s["name"]: s for s in data["shares"]}

        # tenant_1: cost = 800 * 300 / 800 = 300
        assert Decimal(shares["tenant_1"]["cost"]) == Decimal("300.00")
        assert Decimal(shares["tenant_1"]["weighted_consumption"]) == Decimal("300.0")

        # tenant_2: cost = 800 * 400 / 800 = 400
        assert Decimal(shares["tenant_2"]["cost"]) == Decimal("400.00")

    def test_weighted_formula_with_shared_meter(self, client: TestClient) -> None:
        """Test the example from the spec: shared submeter with fractional weights.

        Scenario: 3 submeters, 2 tenants.
        tenant_1 = total_cost * (sub_1 + 0.4 * sub_2) / main_meter
        tenant_2 = total_cost * (sub_3 + 0.6 * sub_2) / main_meter
        """
        property_id, _ = _create_property_with_submeters(
            client, "V2 Cost Weighted", ["sub_1", "sub_2", "sub_3"]
        )

        # Record readings
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "0.0",
                "submeter_readings": {"sub_1": "0.0", "sub_2": "0.0", "sub_3": "0.0"},
            },
        )
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1000.0",
                "submeter_readings": {
                    "sub_1": "200.0",
                    "sub_2": "300.0",
                    "sub_3": "400.0",
                },
            },
        )

        # Main: 1000, sub_1: 200, sub_2: 300, sub_3: 400, unmetered: 100

        # Create formulas
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_1": "1.0", "sub_2": "0.4"},
            },
        )
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_2",
                "terms": {"sub_3": "1.0", "sub_2": "0.6"},
            },
        )

        response = client.get(
            f"/api/v2/billing/property/{property_id}/distribute",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
                "total_cost": "1000.0",
            },
        )
        assert response.status_code == 200
        data = response.json()

        shares = {s["name"]: s for s in data["shares"]}

        # tenant_1: weighted = 1.0 * 200 + 0.4 * 300 = 200 + 120 = 320
        # cost = 1000 * 320 / 1000 = 320
        assert Decimal(shares["tenant_1"]["weighted_consumption"]) == Decimal("320.0")
        assert Decimal(shares["tenant_1"]["cost"]) == Decimal("320.00")

        # tenant_2: weighted = 1.0 * 400 + 0.6 * 300 = 400 + 180 = 580
        # cost = 1000 * 580 / 1000 = 580
        assert Decimal(shares["tenant_2"]["weighted_consumption"]) == Decimal("580.0")
        assert Decimal(shares["tenant_2"]["cost"]) == Decimal("580.00")

    def test_formula_with_unmetered_reference(self, client: TestClient) -> None:
        """Test a formula that includes the _unmetered virtual submeter."""
        property_id, _ = _create_property_with_submeters(client, "V2 Cost Unmetered", ["sub_a"])

        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "0.0",
                "submeter_readings": {"sub_a": "0.0"},
            },
        )
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "1000.0",
                "submeter_readings": {"sub_a": "600.0"},
            },
        )
        # Main: 1000, sub_a: 600, unmetered: 400

        # Formula: tenant gets submeter + half of unmetered
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0", "_unmetered": "0.5"},
            },
        )

        response = client.get(
            f"/api/v2/billing/property/{property_id}/distribute",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
                "total_cost": "500.0",
            },
        )
        assert response.status_code == 200
        data = response.json()

        shares = {s["name"]: s for s in data["shares"]}

        # tenant_1: weighted = 1.0 * 600 + 0.5 * 400 = 600 + 200 = 800
        # cost = 500 * 800 / 1000 = 400
        assert Decimal(shares["tenant_1"]["weighted_consumption"]) == Decimal("800.0")
        assert Decimal(shares["tenant_1"]["cost"]) == Decimal("400.00")

    def test_distribution_with_relative_readings(self, client: TestClient) -> None:
        """Test cost distribution using relative readings."""
        property_id, _ = _create_property_with_submeters(
            client, "V2 Cost Relative", ["sub_a", "sub_b"]
        )

        # Record relative readings (consumption values directly)
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "relative",
                "main_meter_value": "500.0",
                "submeter_readings": {"sub_a": "150.0", "sub_b": "200.0"},
            },
        )
        # Main: 500, sub_a: 150, sub_b: 200, unmetered: 150

        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_a": "1.0"},
            },
        )
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_2",
                "terms": {"sub_b": "1.0"},
            },
        )

        response = client.get(
            f"/api/v2/billing/property/{property_id}/distribute",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
                "total_cost": "250.0",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert Decimal(data["main_meter_consumption"]) == Decimal("500.0")

        shares = {s["name"]: s for s in data["shares"]}
        # tenant_1: 250 * 150 / 500 = 75
        assert Decimal(shares["tenant_1"]["cost"]) == Decimal("75.00")
        # tenant_2: 250 * 200 / 500 = 100
        assert Decimal(shares["tenant_2"]["cost"]) == Decimal("100.00")

    def test_no_formulas_returns_error(self, client: TestClient) -> None:
        """Test that distributing costs with no formulas returns 400."""
        property_id, _ = _create_property_with_submeters(client, "V2 Cost No Formula", ["sub_a"])

        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-01T00:00:00Z",
                "main_meter_value": "0.0",
                "submeter_readings": {"sub_a": "0.0"},
            },
        )
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "main_meter_value": "100.0",
                "submeter_readings": {"sub_a": "80.0"},
            },
        )

        response = client.get(
            f"/api/v2/billing/property/{property_id}/distribute",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
                "total_cost": "100.0",
            },
        )
        assert response.status_code == 400


class TestV2EndToEnd:
    """End-to-end tests for v2 API workflows."""

    def test_full_monthly_billing_workflow(self, client: TestClient) -> None:
        """Complete billing workflow: property, meters, readings, formulas, distribution.

        Scenario: A household with 3 submeters and 2 tenants.
        - sub_1, sub_2, sub_3 are physical submeters
        - tenant_1 uses sub_1 and 40% of sub_2 (shared space)
        - tenant_2 uses sub_3 and 60% of sub_2 (shared space)
        """
        # Create property with 3 submeters
        property_id, meter_ids = _create_property_with_submeters(
            client, "V2 E2E Monthly", ["sub_1", "sub_2", "sub_3"]
        )

        # Record January start readings (absolute)
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-01-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "10000.0",
                "submeter_readings": {
                    "sub_1": "3000.0",
                    "sub_2": "2000.0",
                    "sub_3": "4000.0",
                },
            },
        )

        # Record January end readings
        client.post(
            "/api/v2/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-02-01T00:00:00Z",
                "reading_type": "absolute",
                "main_meter_value": "10800.0",
                "submeter_readings": {
                    "sub_1": "3200.0",  # 200 kWh
                    "sub_2": "2300.0",  # 300 kWh
                    "sub_3": "4250.0",  # 250 kWh
                },
            },
        )
        # Total: 800 kWh, submetered: 750 kWh, unmetered: 50 kWh

        # Verify consumption
        consumption_resp = client.get(
            f"/api/v2/readings/property/{property_id}/consumption",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
            },
        )
        assert consumption_resp.status_code == 200
        consumption = consumption_resp.json()
        assert Decimal(consumption["main_meter_consumption"]) == Decimal("800.0")
        assert Decimal(consumption["total_submetered_consumption"]) == Decimal("750.0")
        assert Decimal(consumption["unmetered_consumption"]) == Decimal("50.0")

        # Create formulas for two tenants
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_1",
                "terms": {"sub_1": "1.0", "sub_2": "0.4"},
            },
        )
        client.post(
            "/api/v2/billing/formulas/",
            json={
                "property_id": property_id,
                "name": "tenant_2",
                "terms": {"sub_3": "1.0", "sub_2": "0.6"},
            },
        )

        # Verify formulas
        formulas_resp = client.get(f"/api/v2/billing/formulas/property/{property_id}")
        assert len(formulas_resp.json()) == 2

        # Distribute the electricity bill ($400)
        dist_resp = client.get(
            f"/api/v2/billing/property/{property_id}/distribute",
            params={
                "start_timestamp": "2024-01-01T00:00:00Z",
                "end_timestamp": "2024-02-01T00:00:00Z",
                "total_cost": "400.0",
            },
        )
        assert dist_resp.status_code == 200
        dist = dist_resp.json()

        assert Decimal(dist["total_cost"]) == Decimal("400.0")
        assert Decimal(dist["main_meter_consumption"]) == Decimal("800.0")
        assert Decimal(dist["unmetered_consumption"]) == Decimal("50.0")

        shares = {s["name"]: s for s in dist["shares"]}

        # tenant_1: weighted = 1.0 * 200 + 0.4 * 300 = 200 + 120 = 320
        # cost = 400 * 320 / 800 = 160
        assert Decimal(shares["tenant_1"]["weighted_consumption"]) == Decimal("320.0")
        assert Decimal(shares["tenant_1"]["cost"]) == Decimal("160.00")

        # tenant_2: weighted = 1.0 * 250 + 0.6 * 300 = 250 + 180 = 430
        # cost = 400 * 430 / 800 = 215
        assert Decimal(shares["tenant_2"]["weighted_consumption"]) == Decimal("430.0")
        assert Decimal(shares["tenant_2"]["cost"]) == Decimal("215.00")

        # Verify meter consumptions are reported
        assert "sub_1" in dist["meter_consumptions"]
        assert "sub_2" in dist["meter_consumptions"]
        assert "sub_3" in dist["meter_consumptions"]
        assert "_unmetered" in dist["meter_consumptions"]

    def test_v1_api_still_works(self, client: TestClient) -> None:
        """Verify that existing v1 API endpoints are not broken."""
        # Create property via v1
        prop_resp = client.post(
            "/api/properties/",
            json={"display_name": "V1 Compat Check"},
        )
        assert prop_resp.status_code == 201
        property_id = prop_resp.json()["id"]

        # Create submeter via v1
        sub_resp = client.post(
            "/api/meters/submeter",
            json={"property_id": property_id, "name": "v1_sub"},
        )
        assert sub_resp.status_code == 201

        # Bulk reading via v1
        bulk_resp = client.post(
            "/api/readings/bulk",
            json={
                "property_id": property_id,
                "reading_timestamp": "2024-06-01T00:00:00Z",
                "main_meter_value": "500.0",
                "submeter_readings": {"v1_sub": "300.0"},
            },
        )
        assert bulk_resp.status_code == 201

        # Summary via v1
        summary_resp = client.get(
            f"/api/readings/property/{property_id}/summary",
            params={"reading_timestamp": "2024-06-01T00:00:00Z"},
        )
        assert summary_resp.status_code == 200
        assert Decimal(summary_resp.json()["main_meter"]) == Decimal("500.0")
        assert Decimal(summary_resp.json()["unmetered"]) == Decimal("200.0")
