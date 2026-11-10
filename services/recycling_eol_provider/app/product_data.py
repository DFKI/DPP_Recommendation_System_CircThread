"""End-of-life data for CircThread Digital Product Passport products.

Covers washing machines, dishwashers, lithium batteries, and solar panels
across key CircThread partner brands: Gorenje, BSH (Bosch/Siemens), LG Energy Solution, Maxeon/SunPower.
"""

PRODUCTS = {
    # ─────────────────────────── WASHING MACHINES ───────────────────────────

    "WM-GORENJE-001": {
        "product_id": "WM-GORENJE-001",
        "product_type": "washing_machine",
        "manufacturer": "Gorenje (Hisense Group)",
        "model": "WNA 94 ARIWIFI",
        "materials": [
            {"material": "Steel (chassis, drum, counterweight support)", "percentage": 42, "recyclable": True, "hazardous": False},
            {"material": "Plastic (PP/ABS/HIPS – casing, drawer, pump housing)", "percentage": 21, "recyclable": True, "hazardous": False},
            {"material": "Concrete (counterweight)", "percentage": 18, "recyclable": False, "hazardous": False},
            {"material": "Copper (motor windings, wiring)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Glass (door porthole)", "percentage": 4, "recyclable": True, "hazardous": False},
            {"material": "Rubber – EPDM (door seal, hoses)", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Aluminium (motor housing, brackets)", "percentage": 2, "recyclable": True, "hazardous": False},
            {"material": "Printed circuit boards (control electronics)", "percentage": 3, "recyclable": False, "hazardous": True},
            {"material": "Neodymium magnets (BLDC motor)", "percentage": 0.3, "recyclable": True, "hazardous": False},
            {"material": "Miscellaneous metals (fasteners, springs)", "percentage": 1.7, "recyclable": True, "hazardous": False},
        ],
        "hazardous_substances": [
            {
                "name": "Brominated flame retardants (PCB plastic coating)",
                "cas_number": "25637-99-4",
                "concentration_pct": 0.008,
                "regulation": "REACH SVHC candidate list",
                "safety_instructions": "Remove control board before shredding. Route PCB fraction to certified WEEE processor. Do not compact with mixed plastics.",
            },
            {
                "name": "DEHP plasticizer (EPDM door seal)",
                "cas_number": "117-81-7",
                "concentration_pct": 0.004,
                "regulation": "REACH SVHC (Annex XIV)",
                "safety_instructions": "Separate rubber door seal; dispose via WEEE stream. Do not co-incinerate with other plastics.",
            },
        ],
        "disassembly_instructions": (
            "1. Disconnect power and water supplies. "
            "2. Remove top panel (2× Phillips M4 screws at rear). "
            "3. Remove back panel (6× Torx T20). "
            "4. Disconnect and remove water inlet valve and drain hoses. "
            "5. Remove front panel (4× Torx T20 + door seal clamp spring). "
            "6. Remove counterweight retaining bolts (2× 13mm). "
            "7. Remove drive belt and unbolt motor (3× M6). "
            "8. Lift out drum assembly from the front opening. "
            "9. Separate neodymium magnets from motor stator before shredding."
        ),
        "recycling_instructions": (
            "Priority material streams: "
            "(1) Steel chassis/drum → shredder + magnetic separation (high value). "
            "(2) Copper motor windings → hand-strip before shredding (3.4 kg Cu/unit). "
            "(3) Neodymium magnets (~180 g) → route to RE magnet recycler (Cyclic Materials, REEtec). "
            "(4) Aluminium brackets → separate fraction, direct remelt. "
            "(5) Glass door porthole → glass cullet recycler. "
            "(6) PCB/control board → certified WEEE processor (Stena Recycling, Boliden). "
            "(7) EPDM rubber seals → specialist rubber recycling (Genan). "
            "(8) Concrete counterweight → construction & demolition mineral waste. "
            "(9) PP/ABS/HIPS plastics → sortable thermoplastics stream (after removing hazardous fractions). "
            "CircThread certified recyclers: Saubermacher (SI/AT/HR), PreZero (DE), Lobbe (DE)."
        ),
        "disposal_instructions": (
            "Do not dispose in municipal waste. "
            "Free take-back via: (a) MediaMarkt stores (CircThread take-back partner, 1,000+ locations EU-wide); "
            "(b) Gorenje authorized dealers; (c) municipal WEEE collection points. "
            "Reference EPR registration: EPR-SI-GORENJE-2024-WM-0047."
        ),
        "recyclability_pct": 80.0,
        "residual_value_eur": 85.0,
        "disassembly_time_estimate_min": 45,
        "component_separation_difficulty": "Medium – standard Torx/Phillips required; drum extraction needs 2 persons",
        "end_of_life_collection_point": "MediaMarkt (CircThread network, 1000+ EU stores), Gorenje dealers, municipal WEEE",
        "remanufacturing_eligibility": True,
        "refurbishment_grade": None,
        "weee_category": "WEEE Category 1 – Large Household Appliances",
        "weee_treatment_instructions": (
            "Pre-treat per Annex VII WEEE Directive 2012/19/EU. "
            "Remove capacitors, PCB fraction and motor before bulk shredding. "
            "Decontaminate EPDM rubber before combined waste stream. "
            "Minimum 85% recovery rate target."
        ),
        "critical_material_recovery_instructions": (
            "PRIORITY: Extract BLDC motor neodymium magnets (~180 g Nd per unit) before shredding. "
            "Hand-strip copper motor windings (3.4 kg Cu). "
            "Route PCB to e-waste smelter for gold/silver/palladium recovery."
        ),
        "dismantling_information_url": "https://circthread.eu/dpp/WM-GORENJE-001/dismantling",
        "urban_mining_priority": False,
        "scrap_metal_value_eur": 22.0,
        "end_of_life_value_eur": 45.0,
        "epr_fee_eur": 4.20,
        "recycling_route": "WEEE Category 1 – CircThread certified network (Saubermacher SI/AT, PreZero DE)",
        "last_updated": "2026-05-15",
    },

    "WM-BOSCH-001": {
        "product_id": "WM-BOSCH-001",
        "product_type": "washing_machine",
        "manufacturer": "BSH Hausgeräte GmbH",
        "model": "WAX32M92 Serie 8",
        "materials": [
            {"material": "Steel", "percentage": 44, "recyclable": True, "hazardous": False},
            {"material": "Plastic (PP/ABS mix)", "percentage": 24, "recyclable": True, "hazardous": False},
            {"material": "Concrete counterweight", "percentage": 16, "recyclable": False, "hazardous": False},
            {"material": "Copper (motor windings, wiring)", "percentage": 6, "recyclable": True, "hazardous": False},
            {"material": "Glass (door)", "percentage": 4, "recyclable": True, "hazardous": False},
            {"material": "Rubber (EPDM door seal)", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Printed circuit boards", "percentage": 3, "recyclable": False, "hazardous": True},
        ],
        "hazardous_substances": [
            {
                "name": "Brominated flame retardants in PCB plastics",
                "cas_number": None,
                "concentration_pct": 0.04,
                "regulation": "REACH SVHC screening",
                "safety_instructions": "Remove control board before shredding. Route PCB fraction to certified WEEE processor.",
            },
            {
                "name": "Electrolytic capacitors on control board",
                "cas_number": None,
                "concentration_pct": 0.02,
                "regulation": "WEEE",
                "safety_instructions": "Keep electronics fraction separate. Do not compact with mixed plastics.",
            },
        ],
        "disassembly_instructions": (
            "Disconnect power and water. Remove top cover, back panel, detergent drawer, "
            "control board, motor, drum assembly, door glass, and counterweight. "
            "Separate electronics before bulk material processing. "
            "Remove EcoSilence BLDC motor neodymium magnets (~210 g) before shredding."
        ),
        "recycling_instructions": (
            "Prioritize steel (chassis, drum), copper (motor windings, 4.1 kg/unit), glass door, "
            "and sortable thermoplastics. Recover neodymium motor magnets before shredding. "
            "Send PCB/control-board fraction to WEEE treatment (Stena/Boliden). "
            "Concrete counterweight: construction & demolition mineral waste stream. "
            "CircThread certified recyclers: BSH/Hamos network (DE), Saubermacher (AT/SI)."
        ),
        "disposal_instructions": (
            "Do not dispose in municipal residual waste. "
            "Return to MediaMarkt/Saturn (BSH take-back partner) free of charge, "
            "BSH authorized service centre, or municipal WEEE collection. "
            "EPR registration: EPR-DE-BSH-2023-WM-0082."
        ),
        "recyclability_pct": 84.0,
        "residual_value_eur": 135.0,
        "disassembly_time_estimate_min": 50,
        "component_separation_difficulty": "Medium",
        "end_of_life_collection_point": "MediaMarkt/Saturn (BSH partner), BSH dealers, municipal WEEE collection EU-wide",
        "remanufacturing_eligibility": True,
        "weee_category": "WEEE Category 1 – Large Household Appliances",
        "weee_treatment_instructions": "Pre-treat per Annex VII WEEE Directive 2012/19/EU. Remove capacitors and PCB. Min 85% recovery rate.",
        "critical_material_recovery_instructions": "Remove EcoSilence motor (~210 g Nd magnets) before shredding. Copper winding hand-strip (4.1 kg Cu/unit).",
        "dismantling_information_url": "https://circthread.eu/dpp/WM-BOSCH-001/dismantling",
        "urban_mining_priority": False,
        "scrap_metal_value_eur": 28.0,
        "end_of_life_value_eur": 55.0,
        "epr_fee_eur": 4.80,
        "recycling_route": "WEEE Category 1 – BSH/Hamos certified treatment (DE) + Saubermacher (AT/SI)",
        "last_updated": "2026-05-15",
    },

    # ─────────────────────────── DISHWASHER ─────────────────────────────────

    "DW-SIEMENS-001": {
        "product_id": "DW-SIEMENS-001",
        "product_type": "dishwasher",
        "manufacturer": "BSH Hausgeräte GmbH",
        "model": "SN65ZX49CE iQ500",
        "materials": [
            {"material": "Stainless Steel (inner tub, spray arms, door inner)", "percentage": 55, "recyclable": True, "hazardous": False},
            {"material": "Plastic (PP/ABS – outer casing, baskets, dispenser)", "percentage": 20, "recyclable": True, "hazardous": False},
            {"material": "Copper (pump motor windings, wiring)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Zeolite mineral (drying unit)", "percentage": 8, "recyclable": False, "hazardous": False},
            {"material": "Glass fibre insulation (acoustic)", "percentage": 5, "recyclable": False, "hazardous": False},
            {"material": "Rubber / Seals (door gasket, hoses)", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Printed circuit boards", "percentage": 4, "recyclable": False, "hazardous": True},
        ],
        "hazardous_substances": [
            {
                "name": "Lead in PCB solder (RoHS exempt)",
                "cas_number": "7439-92-1",
                "concentration_pct": 0.01,
                "regulation": "RoHS 2011/65/EU (exempt Annex III)",
                "safety_instructions": "Handle PCB fraction with gloves. Route to WEEE certified e-waste processor. Do not shred with general metal fraction.",
            },
        ],
        "disassembly_instructions": (
            "1. Disconnect power and water. "
            "2. Remove outer side panels (Torx T15). "
            "3. Remove bottom kick-plate. "
            "4. Access circulation and drain pumps from below. "
            "5. Spray arms pull off directly (quarter-turn). "
            "6. Remove insulation blanket from outer tub. "
            "7. Control board accessed by removing inner front door panel. "
            "8. Separate zeolite drying unit (lower right) – mineral fraction."
        ),
        "recycling_instructions": (
            "Priority streams: "
            "(1) Stainless steel inner tub and door → direct scrap; high grade (55% by mass). "
            "(2) Copper pump motor windings (2.5 kg Cu/unit) → hand-strip or eddy-current separation. "
            "(3) Zeolite mineral → separate fraction; specialist mineral recycler or landfill. "
            "(4) Glass fibre insulation → landfill (hazardous waste boundary check required). "
            "(5) PCB/electronics → certified WEEE processor. "
            "(6) PP/ABS plastics → sortable thermoplastics after decontamination. "
            "CircThread certified recyclers: Hamos (DE), Saubermacher (AT/SI/HR)."
        ),
        "disposal_instructions": (
            "Return to MediaMarkt/Saturn (BSH take-back partner), BSH dealers, or municipal WEEE. "
            "Free collection under EPR-DE-BSH-2024-DW-0091. Do not dispose in household waste."
        ),
        "recyclability_pct": 78.0,
        "residual_value_eur": 70.0,
        "disassembly_time_estimate_min": 35,
        "component_separation_difficulty": "Medium – zeolite unit must be removed before shredding",
        "end_of_life_collection_point": "MediaMarkt/Saturn (BSH partner), BSH dealers, municipal WEEE EU-wide",
        "remanufacturing_eligibility": True,
        "weee_category": "WEEE Category 1 – Large Household Appliances",
        "weee_treatment_instructions": (
            "Pre-treat per Annex VII WEEE Directive 2012/19/EU. "
            "Remove PCB and pump before bulk shredding. "
            "Separate zeolite unit (mineral fraction) from metal/plastic streams."
        ),
        "critical_material_recovery_instructions": "Copper pump windings (2.5 kg/unit) – hand-strip before bulk shredding for higher Cu recovery.",
        "dismantling_information_url": "https://circthread.eu/dpp/DW-SIEMENS-001/dismantling",
        "urban_mining_priority": False,
        "scrap_metal_value_eur": 32.0,
        "end_of_life_value_eur": 38.0,
        "epr_fee_eur": 3.60,
        "recycling_route": "WEEE Category 1 – BSH/Hamos certified treatment network (DE/EU)",
        "last_updated": "2026-05-15",
    },

    # ─────────────────────────── LITHIUM BATTERY ────────────────────────────

    "LB-LG-001": {
        "product_id": "LB-LG-001",
        "product_type": "lithium_battery",
        "manufacturer": "LG Energy Solution",
        "model": "RESU 16H Prime",
        "materials": [
            {"material": "Nickel (NMC cathode)", "percentage": 15, "recyclable": True, "hazardous": True},
            {"material": "Manganese (NMC cathode)", "percentage": 8, "recyclable": True, "hazardous": True},
            {"material": "Cobalt (NMC cathode)", "percentage": 6, "recyclable": True, "hazardous": True},
            {"material": "Lithium (cathode + electrolyte)", "percentage": 4, "recyclable": True, "hazardous": True},
            {"material": "Graphite (anode)", "percentage": 15, "recyclable": True, "hazardous": False},
            {"material": "Aluminium (housing, foil)", "percentage": 18, "recyclable": True, "hazardous": False},
            {"material": "Copper (foil, wiring)", "percentage": 12, "recyclable": True, "hazardous": False},
            {"material": "Steel (enclosure)", "percentage": 10, "recyclable": True, "hazardous": False},
            {"material": "Electrolyte (LiPF6 in organic solvent)", "percentage": 8, "recyclable": False, "hazardous": True},
            {"material": "Plastic / PE separator", "percentage": 4, "recyclable": False, "hazardous": False},
        ],
        "hazardous_substances": [
            {
                "name": "Lithium (Li) – thermal runaway risk",
                "cas_number": "7439-93-2",
                "concentration_pct": 4.0,
                "regulation": "EU Battery Regulation 2023/1542 / ADR Class 9",
                "safety_instructions": "Discharge to <10% SOC before any disassembly. Never puncture, crush, or short-circuit. Transport as UN3480 dangerous goods. Store in fire-rated cabinet away from combustibles.",
            },
            {
                "name": "Cobalt (Co) – carcinogenic dust",
                "cas_number": "7440-48-4",
                "concentration_pct": 6.0,
                "regulation": "EU Battery Regulation (due diligence); CLP Regulation",
                "safety_instructions": "Full PPE (P3 respirator, nitrile gloves, safety goggles) during recycling operations. Avoid dust inhalation. Wash hands thoroughly after handling.",
            },
            {
                "name": "Nickel (Ni) compounds – respiratory sensitizer",
                "cas_number": "7440-02-0",
                "concentration_pct": 15.0,
                "regulation": "REACH SVHC candidate; CLP carcinogen cat. 1A",
                "safety_instructions": "Avoid skin contact and inhalation of nickel-containing dust. Use exhaust ventilation at recycling stations.",
            },
            {
                "name": "LiPF6 electrolyte – toxic/corrosive, HF release on water contact",
                "cas_number": "21324-40-3",
                "concentration_pct": 5.0,
                "regulation": "GHS/CLP; REACH",
                "safety_instructions": "Reacts violently with water to produce hydrogen fluoride (HF). Emergency shower and eyewash station required. Do NOT extinguish lithium battery fires with water. Use Class D extinguisher or dry sand.",
            },
        ],
        "disassembly_instructions": (
            "⚠ HIGH VOLTAGE SYSTEM – Qualified personnel only. ⚠ "
            "1. Discharge battery to SOC <10% using controlled load. "
            "2. Activate integrated DC disconnect switch. "
            "3. Wait minimum 5 minutes for capacitor discharge; verify 0 V with multimeter. "
            "4. Remove enclosure M6 bolts (× 8). "
            "5. Disconnect BMS control and monitoring connectors carefully. "
            "6. Extract individual modules one at a time (~25 kg each; use mechanical aid). "
            "7. Do NOT open individual battery modules – cell-level disassembly requires robotised process. "
            "8. Log serial number and SOH in CircThread battery passport before handing to recycler."
        ),
        "recycling_instructions": (
            "EU Battery Regulation 2023/1542 mandates: ≥70% recycling efficiency by weight (2030), "
            "≥4% Li recovery, ≥12% Co recovery, ≥4% Ni recovery. "
            "Process: discharge → shred under inert atmosphere or CO2 → black mass separation → "
            "hydrometallurgical leaching (H2SO4/H2O2) → precipitation of Co, Ni, Mn, Li salts → "
            "electrolyte solvent recovery (organic distillation). "
            "Cu foil and Al foil: eddy-current separation post-shredding. "
            "EU certified recyclers: Umicore (BE), Hydrovolt (NO/DE), Northvolt Revolt (SE), Stena Recycling (SE/DE). "
            "Battery must be accompanied by EU Battery Passport MPREF-CIRCTHREAD-LB-LG-001."
        ),
        "disposal_instructions": (
            "NEVER dispose in household waste or municipal landfill. NEVER incinerate. "
            "Mandatory producer take-back under EU Battery Regulation and EPR-EU-LGES-2024-BAT-0022. "
            "Transport exclusively as ADR Class 9 (UN3480) with certified dangerous-goods carrier. "
            "Contact LGES EU take-back service: battery-eol@example.com"
        ),
        "recyclability_pct": 70.0,
        "residual_value_eur": 1200.0,
        "second_life_eligibility": True,
        "disassembly_time_estimate_min": 90,
        "component_separation_difficulty": "Hard – high voltage hazard, specialised PPE and training mandatory",
        "end_of_life_collection_point": "LGES EU take-back programme; Accurec GmbH (DE); Redux GmbH (DE); Hydrovolt (NO/DE)",
        "remanufacturing_eligibility": True,
        "weee_category": "WEEE Category 2 – Small Household Appliances (stationary storage)",
        "weee_treatment_instructions": "Comply with EU Battery Regulation 2023/1542 AND WEEE Directive 2012/19/EU. Battery Regulation takes precedence for cell chemistry fraction.",
        "critical_material_recovery_instructions": (
            "PRIORITY recovery targets per EU Battery Regulation 2031 targets: "
            "Cobalt ≥95% (6.6 kg/unit, €50/kg recovery value), "
            "Nickel ≥98% (16.5 kg/unit), "
            "Lithium ≥70% (4.4 kg/unit, critical raw material). "
            "Route to hydrometallurgical plant only – pyrometallurgy loses Li."
        ),
        "battery_removal_instructions": "Discharge to <10% SOC. Isolate at BMS disconnect. Allow 5 min capacitor bleed. Refer to LGES service manual SVC-RESU16H-2024 for module extraction.",
        "dismantling_information_url": "https://circthread.eu/dpp/LB-LG-001/dismantling",
        "urban_mining_priority": True,
        "scrap_metal_value_eur": 195.0,
        "end_of_life_value_eur": 380.0,
        "cobalt_content_g": 6600,
        "lithium_content_g": 4400,
        "nickel_content_g": 16500,
        "epr_fee_eur": 28.00,
        "recycling_route": "EU Battery Regulation certified hydrometallurgical recycler (Umicore BE / Hydrovolt DE)",
        "last_updated": "2026-05-15",
    },

    # ─────────────────────────── SOLAR PANEL ────────────────────────────────

    "SP-SUNPOWER-001": {
        "product_id": "SP-SUNPOWER-001",
        "product_type": "solar_panel",
        "manufacturer": "SunPower / Maxeon Solar",
        "model": "Maxeon 6 AC SPR-MAX6-440-COM-AC",
        "materials": [
            {"material": "Tempered Solar Glass (AR coated)", "percentage": 70, "recyclable": True, "hazardous": False},
            {"material": "Anodized Aluminium Frame (6063-T5)", "percentage": 12, "recyclable": True, "hazardous": False},
            {"material": "EVA Encapsulant (ethylene vinyl acetate)", "percentage": 5, "recyclable": False, "hazardous": False},
            {"material": "Monocrystalline Silicon (IBC cells)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Tedlar-PET-Tedlar backsheet (TPT)", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Copper (junction box connectors, wiring)", "percentage": 3, "recyclable": True, "hazardous": False},
            {"material": "Silver (cell contacts)", "percentage": 0.5, "recyclable": True, "hazardous": False},
            {"material": "Other metals (Enphase microinverter components)", "percentage": 1.5, "recyclable": True, "hazardous": False},
        ],
        "hazardous_substances": [
            {
                "name": "Lead in junction box solder (RoHS exempt for PV)",
                "cas_number": "7439-92-1",
                "concentration_pct": 0.02,
                "regulation": "RoHS 2011/65/EU (Annex III, category 11 exempt)",
                "safety_instructions": "Handle junction box with gloves. Do not crush or incinerate junction box. Route to certified WEEE/PV recycler.",
            },
            {
                "name": "Silver (Ag) – critical raw material at cell level",
                "cas_number": "7440-22-4",
                "concentration_pct": 0.5,
                "regulation": "EU Critical Raw Materials Act 2024",
                "safety_instructions": "Not hazardous in normal use. Maximize silver recovery (109 g/panel) via hydrometallurgical processing at certified PV recycler.",
            },
        ],
        "disassembly_instructions": (
            "1. Isolate DC supply from grid and disconnect microinverter. "
            "2. Remove mounting clamp bolts from aluminium frame. "
            "3. Disengage MC4 connectors from adjacent panels (quarter-turn + press). "
            "4. Module is factory-laminated sealed unit – no field-level cell disassembly. "
            "5. Detach junction box (Torx T10 × 2) for separate processing. "
            "6. Transport complete module to certified PV recycler (PV Cycle collection point). "
            "Note: Enphase IQ8A microinverter must be separately removed and processed as WEEE."
        ),
        "recycling_instructions": (
            "PV Cycle certified process (target ≥80% mass recovery): "
            "(1) Aluminium frame (12%): direct remove and remelt – highest-value fraction, no contamination. "
            "(2) Junction box: detach; copper connectors to scrap, PPO plastic to WEEE plastics. "
            "(3) Microinverter (Enphase IQ8A): remove and process as WEEE electronics. "
            "(4) Glass laminate (70%): thermal delamination at 500°C → glass cullet reclaim, "
            "silicon cell recovery via acid etching (HNO3/HF), silver hydrometallurgical extraction. "
            "(5) EVA encapsulant: thermal decomposition by-products → energy recovery. "
            "(6) TPT backsheet: mechanical + thermal treatment. "
            "Silver recovery target: ≥95% of 109 g/panel – route to precious metal refiner (Heraeus/Umicore). "
            "Silicon recovery: ≥90% for secondary solar grade or metallurgical applications. "
            "PV Cycle partner recyclers: Reiling (DE), Veolia (FR), 3S PV recycling (CH)."
        ),
        "disposal_instructions": (
            "Covered by WEEE Directive (PV panels – Category 4). "
            "Return to: PV Cycle collection points (pvccycle.org/take-back), "
            "Maxeon installer return programme, or municipal WEEE. "
            "Free of charge under EPR-EU-PVCYCLE-MAXEON-2024-001. "
            "Do not dispose in general household waste or skip/dumpster."
        ),
        "recyclability_pct": 95.0,
        "residual_value_eur": 25.0,
        "disassembly_time_estimate_min": 20,
        "component_separation_difficulty": "Low for frame and junction box; High for cell laminate (requires thermal delamination plant)",
        "end_of_life_collection_point": "PV Cycle collection points EU-wide (pvccycle.org); Maxeon installer return; municipal WEEE",
        "remanufacturing_eligibility": False,
        "weee_category": "WEEE Category 4 – Consumer Equipment (photovoltaic panels)",
        "weee_treatment_instructions": "Process under WEEE Directive Annex VII. Remove aluminium frame before bulk treatment. Thermal delamination of laminate required.",
        "critical_material_recovery_instructions": (
            "PRIORITY: Silver (109 g/panel, EU Critical Raw Material). "
            "Route glass-silicon laminate to PV recycler with hydrometallurgical silver recovery line. "
            "Silicon secondary recovery (≥90%) for metallurgical-grade Si applications."
        ),
        "dismantling_information_url": "https://circthread.eu/dpp/SP-SUNPOWER-001/dismantling",
        "urban_mining_priority": False,
        "scrap_metal_value_eur": 18.0,
        "end_of_life_value_eur": 38.0,
        "silver_content_g": 109.0,
        "epr_fee_eur": 2.10,
        "recycling_route": "PV Cycle certified – glass-silicon thermal delamination + Ag hydrometallurgical recovery",
        "last_updated": "2026-05-15",
    },

    # ─────────────────────────── BOILER ────────────────────────────────────────

    "BL-VAILLANT-001": {
        "product_id": "BL-VAILLANT-001",
        "product_type": "boiler",
        "manufacturer": "Vaillant Group",
        "model": "ecoTEC plus VCW 346/5-5",
        "materials": [
            {"material": "Steel (heat exchanger body, casing)", "percentage": 38, "recyclable": True, "hazardous": False},
            {"material": "Copper (primary heat exchanger tubing)", "percentage": 22, "recyclable": True, "hazardous": False},
            {"material": "Aluminium (condensing secondary HX)", "percentage": 14, "recyclable": True, "hazardous": False},
            {"material": "Brass (valves, gas fittings)", "percentage": 10, "recyclable": True, "hazardous": False},
            {"material": "Plastic (PP/ABS – casing panels, condensate trap)", "percentage": 7, "recyclable": True, "hazardous": False},
            {"material": "Stainless steel (burner, flue)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Ceramics (insulation)", "percentage": 2, "recyclable": False, "hazardous": False},
            {"material": "Electronics (PCB, sensors)", "percentage": 1.5, "recyclable": False, "hazardous": True},
            {"material": "Rubber/seals (EPDM, silicone)", "percentage": 0.5, "recyclable": False, "hazardous": False},
        ],
        "hazardous_substances": [
            {
                "name": "Flue gas condensate (acidic, pH 3–4)",
                "cas_number": None,
                "concentration_pct": None,
                "regulation": "Local wastewater regulations / EN 13384",
                "safety_instructions": "Neutralise condensate before disposal. Use condensate neutralisation unit. Do not discharge undiluted to drain in sensitive areas.",
            },
            {
                "name": "Lead solder in PCB electronics",
                "cas_number": "7439-92-1",
                "concentration_pct": 0.01,
                "regulation": "RoHS 2011/65/EU (Annex III category 8 exempt for heating appliances)",
                "safety_instructions": "Route control board to certified WEEE electronics recycler. Do not crush PCB in bulk shredder.",
            },
        ],
        "disassembly_instructions": (
            "1. Isolate gas supply (close isolation valve) and electrical supply (230V). "
            "2. Allow boiler to cool fully before disassembly. "
            "3. Drain central heating circuit via drain cock (22mm hose connection, bottom right). "
            "4. Remove casing: unscrew 2× Torx T20 screws at bottom; lift front panel upward to release top clips. "
            "5. Disconnect flue pipe (push-fit adaptor, quarter-turn release) and condensate pipe. "
            "6. Disconnect gas pipe at union fitting (27mm spanner). "
            "7. Remove primary heat exchanger (2× M6 bolts; caution: residual hot water). "
            "8. Separate secondary condensing heat exchanger (aluminium, 4× M5 bolts). "
            "9. Remove burner assembly and ionisation probe for separate processing."
        ),
        "recycling_instructions": (
            "Material stream priorities: "
            "(1) Copper heat exchanger (22% mass) → strip and route to copper scrap dealer (high value). "
            "(2) Aluminium condensing HX → separate fraction, direct remelt. "
            "(3) Brass valves and fittings → brass scrap recycler. "
            "(4) Steel casing and body → shredder + magnetic separation. "
            "(5) Electronics (PCB, sensors) → certified WEEE processor (WEEE Category 4). "
            "(6) Gas valve with embedded electronics → certified gas appliance recycler. "
            "Registered collectors: Vaillant Take-Back Scheme (Germany/Austria), "
            "Bosch Thermotechnology network, municipal WEEE collection points."
        ),
        "disposal_instructions": (
            "Covered by WEEE Directive (heating appliances – Category 1 large appliance). "
            "Gas appliances must be decommissioned by Gas Safe / DVGW certified engineer before disposal. "
            "Return via: Vaillant partner installer take-back, "
            "municipal WEEE large appliance collection, or scrap merchant (after gas isolation). "
            "EPR registration: DE-VG-WEEE-2024-0083 (Vaillant Group Germany)."
        ),
        "recyclability_pct": 88.0,
        "end_of_life_value_eur": 55.0,
        "component_separation_difficulty": "Medium – requires Gas Safe decommissioning before disassembly; heat exchangers easily separable",
        "end_of_life_collection_point": "Vaillant take-back scheme (DE/AT/GB); municipal WEEE large appliance collection",
        "remanufacturing_eligibility": True,
        "weee_category": "WEEE Category 1 – Large Household Appliances (heating appliances)",
        "weee_treatment_instructions": "Drain all water circuits before transport. Remove and isolate PCB. Process aluminium condensing HX separately.",
        "urban_mining_priority": False,
        "recycling_route": "WEEE Category 1 – certified heating appliance recycler + copper scrap dealer",
        "last_updated": "2026-05-15",
        # INTENTIONAL GAPS (realistic – boiler-specific recycling data not yet fully populated in CircThread DPP Hub):
        # - disassembly_time_estimate_min: not provided
        # - critical_material_recovery_instructions: not provided
        # - scrap_metal_value_eur: not provided (pending scrap market valuation)
        # - epr_fee_eur: not provided (EPR fee structure varies by installer scheme)
        # - urban_mining_priority: False (no rare earths or critical materials)
    },

    # ─────────────────────────── SOLAR PANELS (second unit) ────────────────────

    "SP-SUNPOWER-002": {
        "product_id": "SP-SUNPOWER-002",
        "product_type": "solar_panel",
        "manufacturer": "Maxeon Solar Technologies (SunPower)",
        "model": "Maxeon 6 AC SPR-MAX6-440-COM-AC",
        "materials": [
            {"material": "Tempered Solar Glass (AR coated)", "percentage": 70, "recyclable": True, "hazardous": False},
            {"material": "Anodized Aluminium Frame (6063-T5)", "percentage": 12, "recyclable": True, "hazardous": False},
            {"material": "EVA Encapsulant", "percentage": 5, "recyclable": False, "hazardous": False},
            {"material": "Monocrystalline Silicon (IBC cells)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Tedlar-PET-Tedlar backsheet", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Copper (junction box, wiring)", "percentage": 3, "recyclable": True, "hazardous": False},
            {"material": "Silver (cell contacts)", "percentage": 0.5, "recyclable": True, "hazardous": False},
            {"material": "Other metals (Enphase microinverter)", "percentage": 1.5, "recyclable": True, "hazardous": False},
        ],
        "hazardous_substances": [
            {
                "name": "Lead in junction box solder (RoHS exempt for PV)",
                "cas_number": "7439-92-1",
                "concentration_pct": 0.02,
                "regulation": "RoHS 2011/65/EU (Annex III, category 11 exempt)",
                "safety_instructions": "Handle junction box with gloves. Do not crush or incinerate junction box. Route to certified WEEE/PV recycler.",
            },
        ],
        "disassembly_instructions": (
            "1. Isolate DC supply and disconnect Enphase IQ8A microinverter. "
            "2. Remove mounting clamp bolts from aluminium frame. "
            "3. Disengage MC4 connectors (quarter-turn + press). "
            "4. Detach junction box (Torx T10 × 2). "
            "5. Transport complete module to certified PV recycler (PV Cycle collection point). "
            "Note: Microinverter must be separately removed and processed as WEEE electronics."
        ),
        "recycling_instructions": (
            "PV Cycle certified process (target ≥80% mass recovery): "
            "(1) Aluminium frame: direct remove and remelt. "
            "(2) Junction box copper: to scrap; PPO plastic to WEEE stream. "
            "(3) Microinverter (Enphase IQ8A): separate WEEE processing. "
            "(4) Glass-silicon laminate: thermal delamination at 500°C. "
            "PV Cycle partner recyclers: Reiling (DE), Veolia (FR), 3S PV recycling (CH)."
        ),
        "disposal_instructions": (
            "Covered by WEEE Directive (PV panels – Category 4). "
            "Return via PV Cycle take-back (pvccycle.org) or Maxeon installer return programme. "
            "EPR registration: EPR-EU-PVCYCLE-MAXEON-2024-001. "
            "Do not dispose in general household waste."
        ),
        "recyclability_pct": 92.0,
        "disassembly_time_estimate_min": 25,
        "component_separation_difficulty": "Low for frame and junction box; High for cell laminate (thermal delamination required)",
        "end_of_life_collection_point": "PV Cycle collection points EU-wide; Maxeon installer return; municipal WEEE",
        "weee_category": "WEEE Category 4 – Consumer Equipment (photovoltaic panels)",
        "weee_treatment_instructions": "Remove aluminium frame before bulk treatment. Thermal delamination of laminate required.",
        "urban_mining_priority": False,
        "epr_fee_eur": 2.10,
        "last_updated": "2026-05-15",
        # INTENTIONAL GAPS (realistic – second unit not yet fully profiled in CircThread DPP Hub):
        # - silver_content_g: not yet measured (pending lab analysis of this unit's cell batch)
        # - recycling_route: not provided
        # - critical_material_recovery_instructions: not provided
        # - residual_value_eur: not provided (pending market valuation)
        # - remanufacturing_eligibility: not provided
        # - scrap_metal_value_eur: not provided
        # - end_of_life_value_eur: not provided
    },
}


# ───────────────────── EXTENDED END-OF-LIFE DATA (dataset v2) ─────────────────────
# Material, substance, and battery information that recyclers requested for the partner
# products, plus complete end-of-life records for the two products that are identified by
# their EPREL registration number. Merged into PRODUCTS below.

_NO_BATTERY = (
    "Not applicable – the appliance contains no batteries or accumulators "
    "(no removal step required under Regulation (EU) 2023/1542, Art. 11)."
)

EXTENDED_PRODUCTS = {
    "WM-GORENJE-001": {
        "battery_removal_instructions": _NO_BATTERY,
    },
    "WM-BOSCH-001": {
        "polymer_types_in_casing": "PP (tub, detergent drawer), ABS (control panel), PA66-GF30 (door hinge), POM (drum bearing housing seal carrier)",
        "substance_of_concern_list": [
            "Brominated flame retardants in PCB plastics (<0.1%)",
            "Lead in PCB solder (RoHS exemption 7(c)-I, <0.1%)",
        ],
        "battery_removal_instructions": _NO_BATTERY,
    },
    "DW-SIEMENS-001": {
        "polymer_types_in_casing": "PP-T20 (base tub, spray arms), ABS (control panel), PA6-GF (door hinge mechanism), EPDM (door seal)",
        "substance_of_concern_list": [
            "Lead in PCB solder (RoHS exemption 7(c)-I, <0.1%)",
            "Zeolite drying granulate – non-hazardous, separate before shredding",
        ],
        "battery_removal_instructions": _NO_BATTERY,
    },
    "BL-VAILLANT-001": {
        "polymer_types_in_casing": "PP (front casing, condensate trap), PA66-GF30 (hydraulic block), PPS (fan housing), EPDM (seals)",
        "substance_of_concern_list": [
            "Ceramic fibre insulation in combustion chamber (handle with dust mask, RCF)",
            "Lead in brass fittings (CuZn39Pb3, <3.5% Pb, REACH SVHC)",
        ],
        "critical_raw_materials": [
            {"material": "Copper (Cu)", "mass_kg": 4.8, "application": "Primary heat exchanger tubing, pump windings"},
            {"material": "Aluminium-silicon alloy", "mass_kg": 6.2, "application": "Secondary condensing heat exchanger"},
            {"material": "Nickel (Ni)", "mass_g": 120, "application": "Stainless steel burner and fittings"},
        ],
        "refrigerant_type": "None – gas condensing boiler without refrigerant circuit (no F-gas recovery required)",
        "reuse_potential_score": 6.1,
    },
    "LB-LG-001": {
        "polymer_types_in_casing": "PC/ABS (outer enclosure), PP (module trays), PBT-GF30 (busbar holders), silicone (thermal pads)",
        "substance_of_concern_list": [
            "LiPF6 electrolyte salt – releases HF on contact with moisture",
            "Organic carbonate solvents (EC/DMC) – flammable",
            "Nickel and cobalt compounds in NMC cathode (CLP Carc. 1B)",
        ],
        "rare_earth_elements": "None – NMC chemistry and passive cooling contain no rare-earth elements",
    },
    "SP-SUNPOWER-001": {
        "polymer_types_in_casing": "EVA (encapsulant), PET/PVF (backsheet), PPO (junction box), silicone (frame sealant)",
        "substance_of_concern_list": [
            "Lead in cell interconnection solder (<0.1%)",
            "Fluoropolymer (PVF) backsheet – releases HF if incinerated",
        ],
        "rare_earth_elements": "None – IBC silicon cells contain no rare-earth elements",
    },

    # Products identified by EPREL registration number
    "2219971": {
        "product_id": "2219971",
        "product_type": "washing_machine",
        "manufacturer": "Bosch",
        "model": "WAN28283ES",
        "materials": [
            {"material": "Steel (cabinet, drum, frame)", "percentage": 45, "recyclable": True, "hazardous": False},
            {"material": "Plastic (PP tub, ABS panel)", "percentage": 22, "recyclable": True, "hazardous": False},
            {"material": "Concrete (counterweights)", "percentage": 18, "recyclable": False, "hazardous": False},
            {"material": "Copper (motor windings, wiring)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Glass (door porthole)", "percentage": 4, "recyclable": True, "hazardous": False},
            {"material": "Rubber – EPDM (door seal, hoses)", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Printed circuit boards", "percentage": 2, "recyclable": False, "hazardous": True},
            {"material": "Aluminium (pulley, brackets)", "percentage": 1, "recyclable": True, "hazardous": False},
        ],
        "hazardous_substances": [
            {
                "name": "Brominated flame retardants in PCB plastics",
                "cas_number": None,
                "concentration_pct": 0.03,
                "regulation": "REACH SVHC screening",
                "safety_instructions": "Remove control and motor boards before shredding; route to certified WEEE processor.",
            },
            {
                "name": "Lead in PCB solder",
                "cas_number": "7439-92-1",
                "concentration_pct": 0.01,
                "regulation": "RoHS exemption 7(c)-I",
                "safety_instructions": "Treat PCB fraction separately (precious-metal smelter).",
            },
        ],
        "polymer_types_in_casing": "PP-T20 (tub), ABS (control panel), PA6-GF (door hinge), POM (detergent drawer guides)",
        "substance_of_concern_list": [
            "Brominated flame retardants in PCB plastics (<0.1%)",
            "Lead in PCB solder (RoHS exemption 7(c)-I, <0.1%)",
        ],
        "critical_raw_materials": [
            {"material": "Neodymium (Nd)", "mass_g": 160, "application": "EcoSilence Drive BLDC motor magnets"},
            {"material": "Copper (Cu)", "mass_kg": 3.1, "application": "Motor windings, wiring harness"},
        ],
        "disassembly_instructions": (
            "1. Disconnect power and water supply. "
            "2. Remove worktop (2 Torx T20 screws at rear). "
            "3. Remove plinth panel and drain pump filter cover. "
            "4. Remove detergent drawer and control panel (4 Torx T20). "
            "5. Release door seal clamp ring and remove front panel (6 Torx T20). "
            "6. Unbolt upper and front counterweights (13 mm). "
            "7. Disconnect motor connector, remove motor (2 bolts, 13 mm). "
            "8. Remove shock absorbers and lift out tub assembly."
        ),
        "disassembly_time_estimate_min": 40,
        "component_separation_difficulty": "Medium – standard Torx tools, tub assembly requires 2 persons",
        "recycling_instructions": (
            "(1) Steel cabinet and drum → shredder with magnetic separation. "
            "(2) Motor → hand-strip copper windings, recover NdFeB magnets (~160 g). "
            "(3) PCB → certified WEEE processor for precious-metal recovery. "
            "(4) PP tub → sortable thermoplastic stream after removing bearings. "
            "(5) Concrete counterweights → mineral construction waste."
        ),
        "disposal_instructions": (
            "Do not dispose in municipal waste. Free take-back by the retailer on delivery of a new appliance "
            "(Spain: RD 110/2015), municipal 'punto limpio' collection points, or Bosch take-back partners."
        ),
        "recyclability_pct": 79.0,
        "residual_value_eur": 60.0,
        "end_of_life_collection_point": "Retailer take-back (RD 110/2015), municipal punto limpio, Bosch take-back partners",
        "remanufacturing_eligibility": True,
        "weee_category": "WEEE Category 4 – Large equipment (Directive 2012/19/EU, Annex III)",
        "weee_treatment_instructions": (
            "Pre-treat per Annex VII WEEE Directive 2012/19/EU: remove PCBs > 10 cm², capacitors, and external "
            "cables before shredding. Separate concrete counterweights before metal shredding."
        ),
        "critical_material_recovery_instructions": (
            "Remove the BLDC motor before shredding; separate NdFeB rotor magnets (~160 g) for rare-earth recycling "
            "and hand-strip copper windings (3.1 kg)."
        ),
        "battery_removal_instructions": _NO_BATTERY,
        "reuse_potential_score": 7.0,
        "dismantling_information_url": "https://circthread.eu/dpp/2219971/dismantling",
        "urban_mining_priority": False,
        "scrap_metal_value_eur": 20.0,
        "end_of_life_value_eur": 38.0,
        "epr_fee_eur": 4.0,
        "recycling_route": "WEEE Category 4 – Spanish SCRAP network (Ecolec / Recyclia)",
        "last_updated": "2026-05-15",
    },
    "2613426": {
        "product_id": "2613426",
        "product_type": "dishwasher",
        "manufacturer": "Siemens",
        "model": "SN43HW04ME",
        "materials": [
            {"material": "Stainless steel (inner tub, door inner)", "percentage": 48, "recyclable": True, "hazardous": False},
            {"material": "Plastic (PP base, ABS control panel)", "percentage": 26, "recyclable": True, "hazardous": False},
            {"material": "Bitumen sound insulation", "percentage": 9, "recyclable": False, "hazardous": False},
            {"material": "Copper (pump and motor windings, wiring)", "percentage": 5, "recyclable": True, "hazardous": False},
            {"material": "Galvanised steel (frame, hinges)", "percentage": 7, "recyclable": True, "hazardous": False},
            {"material": "Rubber – EPDM (door seal, hoses)", "percentage": 3, "recyclable": False, "hazardous": False},
            {"material": "Printed circuit boards", "percentage": 2, "recyclable": False, "hazardous": True},
        ],
        "hazardous_substances": [
            {
                "name": "Lead in PCB solder",
                "cas_number": "7439-92-1",
                "concentration_pct": 0.01,
                "regulation": "RoHS exemption 7(c)-I",
                "safety_instructions": "Remove PCB before shredding; route to certified WEEE processor.",
            },
        ],
        "polymer_types_in_casing": "PP-T20 (base tub, spray arms), ABS (control panel), PA6-GF (hinge), EPDM (door seal)",
        "substance_of_concern_list": [
            "Lead in PCB solder (RoHS exemption 7(c)-I, <0.1%)",
        ],
        "critical_raw_materials": [
            {"material": "Copper (Cu)", "mass_kg": 2.2, "application": "Circulation pump, drain pump, wiring"},
        ],
        "disassembly_instructions": (
            "1. Disconnect power and water supply, pull the appliance out of the niche. "
            "2. Remove kick plate and side insulation mats. "
            "3. Remove control panel fascia (Torx T20) and control module. "
            "4. Remove circulation pump with integrated heater from the sump (bayonet lock). "
            "5. Remove drain pump and water softener unit. "
            "6. Separate bitumen mats from the stainless steel tub before shredding."
        ),
        "disassembly_time_estimate_min": 30,
        "component_separation_difficulty": "Low to medium – bayonet-mounted pumps, bitumen mats are glued",
        "recycling_instructions": (
            "(1) Stainless steel tub and door → high-grade stainless scrap. "
            "(2) Pumps → hand-strip copper windings. "
            "(3) PCB → certified WEEE processor. "
            "(4) PP base and spray arms → thermoplastic stream. "
            "(5) Bitumen mats → energy recovery."
        ),
        "disposal_instructions": (
            "Do not dispose in municipal waste. Free retailer take-back when buying a new appliance (ElektroG, Germany), "
            "municipal recycling centres, or Siemens take-back partners."
        ),
        "recyclability_pct": 76.0,
        "residual_value_eur": 75.0,
        "end_of_life_collection_point": "Retailer take-back (ElektroG §17), municipal recycling centres (Wertstoffhof)",
        "remanufacturing_eligibility": True,
        "weee_category": "WEEE Category 4 – Large equipment (Directive 2012/19/EU, Annex III)",
        "weee_treatment_instructions": (
            "Pre-treat per Annex VII WEEE Directive 2012/19/EU: remove PCB and external cables; separate "
            "bitumen insulation before metal shredding."
        ),
        "critical_material_recovery_instructions": "Hand-strip copper windings of circulation and drain pump (2.2 kg Cu) before shredding.",
        "battery_removal_instructions": _NO_BATTERY,
        "reuse_potential_score": 7.4,
        "dismantling_information_url": "https://circthread.eu/dpp/2613426/dismantling",
        "urban_mining_priority": False,
        "scrap_metal_value_eur": 28.0,
        "end_of_life_value_eur": 35.0,
        "epr_fee_eur": 3.5,
        "recycling_route": "WEEE Category 4 – stiftung ear collection group 1 (Germany)",
        "last_updated": "2026-05-15",
    },
}

for _product_id, _extension in EXTENDED_PRODUCTS.items():
    PRODUCTS.setdefault(_product_id, {}).update(_extension)


def get_product(product_id: str) -> dict | None:
    return PRODUCTS.get(product_id)


def get_all_products() -> list[dict]:
    return list(PRODUCTS.values())
