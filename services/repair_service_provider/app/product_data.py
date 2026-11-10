"""Repair and service records for the CircThread Digital Product Passport products.

The Repair & Service Network Provider represents an independent network of repairers,
refurbishers, and authorised service partners. It reports what happens to a product unit
during its use phase: fault codes, repairs, service intervals, service contracts,
spare-part sourcing, and refurbishment grading.

For the CircThread partner products it complements the Midlife Purchase Provider with the
records that provider does not hold, so the two providers do not report conflicting values.
For the two products identified by their EPREL registration number (2219971 Bosch
WAN28283ES, 2613426 Siemens SN43HW04ME) it is the main source of use-phase data.
SP-SUNPOWER-002 is deliberately not covered: it remains the example of a unit with an
incomplete passport.
"""

PRODUCTS = {
    # ─────────────────────────── WASHING MACHINES ───────────────────────────

    "WM-GORENJE-001": {
        "product_id": "WM-GORENJE-001",
        "product_type": "washing_machine",
        "manufacturer": "Gorenje (Hisense Group)",
        "model": "WNA 94 ARIWIFI",
        "fault_code_history": [
            "E23 – drain time exceeded, drain filter blocked by a coin (cleared by user, 2024-08-28)",
        ],
        "service_contract_type": "Gorenje Care+ extended warranty via MediaMarkt (5 years, parts and labour)",
        "service_contract_expiry": "2029-02-20",
        "inspection_date": "2024-09-05",
        "refurbishment_grade": "A – pre-assessment at inspection 2024-09-05: functional and cosmetic condition as new",
        "lubrication_schedule": "No user lubrication required – sealed drum bearings; check bearings and shock absorbers at the 5-year service",
        "filter_replacement_interval_months": 60,
        "spare_parts_cost_index": 0.9,
    },

    "WM-BOSCH-001": {
        "product_id": "WM-BOSCH-001",
        "product_type": "washing_machine",
        "manufacturer": "BSH Hausgeräte GmbH",
        "model": "WAX32M92 Serie 8",
        "fault_code_history": [
            "F18 – drain pump blocked (lint in pump filter, cleared at service 2025-09-18)",
            "E17 – water inlet too slow (tap half closed, resolved by user 2024-02-03)",
        ],
        "service_contract_type": "Bosch Plus extended warranty (5 years, parts and labour)",
        "service_contract_expiry": "2028-07-01",
        "inspection_date": "2025-09-18",
        "refurbishment_grade": "B – functional condition very good, light scratches on top cover (pre-assessment 2025-09-18)",
        "lubrication_schedule": "No user lubrication required – sealed drum bearings; inspect bearings and drive motor at 12-month service check",
        "filter_replacement_interval_months": 48,
        "spare_parts_cost_index": 1.1,
    },

    "2219971": {
        "product_id": "2219971",
        "product_type": "washing_machine",
        "manufacturer": "Bosch",
        "model": "WAN28283ES",
        "maintenance_schedule": [
            {"interval_months": 1, "task": "Wipe door seal and detergent drawer, leave door ajar after use"},
            {"interval_months": 2, "task": "Run 'Drum Clean' programme at 90 °C without laundry"},
            {"interval_months": 6, "task": "Clean drain pump filter and inlet hose mesh filter"},
            {"interval_months": 24, "task": "Inspect hoses, door seal, shock absorbers, and drum bearings"},
        ],
        "repair_history": [
            {
                "date": "2026-10-14",
                "provider": "Bosch Service (BSH Kundendienst) Madrid",
                "action": "Replaced door seal (torn by laundry clip)",
                "result": "Operational",
                "cost_eur": 89.0,
            },
        ],
        "fault_code_history": [
            "E18 – drain pump filter blocked (cleared by user, 2026-08-03)",
            "Door seal leak reported by user (repaired 2026-10-14)",
        ],
        "last_service_date": "2026-10-14",
        "next_service_due_date": "2028-10-14",
        "service_provider_name": "Bosch Service (BSH Kundendienst) Madrid",
        "inspection_date": "2026-10-14",
        "total_repair_count": 1,
        "condition_grade": "B",
        "remote_diagnostic_capable": False,
        "descaling_interval_months": 6,
        "filter_replacement_interval_months": 48,
        "lubrication_schedule": "No user lubrication required – sealed drum bearings",
        "spare_parts_availability_years": 10,
        "spare_parts_supplier": "Bosch Home spare parts shop – bosch-home.com/spareparts",
        "spare_parts_cost_index": 1.0,
        "repair_difficulty_score": 4,
        "repairability_score": 6.9,
        "repair_cost_estimate_eur": 140.0,
        "refurbishment_grade": "B – fully functional, door seal replaced, light wear on drawer",
        "service_contract_type": "Statutory warranty only (2 years); Bosch Service repair on demand",
        "installation_date": "2026-05-20",
        "installer_name": "MediaMarkt Installation Service Madrid",
        "installation_location": "Madrid, Spain",
        "ownership_type": "owned",
        "usage_cycles_total": 95,
        "usage_hours_total": 160,
        "performance_degradation_pct": 0.3,
        "mean_time_between_failures_h": 4200,
    },

    # ─────────────────────────── DISHWASHERS ───────────────────────────

    "DW-SIEMENS-001": {
        "product_id": "DW-SIEMENS-001",
        "product_type": "dishwasher",
        "manufacturer": "BSH Hausgeräte GmbH",
        "model": "SN65ZX49CE iQ500",
        "service_contract_type": "Siemens extended warranty (5 years, parts and labour)",
        "service_contract_expiry": "2029-02-01",
        "inspection_date": "2025-03-10",
        "refurbishment_grade": "A – pre-assessment 2025-03-10: spray arm replaced, no visible wear",
        "descaling_interval_months": 6,
        "filter_replacement_interval_months": 60,
        "lubrication_schedule": "No lubrication required; lightly grease door hinge springs only when replaced",
        "spare_parts_cost_index": 1.2,
    },

    "2613426": {
        "product_id": "2613426",
        "product_type": "dishwasher",
        "manufacturer": "Siemens",
        "model": "SN43HW04ME",
        "maintenance_schedule": [
            {"interval_months": 1, "task": "Clean filter combination and check spray arm nozzles"},
            {"interval_months": 1, "task": "Refill rinse aid and regeneration salt as indicated"},
            {"interval_months": 6, "task": "Run machine-care programme with dishwasher cleaner at 70 °C"},
            {"interval_months": 24, "task": "Check door seal, drain hose, and aquaStop hose for damage"},
        ],
        "repair_history": [
            {
                "date": "2026-09-22",
                "provider": "Siemens Hausgeräte Kundendienst München",
                "action": "Replaced circulation pump heater (fault E09)",
                "result": "Operational",
                "cost_eur": 165.0,
            },
        ],
        "fault_code_history": [
            "E24 – drain blocked by food residue (cleared by user, 2026-07-30)",
            "E09 – heating element of circulation pump faulty (repaired 2026-09-22)",
        ],
        "last_service_date": "2026-09-22",
        "next_service_due_date": "2028-09-22",
        "service_provider_name": "Siemens Hausgeräte Kundendienst München",
        "inspection_date": "2026-09-22",
        "total_repair_count": 1,
        "condition_grade": "A",
        "remote_diagnostic_capable": True,
        "descaling_interval_months": 6,
        "filter_replacement_interval_months": 60,
        "lubrication_schedule": "No lubrication required",
        "spare_parts_availability_years": 10,
        "spare_parts_supplier": "Siemens Home spare parts shop – siemens-home.bsh-group.com/spareparts",
        "spare_parts_cost_index": 1.1,
        "repair_difficulty_score": 5,
        "repairability_score": 6.5,
        "repair_cost_estimate_eur": 150.0,
        "refurbishment_grade": "A – circulation pump renewed, no visible wear",
        "service_contract_type": "Siemens extended warranty (3 years, parts and labour)",
        "service_contract_expiry": "2029-05-12",
        "installation_date": "2026-05-12",
        "installer_name": "Siemens Hausgeräte Kundendienst München",
        "installation_location": "Munich, Germany",
        "ownership_type": "owned",
        "usage_cycles_total": 110,
        "usage_hours_total": 330,
        "performance_degradation_pct": 0.4,
        "mean_time_between_failures_h": 5000,
    },

    # ─────────────────────────── BOILERS ───────────────────────────

    "BL-VAILLANT-001": {
        "product_id": "BL-VAILLANT-001",
        "product_type": "boiler",
        "manufacturer": "Vaillant Group",
        "model": "ecoTEC plus VCW 346/5-5",
        "service_contract_type": "Vaillant Care annual service plan (inspection, parts, and labour)",
        "service_contract_expiry": "2026-11-15",
        "inspection_date": "2025-08-05",
        "refurbishment_grade": "B – diverter valve and ignition electrode renewed; heat exchanger in good condition",
        "usage_cycles_total": 41800,
        "descaling_interval_months": 24,
        "filter_replacement_interval_months": 12,
        "lubrication_schedule": "No lubrication required – circulation pump bearings are water-lubricated",
        "spare_parts_cost_index": 1.3,
    },

    # ─────────────────────────── LITHIUM BATTERIES ───────────────────────────

    "LB-LG-001": {
        "product_id": "LB-LG-001",
        "product_type": "lithium_battery",
        "manufacturer": "LG Energy Solution",
        "model": "RESU 16H Prime",
        "repair_history": [
            {
                "date": "2025-05-27",
                "provider": "SolarService Pro GmbH (LG Energy Solution certified installer)",
                "action": "Annual inspection, BMS firmware update, cable terminals re-torqued",
                "result": "Operational, state of health 98.6 %",
                "cost_eur": 0.0,
            },
        ],
        "fault_code_history": [
            "W-BMS-012 – cell temperature warning during heatwave (self-cleared 2025-07-14)",
        ],
        "last_service_date": "2025-05-27",
        "service_provider_name": "SolarService Pro GmbH (LG Energy Solution certified installer)",
        "inspection_date": "2025-05-27",
        "spare_parts_supplier": "LG Energy Solution Service Europe – replacement modules via certified installers",
        "spare_parts_cost_index": 1.4,
        "service_contract_type": "Installer maintenance contract (annual inspection and remote monitoring)",
        "service_contract_expiry": "2029-05-25",
        "refurbishment_grade": "A – second-life candidate (state of health above 95 %)",
    },

    # ─────────────────────────── SOLAR PANELS ───────────────────────────

    "SP-SUNPOWER-001": {
        "product_id": "SP-SUNPOWER-001",
        "product_type": "solar_panel",
        "manufacturer": "SunPower / Maxeon Solar",
        "model": "Maxeon 6 AC SPR-MAX6-440-COM-AC",
        "repair_history": [
            {
                "date": "2025-04-10",
                "provider": "Maxeon Certified Installer Network",
                "action": "Annual inspection and IV-curve check; MC4 connector re-seated",
                "result": "Output within 1.2 % of rated power",
                "cost_eur": 95.0,
            },
        ],
        "fault_code_history": [
            "Enphase IQ8A – 'DC resistance low' event (cleared after connector re-seat, 2025-04-10)",
        ],
        "last_service_date": "2025-04-10",
        "inspection_date": "2025-04-10",
        "spare_parts_supplier": "Maxeon Warranty Services; Enphase Energy (IQ8A microinverter replacement)",
        "spare_parts_cost_index": 0.8,
        "service_contract_type": "Installer operation and maintenance contract (annual inspection, cleaning on demand)",
        "service_contract_expiry": "2029-03-15",
        "refurbishment_grade": "A – reuse candidate (no visible defects, power above 98 % of rating)",
    },
}


def get_product(product_id: str) -> dict | None:
    return PRODUCTS.get(product_id)


def get_all_products() -> list[dict]:
    return list(PRODUCTS.values())
