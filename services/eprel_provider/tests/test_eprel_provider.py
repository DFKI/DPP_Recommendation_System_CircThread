from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.eprel_client import (
    EprelNotFoundError,
    EprelUpstreamError,
    _best_model_identifier_match,
    _extract_product_search_items,
    _registration_number,
    to_catalog_item,
    to_passport,
)
from app.main import app


DISHWASHER_PAYLOAD = {
    "eprelRegistrationNumber": "2613426",
    "productGroup": "dishwashers2019",
    "supplierOrTrademark": "Siemens",
    "modelIdentifier": "SN43HW04ME",
    "energyClass": "D",
    "energyClassRange": "A_G",
    "energyCons100": 85,
    "energyCons": 0.849,
    "waterCons": 9,
    "noise": 42,
    "noiseClass": "B",
    "ratedCapacity": 14,
    "dimensionHeight": 82,
    "dimensionWidth": 60,
    "dimensionDepth": 57,
    "programmeDuration": 270,
    "cleaningPerformanceIndexV2": 1.121,
    "dryingPerformanceIndexV2": 1.061,
    "guaranteeDuration": 24,
    "status": "PUBLISHED",
    "implementingAct": "EU_2019_2017",
    "productModelCoreId": 2615889,
    "versionId": 5444735,
    "versionNumber": 1,
    "availabilityInEUEEACountries": "ALL",
    "onMarketStartDate": [2026, 4, 29],
    "firstPublicationDate": [2026, 4, 28],
    "organisation": {
        "organisationName": "BSH Hausgeraete GmbH",
        "website": "www.bsh-group.com",
    },
    "contactDetails": {
        "serviceName": "Siemens Infoline",
        "email": "service@example.com",
        "phone": "+49 000 0000000",
        "country": "DE",
        "postalCode": "81739",
        "city": "Muenchen",
        "street": "Carl-Wery-Strasse",
        "streetNumber": "34",
    },
}


WASHING_MACHINE_PAYLOAD = {
    "eprelRegistrationNumber": "2219971",
    "productGroup": "washingmachines2019",
    "supplierOrTrademark": "Bosch",
    "modelIdentifier": "WAN28283ES",
    "energyClass": "A",
    "energyClassRange": "A_G",
    "energyConsPer100Cycle": 47,
    "energyConsPerCycle": 0.472,
    "waterCons": 44,
    "noise": 72,
    "noiseClass": "A",
    "ratedCapacity": 8,
    "dimensionHeight": 85,
    "dimensionWidth": 60,
    "dimensionDepth": 63,
    "programmeDurationRated": 205,
    "spinClass": "B",
    "spinSpeedRated": 1351,
    "rinsingEffectiveness": 5,
    "moisture": 53.9,
    "washingEfficiencyIndexV2": 1.031,
    "guaranteeDuration": 24,
    "status": "PUBLISHED",
    "implementingAct": "EU_2019_2014",
    "productModelCoreId": 2222254,
    "versionId": 5349512,
    "versionNumber": 1,
    "availabilityInEUEEACountries": "ALL",
    "onMarketStartDate": [2026, 5, 1],
}


class EprelMappingTests(unittest.TestCase):
    def test_maps_dishwasher_to_digital_product_memory_passport(self) -> None:
        passport = to_passport(DISHWASHER_PAYLOAD)

        self.assertEqual(passport["product_id"], "2613426")
        self.assertEqual(passport["product_type"], "dishwasher")
        self.assertEqual(passport["manufacturer"], "Siemens")
        self.assertEqual(passport["model"], "SN43HW04ME")
        self.assertEqual(passport["energy_class"], "D")
        self.assertEqual(passport["warranty_years"], 2)
        self.assertEqual(passport["dimensions"], {"height_cm": 82, "width_cm": 60, "depth_cm": 57})
        self.assertEqual(passport["specifications"]["energy_consumption"]["kwh_per_100_cycles"], 85)
        self.assertEqual(passport["specifications"]["water_consumption_l"], 9)
        self.assertEqual(passport["specifications"]["programme_duration_min"], 270)
        self.assertEqual(passport["specifications"]["cleaning_performance_index"], 1.121)
        self.assertEqual(passport["specifications"]["drying_performance_index"], 1.061)
        self.assertEqual(passport["compliance"]["product_group"], "dishwashers2019")
        self.assertEqual(passport["market"]["on_market_start_date"], "2026-04-29")
        self.assertIn("/screen/product/dishwashers2019/2613426", passport["external_links"]["eprel_product_page"])
        self.assertIs(passport["eprel"], DISHWASHER_PAYLOAD)

    def test_maps_washing_machine_specific_fields(self) -> None:
        passport = to_passport(WASHING_MACHINE_PAYLOAD)

        self.assertEqual(passport["product_id"], "2219971")
        self.assertEqual(passport["product_type"], "washing_machine")
        self.assertEqual(passport["manufacturer"], "Bosch")
        self.assertEqual(passport["energy_class"], "A")
        self.assertEqual(passport["specifications"]["energy_consumption"]["kwh_per_100_cycles"], 47)
        self.assertEqual(passport["specifications"]["programme_duration_min"], 205)
        self.assertEqual(passport["specifications"]["spin_class"], "B")
        self.assertEqual(passport["specifications"]["spin_speed_rpm"], 1351)
        self.assertEqual(passport["washing_efficiency_index"], 1.031)

    def test_catalog_item_uses_normalized_identity_fields(self) -> None:
        item = to_catalog_item(to_passport(DISHWASHER_PAYLOAD))

        self.assertEqual(
            item,
            {
                "product_id": "2613426",
                "product_type": "dishwasher",
                "manufacturer": "Siemens",
                "model": "SN43HW04ME",
                "energy_label": "D",
            },
        )

    def test_unknown_eprel_group_is_preserved_as_product_type(self) -> None:
        payload = {**DISHWASHER_PAYLOAD, "productGroup": "tumbledryers20232534"}
        passport = to_passport(payload)

        self.assertEqual(passport["product_type"], "tumbledryers20232534")
        self.assertEqual(passport["compliance"]["product_group"], "tumbledryers20232534")

    def test_extracts_product_search_items_from_eprel_list_payloads(self) -> None:
        payload = {"products": [{"modelIdentifier": "SN43HW04ME", "eprelRegistrationNumber": 2613426}]}

        self.assertEqual(_extract_product_search_items(payload), payload["products"])

    def test_extracts_product_search_items_from_eprel_hit_payloads(self) -> None:
        payload = {"hits": {"hits": [{"_source": {"modelIdentifier": "SN43HW04ME", "eprelRegistrationNumber": 2613426}}]}}

        self.assertEqual(
            _extract_product_search_items(payload),
            [{"modelIdentifier": "SN43HW04ME", "eprelRegistrationNumber": 2613426}],
        )

    def test_model_identifier_matching_ignores_case_and_spaces(self) -> None:
        products = [
            {"modelIdentifier": "SN 43 HW 04 ME", "eprelRegistrationNumber": 2613426},
            {"modelIdentifier": "OTHER", "eprelRegistrationNumber": 1},
        ]

        match = _best_model_identifier_match(products, "sn43hw04me")

        self.assertEqual(_registration_number(match), "2613426")


class EprelApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_metadata_exposes_provider_contract(self) -> None:
        response = self.client.get("/.well-known/circthread-service")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["name"], "EU EPREL Provider")
        self.assertEqual(payload["provider"], "European Commission EPREL")
        self.assertIn("dishwasher", payload["product_types"])
        self.assertIn("washing_machine", payload["product_types"])
        self.assertIn("dishwashers2019", payload["conditions"]["supported_eprel_product_groups"])

    def test_product_endpoint_returns_mapped_passport(self) -> None:
        with patch("app.main.fetch_eprel_product_by_identifier", new=AsyncMock(return_value=DISHWASHER_PAYLOAD)):
            response = self.client.get("/products/2613426")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product_id"], "2613426")
        self.assertEqual(payload["product_type"], "dishwasher")
        self.assertEqual(payload["energy_class"], "D")

    def test_product_endpoint_accepts_model_identifier(self) -> None:
        with patch("app.main.fetch_eprel_product_by_identifier", new=AsyncMock(return_value=DISHWASHER_PAYLOAD)) as fetch:
            response = self.client.get("/products/SN43HW04ME")

        self.assertEqual(response.status_code, 200)
        fetch.assert_awaited_once_with("SN43HW04ME")
        self.assertEqual(response.json()["product_id"], "2613426")

    def test_product_endpoint_can_return_raw_eprel_payload(self) -> None:
        with patch("app.main.fetch_eprel_product_by_identifier", new=AsyncMock(return_value=DISHWASHER_PAYLOAD)):
            response = self.client.get("/products/2613426?raw=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), DISHWASHER_PAYLOAD)

    def test_product_endpoint_maps_not_found_to_404(self) -> None:
        with patch("app.main.fetch_eprel_product_by_identifier", new=AsyncMock(side_effect=EprelNotFoundError("missing"))):
            response = self.client.get("/products/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"])

    def test_product_endpoint_maps_upstream_failure_to_502(self) -> None:
        with patch("app.main.fetch_eprel_product_by_identifier", new=AsyncMock(side_effect=EprelUpstreamError("timeout"))):
            response = self.client.get("/products/2613426")

        self.assertEqual(response.status_code, 502)
        self.assertIn("EPREL upstream error", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
