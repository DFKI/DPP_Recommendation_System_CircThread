"""Knowledge Graph seed data and ontology for the DPP Recommendation Engine.

Defines the complete knowledge graph structure with:
- Product types, Roles, Events
- Data fields with categories
- Role-Event-specific relevance mappings (priority weights)
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from app.neo4j_client import Neo4jClient
from app.sssom import load_sssom_mapping_set

logger = logging.getLogger(__name__)


# ─── Data Field Definitions ────────────────────────────────────────────────────
# Each field: (field_name, display_name, category, description)

DATA_FIELDS = [
    # ── Identification ──────────────────────────────────────────────────────────
    ("product_id", "Product ID", "identification", "Unique product identifier"),
    ("product_type", "Product Type", "identification", "Category of the product"),
    ("manufacturer", "Manufacturer", "identification", "Producer of the product"),
    ("model", "Model Name", "identification", "Commercial model designation"),
    ("serial_number", "Serial Number", "identification", "Unique serial number"),
    ("manufacturing_date", "Manufacturing Date", "identification", "Date of production"),
    ("manufacturing_location", "Manufacturing Location", "identification", "Place of production"),
    ("brand_name", "Brand Name", "identification", "Commercial brand under which the product is sold"),
    ("product_variant", "Product Variant", "identification", "Specific variant or configuration code within the model line"),
    ("ean_barcode", "EAN Barcode", "identification", "European Article Number barcode for retail identification"),
    ("batch_number", "Batch Number", "identification", "Production batch identifier for quality traceability"),
    ("country_of_origin", "Country of Origin", "identification", "ISO 3166-1 alpha-2 country code of the primary production site"),
    ("customs_tariff_number", "Customs Tariff Number", "identification", "HS/CN customs classification number for import/export purposes"),
    ("digital_twin_reference", "Digital Twin Reference", "identification", "URI or ID linking to the product's digital twin instance"),
    ("product_registration_id", "Product Registration ID", "identification", "Manufacturer or regulatory product registration identifier"),

    # ── Technical Specifications ────────────────────────────────────────────────
    ("specifications", "Technical Specifications", "technical", "Full technical specification data"),
    ("weight_kg", "Weight", "technical", "Product weight in kilograms"),
    ("dimensions", "Dimensions", "technical", "Physical dimensions of the product"),
    ("rated_power_w", "Rated Power", "technical", "Nominal electrical power consumption in watts"),
    ("standby_power_w", "Standby Power", "technical", "Power draw in standby mode in watts"),
    ("operating_voltage_v", "Operating Voltage", "technical", "Nominal operating voltage in volts"),
    ("ip_rating", "IP Rating", "technical", "Ingress Protection rating for dust and water resistance"),
    ("noise_level_db", "Noise Level", "technical", "Acoustic noise emission during operation in decibels"),
    ("colour", "Colour", "technical", "Product colour designation"),
    ("installation_type", "Installation Type", "technical", "How the product is installed (freestanding, built-in, wall-mounted)"),
    ("connectivity_protocol", "Connectivity Protocol", "technical", "Supported smart home communication protocol"),
    ("software_version", "Software Version", "technical", "Installed firmware or software version at time of manufacture"),
    ("spare_parts_availability_years", "Spare Parts Availability", "technical", "Years the manufacturer guarantees availability of spare parts"),
    ("spare_parts_supplier", "Spare Parts Supplier", "technical", "Name or identifier of the authorised spare parts distributor"),
    ("repair_difficulty_score", "Repair Difficulty Score", "technical", "Standardised score indicating difficulty of self-repair (1=easy, 10=very hard)"),

    # ── Components ──────────────────────────────────────────────────────────────
    ("components", "Components", "components", "List of product components with details"),

    # ── Materials ───────────────────────────────────────────────────────────────
    ("materials", "Material Composition", "materials", "Breakdown of materials used"),
    ("polymer_types_in_casing", "Polymer Types in Casing", "materials", "Identification of polymer types used in outer casing for sorting"),
    ("recycled_content_pct", "Recycled Content Percentage", "materials", "Percentage by mass of recycled material in the product"),
    ("bio_based_content_pct", "Bio-Based Content Percentage", "materials", "Percentage by mass of bio-based material in the product"),
    ("critical_raw_materials", "Critical Raw Materials", "materials", "List of EU critical raw materials present and their mass fractions"),
    ("conflict_minerals_declaration", "Conflict Minerals Declaration", "materials", "Declaration of compliance regarding conflict minerals per OECD guidance"),
    ("substance_of_concern_list", "Substances of Concern", "materials", "List of substances of very high concern (SVHCs) per REACH regulation"),
    ("packaging_material", "Packaging Material", "materials", "Material composition of the product packaging"),
    ("packaging_recyclability", "Packaging Recyclability", "materials", "Recyclability classification of the product packaging"),
    ("rare_earth_elements", "Rare Earth Elements", "materials", "Rare earth elements present and their mass fractions"),
    ("halogen_free", "Halogen Free", "materials", "Indicates whether the product is free of halogenated flame retardants"),

    # ── Sustainability ──────────────────────────────────────────────────────────
    ("energy_label", "Energy Label", "sustainability", "EU Energy efficiency rating"),
    ("repairability_score", "Repairability Score", "sustainability", "Repairability index (0-10)"),
    ("recyclability_pct", "Recyclability Rate", "sustainability", "Percentage of recyclable materials"),
    ("carbon_footprint_kg_co2", "Carbon Footprint", "sustainability", "Total CO2 emissions in production"),
    ("expected_lifetime_years", "Expected Lifetime", "sustainability", "Expected product lifespan in years"),
    ("energy_consumption_kwh_per_year", "Annual Energy Consumption", "sustainability", "Estimated annual energy consumption in kilowatt-hours based on standard use profile"),
    ("energy_consumption_kwh_per_cycle", "Energy Consumption per Cycle", "sustainability", "Energy consumed per standard programme cycle in kilowatt-hours"),
    ("scope1_co2_manufacturing_kg", "Scope 1 CO2 Manufacturing", "sustainability", "Direct greenhouse gas emissions from manufacturing processes in kg CO2e"),
    ("scope2_co2_manufacturing_kg", "Scope 2 CO2 Manufacturing", "sustainability", "Indirect emissions from purchased energy at manufacturing site in kg CO2e"),
    ("scope3_co2_upstream_kg", "Scope 3 CO2 Upstream", "sustainability", "Upstream supply chain embodied emissions in kg CO2e"),
    ("water_stress_index_manufacturing", "Water Stress Index of Manufacturing Site", "sustainability", "Water stress index score of the manufacturing location per WRI Aqueduct"),
    ("product_environmental_footprint", "Product Environmental Footprint", "sustainability", "PEF category result per EU Product Environmental Footprint methodology"),
    ("ecodesign_class", "Ecodesign Class", "sustainability", "Ecodesign regulation compliance class or tier"),
    ("noise_class", "Noise Class", "sustainability", "Acoustic noise class per EU energy labelling regulation"),
    ("eco_mode_available", "Eco Mode Available", "sustainability", "Indicates whether an eco-optimised operating mode is available"),
    ("co2_saved_vs_average_kg", "CO2 Saved vs. Average Product", "sustainability", "Estimated CO2 saving compared to average market product over lifetime"),
    ("eu_ecolabel", "EU Ecolabel", "sustainability", "Indicates whether the product holds the EU Ecolabel certification"),
    ("epd_reference", "Environmental Product Declaration", "sustainability", "Reference identifier for the product's Environmental Product Declaration (EPD)"),
    ("lca_reference", "Life Cycle Assessment Reference", "sustainability", "Reference to full Life Cycle Assessment study for this product"),
    ("take_back_scheme_participation", "Take-Back Scheme Participation", "sustainability", "Indicates participation in a manufacturer or retailer product take-back programme"),

    # ── Safety ──────────────────────────────────────────────────────────────────
    ("hazardous_substances", "Hazardous Substances", "safety", "List of hazardous materials and concentrations"),
    ("flammability_class", "Flammability Class", "safety", "Material flammability classification per UL 94 or equivalent standard"),
    ("thermal_runaway_protection", "Thermal Runaway Protection", "safety", "Describes built-in mechanisms preventing or containing thermal runaway events"),
    ("overheat_protection", "Overheat Protection", "safety", "Indicates presence of automatic overheat cutoff protection"),
    ("short_circuit_protection", "Short Circuit Protection", "safety", "Indicates presence of short circuit protection mechanism"),
    ("transportation_class", "Transportation Class", "safety", "Dangerous goods transportation classification, e.g. UN 3481 Class 9"),
    ("safety_data_sheet_reference", "Safety Data Sheet Reference", "safety", "Reference URL or document ID for the product Safety Data Sheet"),
    ("child_safety_compliance", "Child Safety Compliance", "safety", "Compliance with relevant child safety standards"),
    ("fire_safety_standard", "Fire Safety Standard", "safety", "Applicable fire safety standard and compliance status"),

    # ── Regulatory Compliance ───────────────────────────────────────────────────
    ("certifications", "Certifications", "compliance", "Product certifications obtained"),
    ("compliance", "Regulatory Compliance", "compliance", "Applicable regulations and directives"),
    ("rohs_compliance", "RoHS Compliance", "compliance", "Compliance with EU RoHS Directive on hazardous substances in electronics"),
    ("weee_category", "WEEE Category", "compliance", "WEEE Directive product category number for waste classification"),
    ("reach_compliance", "REACH Compliance", "compliance", "Compliance status with EU REACH chemical regulation"),
    ("ecodesign_regulation", "Ecodesign Regulation Reference", "compliance", "Applicable EU Ecodesign implementing regulation number and version"),
    ("eu_battery_regulation_compliance", "EU Battery Regulation Compliance", "compliance", "Compliance status with EU Battery Regulation 2023/1542"),
    ("extended_producer_responsibility_id", "Extended Producer Responsibility ID", "compliance", "Producer registration number under applicable EPR scheme"),
    ("type_approval_number", "Type Approval Number", "compliance", "Official type approval or product registration number"),
    ("gas_appliance_regulation", "Gas Appliance Regulation", "compliance", "Compliance with EU Gas Appliance Regulation 2016/426"),
    ("low_voltage_directive", "Low Voltage Directive", "compliance", "Compliance with EU Low Voltage Directive 2014/35/EU"),
    ("electromagnetic_compatibility", "EMC Compliance", "compliance", "Compliance with EU Electromagnetic Compatibility Directive 2014/30/EU"),
    ("construction_products_regulation", "Construction Products Regulation", "compliance", "Compliance reference for construction-related products per CPR"),
    ("f_gas_regulation", "F-Gas Regulation", "compliance", "Compliance status with EU F-Gas Regulation where refrigerants are used"),

    # ── End of Life ─────────────────────────────────────────────────────────────
    ("disassembly_instructions", "Disassembly Instructions", "end_of_life", "Step-by-step disassembly guide"),
    ("recycling_instructions", "Recycling Instructions", "end_of_life", "How to recycle the product"),
    ("disposal_instructions", "Disposal Instructions", "end_of_life", "Safe disposal guidelines"),
    ("disassembly_time_estimate_min", "Disassembly Time Estimate", "end_of_life", "Estimated time required for full product disassembly in minutes"),
    ("component_separation_difficulty", "Component Separation Difficulty", "end_of_life", "Qualitative rating of difficulty separating components for recycling"),
    ("end_of_life_collection_point", "End-of-Life Collection Point", "end_of_life", "Address or URL of the nearest authorised product collection point"),
    ("remanufacturing_eligibility", "Remanufacturing Eligibility", "end_of_life", "Indicates whether the product is eligible for certified remanufacturing"),
    ("refurbishment_grade", "Refurbishment Grade", "end_of_life", "Standardised grade indicating level of refurbishment applied: A, B, or C"),
    ("critical_material_recovery_instructions", "Critical Material Recovery Instructions", "end_of_life", "Specific instructions for recovering critical or valuable materials"),
    ("battery_removal_instructions", "Battery Removal Instructions", "end_of_life", "Step-by-step instructions for safe battery removal before disposal"),
    ("refrigerant_type", "Refrigerant Type", "end_of_life", "Type of refrigerant present and quantity, required for safe disposal"),
    ("dismantling_information_url", "Dismantling Information URL", "end_of_life", "URL to professional dismantling information for treatment facilities"),
    ("weee_treatment_instructions", "WEEE Treatment Instructions", "end_of_life", "Instructions for WEEE-compliant treatment of the product"),

    # ── Economic ────────────────────────────────────────────────────────────────
    ("purchase_price_eur", "Purchase Price", "economic", "Original purchase price in EUR"),
    ("residual_value_eur", "Residual Value", "economic", "Estimated residual/resale value"),
    ("warranty_years", "Warranty Period", "economic", "Warranty duration in years"),
    ("leasing_eligible", "Leasing Eligible", "economic", "Indicates whether the product is available under a leasing scheme"),
    ("product_as_a_service_eligible", "Product-as-a-Service Eligible", "economic", "Indicates whether the product is available under a product-as-a-service model"),
    ("insurance_information", "Insurance Information", "economic", "Reference to applicable product insurance policy or scheme"),
    ("repair_cost_estimate_eur", "Repair Cost Estimate", "economic", "Average estimated cost for common repair interventions in EUR"),
    ("operating_cost_annual_eur", "Annual Operating Cost", "economic", "Estimated annual operating cost including energy and water in EUR"),
    ("spare_parts_cost_index", "Spare Parts Cost Index", "economic", "Relative index indicating cost level of spare parts availability"),
    ("total_cost_of_ownership_eur", "Total Cost of Ownership", "economic", "Estimated total cost over expected lifetime including purchase and operating costs"),
    ("subsidy_eligibility", "Subsidy / Grant Eligibility", "economic", "Information on applicable government subsidies or rebates for this product"),
    ("carbon_credit_value_eur", "Carbon Credit Value", "economic", "Estimated monetary value of carbon credits associated with product use"),
    ("scrap_metal_value_eur", "Scrap Metal Value", "economic", "Estimated value of recoverable metal at end-of-life in EUR"),

    # ── Maintenance & Repair ────────────────────────────────────────────────────
    ("maintenance_schedule", "Maintenance Schedule", "maintenance", "Scheduled maintenance tasks"),
    ("repair_history", "Repair History", "maintenance", "Record of past repairs"),
    ("last_service_date", "Last Service Date", "maintenance", "Date of the most recent professional service or inspection"),
    ("service_provider_name", "Service Provider Name", "maintenance", "Name or identifier of the entity that performed the last service"),
    ("next_service_due_date", "Next Service Due Date", "maintenance", "Scheduled date for the next required service or inspection"),
    ("filter_replacement_interval_months", "Filter Replacement Interval", "maintenance", "Recommended filter replacement interval in months"),
    ("descaling_interval_months", "Descaling Interval", "maintenance", "Recommended descaling interval in months for water-carrying components"),
    ("lubrication_schedule", "Lubrication Schedule", "maintenance", "Schedule and specifications for required lubrication tasks"),
    ("fault_code_history", "Fault Code History", "maintenance", "Log of diagnostic fault codes recorded by the product"),
    ("remote_diagnostic_capable", "Remote Diagnostic Capable", "maintenance", "Indicates whether the product supports remote diagnostic access by service engineers"),

    # ── Metadata ────────────────────────────────────────────────────────────────
    ("data_sources", "Data Sources", "metadata", "Origins of the product data"),
    ("last_updated", "Last Updated", "metadata", "Date of last data update"),
    ("data_quality_score", "Data Quality Score", "metadata", "Composite score reflecting completeness and reliability of the DPP data"),
    ("data_custodian", "Data Custodian", "metadata", "Organisation responsible for maintaining and updating the DPP data"),
    ("dpp_schema_version", "DPP Schema Version", "metadata", "Version of the DPP data schema used for this record"),
    ("verification_status", "Verification Status", "metadata", "Status of third-party data verification: unverified, self-declared, verified"),
    ("publication_date", "Publication Date", "metadata", "Date on which this DPP record was first published"),

    # ── Water Consumption ───────────────────────────────────────────────────────
    ("water_consumption_l_per_cycle", "Water Consumption per Cycle", "water", "Volume of water consumed per wash cycle in litres"),
    ("water_consumption_annual_l", "Annual Water Consumption", "water", "Estimated annual water consumption in litres based on standard use"),
    ("water_hardness_compatibility", "Water Hardness Compatibility", "water", "Compatible water hardness range in degrees dH"),
    ("hot_water_connection", "Hot Water Connection", "water", "Indicates whether the appliance supports direct hot water supply connection"),
    ("rinse_aid_consumption_ml_per_cycle", "Rinse Aid Consumption", "water", "Volume of rinse aid consumed per dishwasher cycle in millilitres"),
    ("salt_consumption_g_per_cycle", "Salt Consumption per Cycle", "water", "Mass of dishwasher salt consumed per cycle in grams"),
    ("hose_material", "Hose Material", "water", "Material composition of water inlet and outlet hoses"),
    ("hose_length_m", "Hose Length", "water", "Length of supply and drain hoses in metres"),
    ("aquastop_feature", "AquaStop / Leak Protection", "water", "Indicates presence of automatic water leak protection system"),
    ("self_cleaning_filter", "Self-Cleaning Filter", "water", "Indicates whether the appliance has an automatic self-cleaning filter"),

    # ── Performance Metrics ─────────────────────────────────────────────────────
    ("drum_volume_l", "Drum Volume", "performance", "Internal drum volume in litres"),
    ("drum_material", "Drum Material", "performance", "Material of the wash drum, e.g. stainless steel"),
    ("load_capacity_kg", "Load Capacity", "performance", "Maximum rated load in kilograms per cycle"),
    ("spin_speed_rpm", "Maximum Spin Speed", "performance", "Maximum drum spin speed in revolutions per minute"),
    ("wash_temperature_max_c", "Maximum Wash Temperature", "performance", "Highest selectable wash temperature in degrees Celsius"),
    ("motor_type", "Motor Type", "performance", "Motor technology used, e.g. brushless inverter, universal"),
    ("number_of_programmes", "Number of Programmes", "performance", "Count of distinct washing or cleaning programmes"),
    ("child_lock", "Child Lock", "performance", "Indicates whether a child safety lock feature is present"),
    ("delay_start", "Delay Start Function", "performance", "Indicates whether the appliance supports delayed programme start"),
    ("short_cycle_duration_min", "Short Cycle Duration", "performance", "Duration of the shortest available wash programme in minutes"),
    ("vibration_emission_db", "Vibration Emission", "performance", "Structure-borne vibration level during spin in decibels"),
    ("basket_capacity_place_settings", "Basket Capacity", "performance", "Number of place settings that fit in a dishwasher basket"),

    # ── Connectivity & Smart Features ───────────────────────────────────────────
    ("wifi_enabled", "Wi-Fi Enabled", "connectivity", "Indicates whether the appliance has built-in Wi-Fi connectivity"),
    ("app_control_supported", "App Control Supported", "connectivity", "Indicates whether the appliance can be controlled via a smartphone application"),
    ("voice_assistant_compatible", "Voice Assistant Compatible", "connectivity", "Indicates compatibility with voice assistant platforms"),
    ("smart_grid_ready", "Smart Grid Ready", "connectivity", "Indicates whether the appliance can respond to smart grid demand signals"),
    ("home_automation_protocol", "Home Automation Protocol", "connectivity", "Supported smart home protocol, e.g. Matter, Zigbee, Z-Wave, KNX"),
    ("ota_update_supported", "OTA Update Supported", "connectivity", "Indicates whether the appliance supports over-the-air firmware updates"),
    ("energy_monitoring_capable", "Energy Monitoring Capable", "connectivity", "Indicates whether the appliance reports real-time energy consumption data"),
    ("demand_response_capable", "Demand Response Capable", "connectivity", "Indicates whether the appliance can participate in utility demand-response programmes"),

    # ── Thermal & Combustion (boiler) ───────────────────────────────────────────
    ("boiler_type", "Boiler Type", "thermal", "Type of boiler: combi, system, regular, or heat-only"),
    ("fuel_type", "Fuel Type", "thermal", "Primary fuel: natural gas, LPG, oil, hydrogen-blend, biomass"),
    ("burner_type", "Burner Type", "thermal", "Burner technology: atmospheric, forced-draught, premix, modulating"),
    ("heat_exchanger_material", "Heat Exchanger Material", "thermal", "Material of the primary heat exchanger, e.g. stainless steel, aluminium alloy"),
    ("flue_gas_temperature_c", "Flue Gas Temperature", "thermal", "Temperature of exhaust flue gas at nominal output in degrees Celsius"),
    ("venting_type", "Venting Type", "thermal", "Exhaust venting configuration: balanced flue, open flue, condensing"),
    ("nox_emission_class", "NOx Emission Class", "thermal", "Nitrogen oxide emission classification per EN 15502"),
    ("seasonal_efficiency_pct", "Seasonal Space Heating Efficiency", "thermal", "Annual seasonal energy efficiency as a percentage per ErP directive"),
    ("efficiency_at_partial_load_pct", "Efficiency at Partial Load", "thermal", "Thermal efficiency at 30% partial load condition in percent"),
    ("max_output_power_kw", "Maximum Output Power", "thermal", "Maximum rated heat output in kilowatts"),
    ("min_output_power_kw", "Minimum Output Power", "thermal", "Minimum modulated heat output in kilowatts"),
    ("hot_water_flow_rate_l_per_min", "Hot Water Flow Rate", "thermal", "Domestic hot water output flow rate in litres per minute"),
    ("expansion_vessel_size_l", "Expansion Vessel Size", "thermal", "Volume of the built-in expansion vessel in litres"),
    ("frost_protection", "Frost Protection", "thermal", "Indicates whether built-in frost protection is present"),
    ("ignition_type", "Ignition Type", "thermal", "Ignition mechanism: electronic spark, hot surface, pilot flame"),
    ("gas_valve_manufacturer", "Gas Valve Manufacturer", "thermal", "Manufacturer of the gas valve component"),
    ("condensate_pipe_material", "Condensate Pipe Material", "thermal", "Material of the condensate drain pipe, e.g. ABS, PVC-U"),
    ("service_interval_months", "Service Interval", "thermal", "Recommended service interval in months"),
    ("pressure_relief_valve_spec", "Pressure Relief Valve Spec", "thermal", "Specification and set pressure of the safety pressure relief valve"),

    # ── Photovoltaic Properties (solar_panel) ───────────────────────────────────
    ("cell_technology", "Cell Technology", "photovoltaic", "PV cell technology: monocrystalline, polycrystalline, thin-film, HJT, TOPCon"),
    ("cell_efficiency_pct", "Cell Efficiency", "photovoltaic", "Individual cell conversion efficiency under STC in percent"),
    ("module_efficiency_pct", "Module Efficiency", "photovoltaic", "Full module power conversion efficiency under STC in percent"),
    ("rated_power_watt_peak", "Rated Peak Power", "photovoltaic", "Nominal peak power output in Watt-peak under STC"),
    ("power_tolerance_pct", "Power Tolerance", "photovoltaic", "Permitted deviation from rated power, expressed as ± percentage"),
    ("temperature_coefficient_pmax", "Temperature Coefficient Pmax", "photovoltaic", "Rate of change of peak power per degree Celsius above STC"),
    ("degradation_rate_pct_per_year", "Annual Degradation Rate", "photovoltaic", "Expected annual power output degradation in percent per year"),
    ("bifaciality_factor", "Bifaciality Factor", "photovoltaic", "Ratio of rear-side to front-side power generation for bifacial modules"),
    ("backsheet_material", "Backsheet Material", "photovoltaic", "Material composition of the module backsheet"),
    ("frame_material", "Frame Material", "photovoltaic", "Material of the module frame, typically aluminium alloy grade"),
    ("junction_box_ip_rating", "Junction Box IP Rating", "photovoltaic", "Ingress Protection rating of the junction box"),
    ("bypass_diode_count", "Bypass Diode Count", "photovoltaic", "Number of bypass diodes installed in the junction box"),
    ("fire_classification", "Fire Classification", "photovoltaic", "Module fire safety class per IEC 61730: Class A, B, or C"),
    ("salt_mist_resistance", "Salt Mist Resistance", "photovoltaic", "Indicates certification for salt mist corrosion resistance per IEC 61701"),
    ("ammonia_resistance", "Ammonia Resistance", "photovoltaic", "Indicates certification for ammonia atmosphere resistance per IEC 62716"),
    ("flash_test_result", "Flash Test Result", "photovoltaic", "Actual measured peak power from factory flash test in Watt-peak"),
    ("mounting_system_compatibility", "Mounting System Compatibility", "photovoltaic", "Compatible roof mounting system types and rail specifications"),
    ("inverter_compatibility", "Inverter Compatibility", "photovoltaic", "List of compatible inverter types or specific models"),
    ("open_circuit_voltage_v", "Open Circuit Voltage", "photovoltaic", "Voltage at open circuit conditions under STC in volts"),
    ("short_circuit_current_a", "Short Circuit Current", "photovoltaic", "Current at short circuit conditions under STC in amperes"),
    ("number_of_cells", "Number of Cells", "photovoltaic", "Total number of photovoltaic cells in the module"),

    # ── Electrical Characteristics (lithium_battery) ────────────────────────────
    ("cell_chemistry", "Cell Chemistry", "electrical", "Electrochemical cell chemistry: NMC, LFP, NCA, LTO, sodium-ion"),
    ("nominal_voltage_v", "Nominal Voltage", "electrical", "Nominal pack voltage in volts"),
    ("nominal_capacity_kwh", "Nominal Capacity", "electrical", "Total nominal energy capacity in kilowatt-hours"),
    ("usable_capacity_kwh", "Usable Capacity", "electrical", "Energy capacity available to end-user accounting for depth of discharge limits"),
    ("charge_cycles_rated", "Rated Charge Cycles", "electrical", "Number of full charge-discharge cycles at rated capacity retention"),
    ("depth_of_discharge_pct", "Depth of Discharge Rated", "electrical", "Maximum recommended depth of discharge as a percentage of nominal capacity"),
    ("max_charge_rate_kw", "Maximum Charge Rate", "electrical", "Maximum continuous charging power in kilowatts"),
    ("max_discharge_rate_kw", "Maximum Discharge Rate", "electrical", "Maximum continuous discharging power in kilowatts"),
    ("cell_format", "Cell Format", "electrical", "Physical cell form factor: cylindrical, prismatic, or pouch"),
    ("electrolyte_type", "Electrolyte Type", "electrical", "Type of electrolyte: liquid, gel polymer, solid-state"),
    ("cathode_material", "Cathode Material", "electrical", "Chemical composition of the cathode active material"),
    ("anode_material", "Anode Material", "electrical", "Chemical composition of the anode active material"),
    ("separator_material", "Separator Material", "electrical", "Material of the cell separator membrane"),
    ("thermal_management_type", "Thermal Management Type", "electrical", "Method of thermal management: passive, air-cooled, liquid-cooled, PCM"),
    ("bms_manufacturer", "BMS Manufacturer", "electrical", "Manufacturer of the Battery Management System"),
    ("bms_firmware_version", "BMS Firmware Version", "electrical", "Installed firmware version of the Battery Management System"),
    ("un38_3_test_result", "UN 38.3 Test Result", "electrical", "Result of UN 38.3 transportation safety test"),
    ("iec_62619_compliance", "IEC 62619 Compliance", "electrical", "Compliance status with IEC 62619 safety standard for secondary lithium cells"),

    # ── Battery Health & State (lithium_battery) ────────────────────────────────
    ("state_of_health_pct", "State of Health", "battery_health", "Current capacity as a percentage of original rated capacity"),
    ("state_of_charge_pct", "State of Charge", "battery_health", "Current charge level as a percentage of usable capacity"),
    ("actual_cycle_count", "Actual Cycle Count", "battery_health", "Number of full charge-discharge cycles completed to date"),
    ("end_of_life_capacity_threshold_pct", "End-of-Life Capacity Threshold", "battery_health", "State of Health percentage below which the battery is considered end-of-life"),
    ("second_life_eligibility", "Second Life Eligibility", "battery_health", "Indicates whether the battery is suitable for second-life stationary storage application"),
    ("storage_temperature_range_c", "Storage Temperature Range", "battery_health", "Recommended storage temperature range in degrees Celsius"),
    ("operating_temperature_range_c", "Operating Temperature Range", "battery_health", "Permitted operating temperature range in degrees Celsius"),
    ("calendar_age_years", "Calendar Age", "battery_health", "Number of years since the battery was manufactured"),

    # ── Circular Economy ────────────────────────────────────────────────────────
    ("previous_owner_count", "Previous Owner Count", "circular_economy", "Number of previous owners the product has had"),
    ("product_age_years", "Product Age", "circular_economy", "Current age of the product in years since manufacture"),
    ("remaining_lifetime_pct", "Remaining Lifetime Estimate", "circular_economy", "Estimated remaining useful lifetime as a percentage of expected lifetime"),
    ("reuse_potential_score", "Reuse Potential Score", "circular_economy", "Composite score indicating suitability for direct reuse or resale"),
    ("circular_economy_index", "Circular Economy Index", "circular_economy", "Standardised index measuring overall circularity of the product"),
    ("design_for_repair_compliance", "Design for Repair Compliance", "circular_economy", "Indicates compliance with design-for-repair requirements per Ecodesign"),
    ("modular_design", "Modular Design", "circular_economy", "Indicates whether the product uses a modular design enabling component replacement"),
    ("software_update_end_date", "Software Update End Date", "circular_economy", "Date after which software or firmware updates will no longer be provided"),
    ("interoperability_standard", "Interoperability Standard", "circular_economy", "Standards ensuring product interoperability with other brands and systems"),
    ("rental_return_condition", "Rental Return Condition", "circular_economy", "Condition assessment recorded at return from rental or leasing"),
    ("cradle_to_cradle_certification", "Cradle to Cradle Certification", "circular_economy", "Cradle to Cradle certification level: Basic, Bronze, Silver, Gold, Platinum"),
    ("material_passport_reference", "Material Passport Reference", "circular_economy", "Reference ID linking to a separate detailed material passport document"),
    ("urban_mining_priority", "Urban Mining Priority", "circular_economy", "Indicates whether the product is flagged as high-priority for urban mining"),
    ("functional_unit_defined", "Functional Unit Defined", "circular_economy", "Confirmed definition of the functional unit used in LCA and EPD studies"),
    ("circularity_label", "Circularity Label", "circular_economy", "Third-party circularity label or certification name and level"),

    # ── Supply Chain & Origin ───────────────────────────────────────────────────
    ("supplier_name", "Component Supplier Name", "supply_chain", "Name of the primary component or sub-assembly supplier"),
    ("supplier_country", "Supplier Country", "supply_chain", "Country of origin of the primary component supplier"),
    ("supply_chain_transparency_level", "Supply Chain Transparency Level", "supply_chain", "Level of supply chain traceability disclosed: tier 1, tier 2, full"),
    ("product_origin_country", "Product Origin Country", "supply_chain", "Country where the product's primary manufacturing or assembly takes place"),
    ("manufacturing_site_id", "Manufacturing Site ID", "supply_chain", "Unique identifier of the manufacturing facility"),
    ("deforestation_free_declaration", "Deforestation-Free Declaration", "supply_chain", "Declaration that no deforestation-linked materials are used per EUDR"),
    ("child_labour_free_declaration", "Child Labour Free Declaration", "supply_chain", "Declaration of compliance with ILO child labour standards across supply chain"),
    ("due_diligence_report_reference", "Due Diligence Report Reference", "supply_chain", "Reference to the supply chain due diligence report"),
    ("traceability_system", "Traceability System", "supply_chain", "Name or type of supply chain traceability system used"),
    ("supplier_audit_status", "Supplier Audit Status", "supply_chain", "Status of most recent supplier sustainability audit"),
    ("responsible_sourcing_certification", "Responsible Sourcing Certification", "supply_chain", "Certification held by supplier for responsible material sourcing"),
    ("local_content_pct", "Local Content Percentage", "supply_chain", "Percentage of product value or components sourced from the country of manufacture"),

    # ── Logistics & Transport ───────────────────────────────────────────────────
    ("packaging_weight_kg", "Packaging Weight", "logistics", "Weight of the product packaging in kilograms"),
    ("packaged_dimensions_mm", "Packaged Dimensions", "logistics", "Outer dimensions of the packaged product in millimetres"),
    ("transport_co2_kg", "Transport CO2 Emissions", "logistics", "CO2 emissions from transport of the product from factory to first point of sale"),
    ("storage_conditions", "Storage Conditions", "logistics", "Required storage conditions including temperature and humidity ranges"),
    ("handling_instructions", "Handling Instructions", "logistics", "Special handling requirements for transport and storage"),
    ("fragile_indicator", "Fragile Indicator", "logistics", "Indicates whether the product requires fragile handling"),
    ("return_logistics_scheme", "Return Logistics Scheme", "logistics", "Description of the reverse logistics scheme for return or recall"),
    ("pallet_count", "Pallet Count per Shipment", "logistics", "Standard number of units per pallet for bulk shipments"),

    # ── Service & Ownership ─────────────────────────────────────────────────────
    ("ownership_type", "Ownership Type", "service", "Describes current ownership model: owned, leased, rented, pay-per-use"),
    ("service_contract_type", "Service Contract Type", "service", "Type of active service or maintenance contract"),
    ("service_contract_expiry", "Service Contract Expiry", "service", "Expiry date of the current service or maintenance contract"),
    ("installer_name", "Installer Name", "service", "Name or identifier of the entity that performed the product installation"),
    ("installation_date", "Installation Date", "service", "Date on which the product was installed at its current location"),
    ("installation_location", "Installation Location", "service", "Physical address or coordinates of the product's installation site"),
    ("asset_register_id", "Asset Register ID", "service", "Identifier of the product in the owner's asset management register"),
    ("fleet_management_id", "Fleet Management ID", "service", "Identifier within a fleet or estate management system"),
    ("usage_hours_total", "Total Usage Hours", "service", "Total cumulative operating hours recorded by the product"),
    ("usage_cycles_total", "Total Usage Cycles", "service", "Total cumulative programme cycles or operating cycles completed"),
    ("error_rate_per_1000h", "Error Rate", "service", "Observed error or fault rate per 1000 operating hours"),
    ("performance_degradation_pct", "Performance Degradation", "service", "Measured percentage reduction in performance compared to initial specification"),

    # ── Maintenance extras ──────────────────────────────────────────────────────
    ("condition_grade", "Condition Grade", "maintenance", "Standardised physical condition grade of the product (A=excellent, D=poor)"),
    ("inspection_date", "Inspection Date", "maintenance", "Date of the most recent formal product inspection"),
    ("total_repair_count", "Total Repair Count", "maintenance", "Total number of repair interventions recorded over product lifetime"),
    ("mean_time_between_failures_h", "Mean Time Between Failures", "maintenance", "Statistical MTBF in operating hours derived from field data"),

    # ── Compliance extras ───────────────────────────────────────────────────────
    ("scip_database_id", "SCIP Database ID", "compliance", "Notification identifier in ECHA SCIP database for articles containing SVHCs"),
    ("product_safety_regulation_id", "Product Safety Regulation ID", "compliance", "Reference under the EU General Product Safety Regulation (GPSR)"),

    # ── Economic extras ─────────────────────────────────────────────────────────
    ("trade_in_value_eur", "Trade-in Value", "economic", "Estimated trade-in value offered by retailers or take-back schemes in EUR"),
    ("lease_rate_monthly_eur", "Monthly Lease Rate", "economic", "Monthly leasing rate for product-as-a-service offering in EUR"),
    ("end_of_life_value_eur", "End-of-Life Value", "economic", "Estimated residual material value at confirmed end of life in EUR"),

    # ── Circular economy extras ─────────────────────────────────────────────────
    ("cobalt_content_g", "Cobalt Content", "circular_economy", "Mass of cobalt present in the product in grams"),
    ("lithium_content_g", "Lithium Content", "circular_economy", "Mass of lithium present in the product in grams"),
    ("nickel_content_g", "Nickel Content", "circular_economy", "Mass of nickel present in the product in grams"),
    ("silver_content_g", "Silver Content", "circular_economy", "Mass of silver present in the product in grams"),
    ("copper_content_kg", "Copper Content", "circular_economy", "Mass of copper present in the product in kilograms"),
    ("aluminum_content_kg", "Aluminum Content", "circular_economy", "Mass of aluminium present in the product in kilograms"),
    ("steel_content_kg", "Steel Content", "circular_economy", "Mass of steel present in the product in kilograms"),
    ("plastic_content_kg", "Plastic Content", "circular_economy", "Total mass of plastics present in the product in kilograms"),
    ("recycling_route", "Recycling Route", "circular_economy", "Designated material recovery or recycling route for end-of-life processing"),
    ("epr_fee_eur", "EPR Fee", "circular_economy", "Producer contribution fee paid under the Extended Producer Responsibility scheme in EUR"),

    # ── Thermal extras (boiler) ─────────────────────────────────────────────────
    ("flue_connection_diameter_mm", "Flue Connection Diameter", "thermal", "Diameter of the flue gas outlet connection in millimetres"),
    ("modulation_range_pct", "Modulation Range", "thermal", "Output modulation range as a percentage of rated output"),
    ("weather_compensation_capable", "Weather Compensation Capable", "thermal", "Indicates whether weather-compensated control is supported"),

    # ── Electrical extras (lithium_battery) ────────────────────────────────────
    ("max_system_voltage_v", "Maximum System Voltage", "electrical", "Maximum allowable system voltage in volts"),
    ("charging_standard", "Charging Standard", "electrical", "Supported charging communication protocol or standard"),

    # ── Connectivity extras ─────────────────────────────────────────────────────
    ("grid_injection_capable", "Grid Injection Capable", "connectivity", "Indicates whether the product can inject surplus energy into the grid"),

    # ── Metadata extras ─────────────────────────────────────────────────────────
    ("lifecycle_stage", "Lifecycle Stage", "metadata", "Current lifecycle stage of the product instance (new, in-use, refurbished, end-of-life)"),
]


# ─── Role-Event Relevance Mappings ─────────────────────────────────────────────
# The priorities are maintained in ontology/role_event_priorities.csv so that they can be
# inspected, reviewed and adapted without changing code.
# Format after loading: { (role, event): { field_name: priority(0.0-1.0) } }
# Fields not listed for a combination are not recommended (hidden).

PRIORITIES_FILE = Path(__file__).resolve().parents[1] / "ontology" / "role_event_priorities.csv"


def load_role_event_mappings(path: Path = PRIORITIES_FILE) -> dict[tuple[str, str], dict[str, float]]:
    """Load the role-event relevance priorities from CSV."""
    mappings: dict[tuple[str, str], dict[str, float]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(line for line in handle if line.strip() and not line.startswith("#"))
        for row in rows:
            priority = float(row["priority"])
            if not 0.0 <= priority <= 1.0:
                raise ValueError(f"Priority out of range in {path}: {row}")
            mappings.setdefault((row["role"], row["event"]), {})[row["field_name"]] = priority
    return mappings


ROLE_EVENT_MAPPINGS = load_role_event_mappings()


# ─── Product Type Specific Fields ──────────────────────────────────────────────

# Shared cross-product fields (applied to all 5 product types)
_CROSS_PRODUCT_FIELDS = [
    # identification
    "brand_name", "product_variant", "ean_barcode", "batch_number",
    "country_of_origin", "customs_tariff_number", "digital_twin_reference",
    "product_registration_id",
    # technical
    "rated_power_w", "standby_power_w", "operating_voltage_v", "ip_rating",
    "noise_level_db", "colour", "installation_type", "connectivity_protocol",
    "software_version", "spare_parts_availability_years", "spare_parts_supplier",
    "repair_difficulty_score",
    # materials (subset, no rare_earth_elements by default)
    "polymer_types_in_casing", "recycled_content_pct", "bio_based_content_pct",
    "critical_raw_materials", "conflict_minerals_declaration",
    "substance_of_concern_list", "packaging_material", "packaging_recyclability",
    "halogen_free",
    # sustainability
    "energy_consumption_kwh_per_year", "scope1_co2_manufacturing_kg",
    "scope2_co2_manufacturing_kg", "scope3_co2_upstream_kg",
    "water_stress_index_manufacturing", "product_environmental_footprint",
    "ecodesign_class", "eco_mode_available", "co2_saved_vs_average_kg",
    "eu_ecolabel", "epd_reference", "lca_reference", "take_back_scheme_participation",
    # compliance
    "rohs_compliance", "weee_category", "reach_compliance", "ecodesign_regulation",
    "extended_producer_responsibility_id", "type_approval_number",
    "low_voltage_directive", "electromagnetic_compatibility",
    # safety
    "flammability_class", "overheat_protection",
    "safety_data_sheet_reference", "child_safety_compliance",
    # end_of_life
    "disassembly_time_estimate_min", "component_separation_difficulty",
    "end_of_life_collection_point", "remanufacturing_eligibility",
    "refurbishment_grade", "critical_material_recovery_instructions",
    "dismantling_information_url", "weee_treatment_instructions",
    # economic
    "leasing_eligible", "product_as_a_service_eligible", "insurance_information",
    "repair_cost_estimate_eur", "operating_cost_annual_eur", "spare_parts_cost_index",
    "total_cost_of_ownership_eur", "subsidy_eligibility",
    "carbon_credit_value_eur", "scrap_metal_value_eur",
    # maintenance
    "last_service_date", "service_provider_name", "next_service_due_date",
    "filter_replacement_interval_months", "fault_code_history",
    "remote_diagnostic_capable",
    "condition_grade", "inspection_date", "total_repair_count",
    "mean_time_between_failures_h",
    # compliance extras
    "scip_database_id", "product_safety_regulation_id",
    # economic extras
    "trade_in_value_eur", "lease_rate_monthly_eur", "end_of_life_value_eur",
    # circular_economy
    "previous_owner_count", "product_age_years", "remaining_lifetime_pct",
    "reuse_potential_score", "circular_economy_index", "design_for_repair_compliance",
    "modular_design", "software_update_end_date", "interoperability_standard",
    "rental_return_condition", "cradle_to_cradle_certification",
    "material_passport_reference", "urban_mining_priority",
    "functional_unit_defined", "circularity_label",
    "copper_content_kg", "aluminum_content_kg", "steel_content_kg",
    "plastic_content_kg", "recycling_route", "epr_fee_eur",
    # supply_chain
    "supplier_name", "supplier_country", "supply_chain_transparency_level",
    "product_origin_country", "manufacturing_site_id",
    "deforestation_free_declaration", "child_labour_free_declaration",
    "due_diligence_report_reference", "traceability_system",
    "supplier_audit_status", "responsible_sourcing_certification",
    "local_content_pct",
    # logistics
    "packaging_weight_kg", "packaged_dimensions_mm", "transport_co2_kg",
    "storage_conditions", "handling_instructions", "fragile_indicator",
    "return_logistics_scheme", "pallet_count",
    # service
    "ownership_type", "service_contract_type", "service_contract_expiry",
    "installer_name", "installation_date", "installation_location",
    "asset_register_id", "fleet_management_id", "usage_hours_total",
    "usage_cycles_total", "error_rate_per_1000h", "performance_degradation_pct",
    # metadata
    "data_quality_score", "data_custodian", "dpp_schema_version",
    "verification_status", "publication_date", "lifecycle_stage",
    # connectivity extras
    "grid_injection_capable",
]

PRODUCT_TYPE_FIELDS = {
    "washing_machine": [
        # ── existing core fields ──
        "product_id", "product_type", "manufacturer", "model", "serial_number",
        "manufacturing_date", "manufacturing_location", "specifications",
        "components", "materials", "weight_kg", "dimensions",
        "energy_label", "repairability_score", "recyclability_pct",
        "carbon_footprint_kg_co2", "expected_lifetime_years",
        "hazardous_substances", "certifications", "compliance",
        "disassembly_instructions", "recycling_instructions", "disposal_instructions",
        "purchase_price_eur", "residual_value_eur", "warranty_years",
        "maintenance_schedule", "repair_history",
        "data_sources", "last_updated",
        # ── water ──
        "water_consumption_l_per_cycle", "water_consumption_annual_l",
        "water_hardness_compatibility", "hot_water_connection",
        "hose_material", "hose_length_m", "aquastop_feature", "self_cleaning_filter",
        # ── performance ──
        "drum_volume_l", "drum_material", "load_capacity_kg", "spin_speed_rpm",
        "wash_temperature_max_c", "motor_type", "number_of_programmes",
        "child_lock", "delay_start", "short_cycle_duration_min",
        "vibration_emission_db",
        # ── connectivity ──
        "wifi_enabled", "app_control_supported", "voice_assistant_compatible",
        "smart_grid_ready", "home_automation_protocol", "ota_update_supported",
        "energy_monitoring_capable", "demand_response_capable",
        # ── sustainability extras ──
        "energy_consumption_kwh_per_cycle", "noise_class",
        # ── maintenance extras ──
        "descaling_interval_months", "lubrication_schedule",
        # ── end_of_life extras ──
        "battery_removal_instructions",
        # ── circular_economy extras ──
        "cobalt_content_g",
    ] + _CROSS_PRODUCT_FIELDS,

    "dishwasher": [
        # ── existing core fields ──
        "product_id", "product_type", "manufacturer", "model", "serial_number",
        "manufacturing_date", "manufacturing_location", "specifications",
        "components", "materials", "weight_kg", "dimensions",
        "energy_label", "repairability_score", "recyclability_pct",
        "carbon_footprint_kg_co2", "expected_lifetime_years",
        "hazardous_substances", "certifications", "compliance",
        "disassembly_instructions", "recycling_instructions", "disposal_instructions",
        "purchase_price_eur", "residual_value_eur", "warranty_years",
        "maintenance_schedule", "repair_history",
        "data_sources", "last_updated",
        # ── water (all 10, including DW-specific) ──
        "water_consumption_l_per_cycle", "water_consumption_annual_l",
        "water_hardness_compatibility", "hot_water_connection",
        "rinse_aid_consumption_ml_per_cycle", "salt_consumption_g_per_cycle",
        "hose_material", "hose_length_m", "aquastop_feature", "self_cleaning_filter",
        # ── performance (DW subset) ──
        "wash_temperature_max_c", "motor_type", "number_of_programmes",
        "child_lock", "delay_start", "short_cycle_duration_min",
        "basket_capacity_place_settings",
        # ── connectivity ──
        "wifi_enabled", "app_control_supported", "voice_assistant_compatible",
        "smart_grid_ready", "home_automation_protocol", "ota_update_supported",
        "energy_monitoring_capable", "demand_response_capable",
        # ── sustainability extras ──
        "energy_consumption_kwh_per_cycle", "noise_class",
        # ── maintenance extras ──
        "descaling_interval_months", "lubrication_schedule",
        # ── end_of_life extras ──
        "battery_removal_instructions",
        # ── circular_economy extras ──
        "cobalt_content_g",
    ] + _CROSS_PRODUCT_FIELDS,

    "boiler": [
        # ── existing core fields ──
        "product_id", "product_type", "manufacturer", "model", "serial_number",
        "manufacturing_date", "manufacturing_location", "specifications",
        "components", "materials", "weight_kg", "dimensions",
        "energy_label", "repairability_score", "recyclability_pct",
        "carbon_footprint_kg_co2", "expected_lifetime_years",
        "hazardous_substances", "certifications", "compliance",
        "disassembly_instructions", "recycling_instructions", "disposal_instructions",
        "purchase_price_eur", "residual_value_eur", "warranty_years",
        "maintenance_schedule", "repair_history",
        "data_sources", "last_updated",
        # ── water ──
        "hot_water_connection",
        # ── thermal (all 19) ──
        "boiler_type", "fuel_type", "burner_type", "heat_exchanger_material",
        "flue_gas_temperature_c", "venting_type", "nox_emission_class",
        "seasonal_efficiency_pct", "efficiency_at_partial_load_pct",
        "max_output_power_kw", "min_output_power_kw",
        "hot_water_flow_rate_l_per_min", "expansion_vessel_size_l",
        "frost_protection", "ignition_type", "gas_valve_manufacturer",
        "condensate_pipe_material", "service_interval_months",
        "pressure_relief_valve_spec",
        # ── connectivity ──
        "smart_grid_ready", "home_automation_protocol", "ota_update_supported",
        "energy_monitoring_capable", "demand_response_capable",
        # ── compliance extras ──
        "gas_appliance_regulation", "f_gas_regulation",
        # ── safety extras ──
        "short_circuit_protection",
        # ── end_of_life extras ──
        "refrigerant_type",
        # ── maintenance extras ──
        "descaling_interval_months", "lubrication_schedule",
        # ── thermal extras ──
        "flue_connection_diameter_mm", "modulation_range_pct",
        "weather_compensation_capable",
    ] + _CROSS_PRODUCT_FIELDS,

    "solar_panel": [
        # ── existing core fields ──
        "product_id", "product_type", "manufacturer", "model", "serial_number",
        "manufacturing_date", "manufacturing_location", "specifications",
        "components", "materials", "weight_kg", "dimensions",
        "energy_label", "repairability_score", "recyclability_pct",
        "carbon_footprint_kg_co2", "expected_lifetime_years",
        "hazardous_substances", "certifications", "compliance",
        "disassembly_instructions", "recycling_instructions", "disposal_instructions",
        "purchase_price_eur", "residual_value_eur", "warranty_years",
        "maintenance_schedule", "repair_history",
        "data_sources", "last_updated",
        # ── photovoltaic (all 21) ──
        "cell_technology", "cell_efficiency_pct", "module_efficiency_pct",
        "rated_power_watt_peak", "power_tolerance_pct",
        "temperature_coefficient_pmax", "degradation_rate_pct_per_year",
        "bifaciality_factor", "backsheet_material", "frame_material",
        "junction_box_ip_rating", "bypass_diode_count", "fire_classification",
        "salt_mist_resistance", "ammonia_resistance", "flash_test_result",
        "mounting_system_compatibility", "inverter_compatibility",
        "open_circuit_voltage_v", "short_circuit_current_a", "number_of_cells",
        # ── connectivity ──
        "smart_grid_ready", "energy_monitoring_capable", "demand_response_capable",
        # ── materials extras ──
        "rare_earth_elements",
        # ── compliance extras ──
        "construction_products_regulation",
        # ── safety extras ──
        "fire_safety_standard",
        # ── circular_economy extras ──
        "silver_content_g",
    ] + _CROSS_PRODUCT_FIELDS,

    "lithium_battery": [
        # ── existing core fields ──
        "product_id", "product_type", "manufacturer", "model", "serial_number",
        "manufacturing_date", "manufacturing_location", "specifications",
        "components", "materials", "weight_kg", "dimensions",
        "energy_label", "repairability_score", "recyclability_pct",
        "carbon_footprint_kg_co2", "expected_lifetime_years",
        "hazardous_substances", "certifications", "compliance",
        "disassembly_instructions", "recycling_instructions", "disposal_instructions",
        "purchase_price_eur", "residual_value_eur", "warranty_years",
        "maintenance_schedule", "repair_history",
        "data_sources", "last_updated",
        # ── electrical (all 18) ──
        "cell_chemistry", "nominal_voltage_v", "nominal_capacity_kwh",
        "usable_capacity_kwh", "charge_cycles_rated", "depth_of_discharge_pct",
        "max_charge_rate_kw", "max_discharge_rate_kw", "cell_format",
        "electrolyte_type", "cathode_material", "anode_material",
        "separator_material", "thermal_management_type",
        "bms_manufacturer", "bms_firmware_version",
        "un38_3_test_result", "iec_62619_compliance",
        # ── battery_health (all 8) ──
        "state_of_health_pct", "state_of_charge_pct", "actual_cycle_count",
        "end_of_life_capacity_threshold_pct", "second_life_eligibility",
        "storage_temperature_range_c", "operating_temperature_range_c",
        "calendar_age_years",
        # ── connectivity ──
        "smart_grid_ready", "home_automation_protocol",
        "energy_monitoring_capable", "demand_response_capable",
        # ── materials extras ──
        "rare_earth_elements",
        # ── compliance extras ──
        "eu_battery_regulation_compliance",
        # ── safety extras ──
        "thermal_runaway_protection", "short_circuit_protection",
        "transportation_class", "fire_safety_standard",
        # ── end_of_life extras ──
        "battery_removal_instructions",
        # ── electrical extras ──
        "max_system_voltage_v", "charging_standard",
        # ── circular_economy extras ──
        "cobalt_content_g", "lithium_content_g", "nickel_content_g",
    ] + _CROSS_PRODUCT_FIELDS,
}


DPP_TERM_ALIASES = {
    # classes
    "dpp:Product": {"product_type"},
    "dpp:WashingMachine": {"washing_machine"},
    "dpp:Dishwasher": {"dishwasher"},
    "dpp:Boiler": {"boiler"},
    "dpp:SolarPanel": {"solar_panel"},
    "dpp:LithiumBattery": {"lithium_battery"},
    "dpp:HazardousSubstance": {"hazardous_substances"},
    "dpp:Recycle": {"recycling_instructions"},
    "dpp:Repair": {"repair_history", "disassembly_instructions"},
    # properties that correspond to DPP data fields
    "dpp:repairabilityScore": {"repairability_score"},
    "dpp:recyclabilityPercentage": {"recyclability_pct"},
    "dpp:hasMaterial": {"materials"},
    "dpp:productId": {"product_id"},
    "dpp:manufacturer": {"manufacturer"},
    "dpp:model": {"model"},
    "dpp:eanBarcode": {"ean_barcode"},
    "dpp:brandName": {"brand_name"},
    "dpp:colour": {"colour"},
    "dpp:countryOfOrigin": {"country_of_origin"},
    "dpp:manufacturingDate": {"manufacturing_date"},
    "dpp:weightKg": {"weight_kg"},
    "dpp:recycledContentPct": {"recycled_content_pct"},
    "dpp:substanceOfConcernList": {"substance_of_concern_list"},
    "dpp:energyLabel": {"energy_label"},
    "dpp:certifications": {"certifications"},
}


CONSTRAINTS = (
    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Role) REQUIRE r.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (pt:ProductType) REQUIRE pt.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (df:DataField) REQUIRE df.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (dc:DataCategory) REQUIRE dc.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (t:OntologyTerm) REQUIRE t.curie IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:SSSOMMapping) REQUIRE m.mapping_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (ms:MappingSet) REQUIRE ms.mapping_set_id IS UNIQUE",
)


async def ensure_constraints(client: Neo4jClient) -> None:
    """Create the uniqueness constraints of the static knowledge graph layer."""
    for constraint in CONSTRAINTS:
        await client.run_write(constraint)


async def seed_knowledge_graph(client: Neo4jClient) -> None:
    """Seed the Neo4j knowledge graph with the DPP ontology."""

    logger.info("Seeding Knowledge Graph...")

    # Clear the static subgraph only. The dynamic subgraph (DPPTemplate, TemplateTerm,
    # TemplateUser) holds user-created templates and is preserved across re-seeding;
    # REFERS_TO links are restored below once the DataField nodes exist again.
    await client.run_write(
        """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN
              ["Role", "Event", "ProductType", "DataField", "DataCategory",
               "OntologyTerm", "SSSOMMapping", "MappingSet"])
        DETACH DELETE n
        """
    )

    await ensure_constraints(client)

    # Create Role nodes
    roles = ["recycler", "consumer", "manufacturer", "repairer", "collector"]
    role_labels = {
        "recycler": "Recycling Company",
        "consumer": "End Consumer",
        "manufacturer": "Product Manufacturer",
        "repairer": "Repair Service Provider",
        "collector": "Collection & B-Stock Operator",
    }
    for role in roles:
        await client.run_write(
            "CREATE (r:Role {name: $name, display_name: $display_name})",
            {"name": role, "display_name": role_labels[role]},
        )

    # Create Event nodes
    events = ["purchase", "repair", "recycling", "maintenance", "disposal", "resale"]
    event_labels = {
        "purchase": "Product Purchase",
        "repair": "Product Repair",
        "recycling": "End-of-Life Recycling",
        "maintenance": "Scheduled Maintenance",
        "disposal": "Product Disposal",
        "resale": "Second-hand Resale",
    }
    for event in events:
        await client.run_write(
            "CREATE (e:Event {name: $name, display_name: $display_name})",
            {"name": event, "display_name": event_labels[event]},
        )

    # Create ProductType nodes
    product_types = {
        "washing_machine": "Washing Machine",
        "dishwasher": "Dishwasher",
        "boiler": "Boiler / Gas Heating",
        "solar_panel": "Solar Panel",
        "lithium_battery": "Lithium Battery Storage",
    }
    for pt_name, pt_label in product_types.items():
        await client.run_write(
            "CREATE (pt:ProductType {name: $name, display_name: $display_name})",
            {"name": pt_name, "display_name": pt_label},
        )

    # Create DataCategory nodes
    categories = set(f[2] for f in DATA_FIELDS)
    category_labels = {
        "identification": "Product Identification",
        "technical": "Technical Specifications",
        "components": "Product Components",
        "materials": "Material Composition",
        "sustainability": "Sustainability Metrics",
        "safety": "Safety Information",
        "compliance": "Regulatory Compliance",
        "end_of_life": "End of Life",
        "economic": "Economic Data",
        "maintenance": "Maintenance & Repair",
        "metadata": "Data Metadata",
        # new categories
        "water": "Water Consumption",
        "performance": "Performance Metrics",
        "connectivity": "Connectivity & Smart Features",
        "thermal": "Thermal & Combustion",
        "electrical": "Electrical Characteristics",
        "battery_health": "Battery Health & State",
        "photovoltaic": "Photovoltaic Properties",
        "circular_economy": "Circular Economy",
        "supply_chain": "Supply Chain & Origin",
        "logistics": "Logistics & Transport",
        "service": "Service & Ownership",
    }
    for cat in categories:
        await client.run_write(
            "CREATE (dc:DataCategory {name: $name, display_name: $display_name})",
            {"name": cat, "display_name": category_labels.get(cat, cat)},
        )

    # Create DataField nodes and link to categories
    for field_name, display_name, category, description in DATA_FIELDS:
        await client.run_write(
            """
            MATCH (dc:DataCategory {name: $category})
            CREATE (df:DataField {
                name: $name,
                display_name: $display_name,
                category: $category,
                description: $description
            })
            CREATE (df)-[:BELONGS_TO]->(dc)
            """,
            {
                "name": field_name,
                "display_name": display_name,
                "category": category,
                "description": description,
            },
        )

    # Link DataFields to ProductTypes
    for pt_name, fields in PRODUCT_TYPE_FIELDS.items():
        for field_name in fields:
            await client.run_write(
                """
                MATCH (pt:ProductType {name: $pt_name})
                MATCH (df:DataField {name: $field_name})
                CREATE (pt)-[:HAS_FIELD]->(df)
                """,
                {"pt_name": pt_name, "field_name": field_name},
            )

    # Create Role-Event-DataField relationships with priorities
    for (role, event), field_priorities in ROLE_EVENT_MAPPINGS.items():
        for field_name, priority in field_priorities.items():
            await client.run_write(
                """
                MATCH (r:Role {name: $role})
                MATCH (e:Event {name: $event})
                MATCH (df:DataField {name: $field_name})
                CREATE (r)-[:NEEDS {priority: $priority, event: $event}]->(df)
                MERGE (r)-[p:PARTICIPATES_IN]->(e)
                ON CREATE SET p.context = $role + ":" + $event
                """,
                {
                    "role": role,
                    "event": event,
                    "field_name": field_name,
                    "priority": priority,
                },
            )

    # Re-link preserved dynamic template terms to the re-created DataField nodes
    await client.run_write(
        """
        MATCH (tt:TemplateTerm)
        MATCH (df:DataField {name: tt.name})
        MERGE (tt)-[:REFERS_TO]->(df)
        """
    )

    await seed_sssom_mappings(client)

    logger.info("Seeding Knowledge Graph seeded successfully with %d data fields, %d roles, %d events",
                len(DATA_FIELDS), len(roles), len(events))


async def seed_sssom_mappings(client: Neo4jClient) -> None:
    """Seed SSSOM ontology mappings into Neo4j and link them to known DPP terms."""
    mapping_set = load_sssom_mapping_set()
    metadata = mapping_set["metadata"]
    mappings = mapping_set["mappings"]

    if not mappings:
        logger.warning("No SSSOM mappings found to seed.")
        return

    # Replace any previously seeded mapping set (e.g. an older version of the TSV file).
    await client.run_write("MATCH (n) WHERE n:SSSOMMapping OR n:MappingSet DETACH DELETE n")
    await client.run_write(
        "MATCH (t:OntologyTerm) WHERE NOT (t)<-[:HAS_SUBJECT|HAS_OBJECT]-() DETACH DELETE t"
    )

    sssom_constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:OntologyTerm) REQUIRE t.curie IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:SSSOMMapping) REQUIRE m.mapping_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (ms:MappingSet) REQUIRE ms.mapping_set_id IS UNIQUE",
    ]
    for constraint in sssom_constraints:
        await client.run_write(constraint)

    mapping_set_id = metadata.get("mapping_set_id", "local:sssom:dpp-mappings")
    await client.run_write(
        """
        MERGE (ms:MappingSet {mapping_set_id: $mapping_set_id})
        SET ms.mapping_set_version = $mapping_set_version,
            ms.mapping_set_description = $mapping_set_description,
            ms.creator_id = $creator_id,
            ms.creator_label = $creator_label,
            ms.license = $license,
            ms.curie_map = $curie_map
        """,
        {
            "mapping_set_id": mapping_set_id,
            "mapping_set_version": metadata.get("mapping_set_version"),
            "mapping_set_description": metadata.get("mapping_set_description"),
            "creator_id": metadata.get("creator_id"),
            "creator_label": metadata.get("creator_label"),
            "license": metadata.get("license"),
            "curie_map": json.dumps(metadata.get("curie_map", {}), sort_keys=True),
        },
    )

    for mapping in mappings:
        await client.run_write(
            """
            MATCH (ms:MappingSet {mapping_set_id: $mapping_set_id})
            MERGE (subject:OntologyTerm {curie: $subject_id})
            SET subject.label = $subject_label
            MERGE (object:OntologyTerm {curie: $object_id})
            SET object.label = $object_label
            MERGE (mapping:SSSOMMapping {mapping_id: $mapping_id})
            SET mapping.predicate_id = $predicate_id,
                mapping.mapping_justification = $mapping_justification,
                mapping.mapping_tool = $mapping_tool,
                mapping.confidence = $confidence
            MERGE (ms)-[:CONTAINS_MAPPING]->(mapping)
            MERGE (mapping)-[:HAS_SUBJECT]->(subject)
            MERGE (mapping)-[:HAS_OBJECT]->(object)
            MERGE (subject)-[:MAPPED_TO {
                mapping_id: $mapping_id,
                predicate_id: $predicate_id
            }]->(object)
            """,
            {
                "mapping_set_id": mapping_set_id,
                **mapping,
            },
        )

        for local_name in DPP_TERM_ALIASES.get(mapping["subject_id"], set()):
            await client.run_write(
                """
                MATCH (term:OntologyTerm {curie: $subject_id})
                OPTIONAL MATCH (df:DataField {name: $local_name})
                OPTIONAL MATCH (pt:ProductType {name: $local_name})
                FOREACH (_ IN CASE WHEN df IS NULL THEN [] ELSE [1] END |
                    MERGE (df)-[:REPRESENTS_TERM]->(term)
                )
                FOREACH (_ IN CASE WHEN pt IS NULL THEN [] ELSE [1] END |
                    MERGE (pt)-[:REPRESENTS_TERM]->(term)
                )
                """,
                {"subject_id": mapping["subject_id"], "local_name": local_name},
            )

    logger.info("Seeded %d SSSOM mappings from %s", len(mappings), mapping_set_id)


async def check_seed_status(client: Neo4jClient) -> bool:
    """Check if the KG has been seeded."""
    result = await client.run_query("MATCH (r:Role) RETURN count(r) as count")
    return result[0]["count"] > 0 if result else False


async def check_static_layer_current(client: Neo4jClient) -> bool:
    """Check whether the static layer in Neo4j matches the ontology defined in this module.

    Used after importing a bundled graph snapshot: if the ontology was changed after the
    snapshot was exported, the static layer is re-seeded (templates are preserved).
    """
    fields = await client.run_query("MATCH (df:DataField) RETURN df.name AS name, df.category AS category")
    if {(row["name"], row["category"]) for row in fields} != {(n, c) for n, _l, c, _d in DATA_FIELDS}:
        return False
    needs = await client.run_query(
        "MATCH (r:Role)-[n:NEEDS]->(df:DataField) "
        "RETURN r.name AS role, n.event AS event, df.name AS field, n.priority AS priority"
    )
    expected_needs = {
        (role, event, field, priority)
        for (role, event), priorities in ROLE_EVENT_MAPPINGS.items()
        for field, priority in priorities.items()
    }
    if {(r["role"], r["event"], r["field"], r["priority"]) for r in needs} != expected_needs:
        return False
    has_field = await client.run_query(
        "MATCH (pt:ProductType)-[:HAS_FIELD]->(df:DataField) RETURN pt.name AS pt, df.name AS field"
    )
    expected_has_field = {(pt, f) for pt, fields_ in PRODUCT_TYPE_FIELDS.items() for f in fields_}
    return {(r["pt"], r["field"]) for r in has_field} == expected_has_field


async def check_sssom_seed_status(client: Neo4jClient) -> bool:
    """Check if the SSSOM mapping subgraph is seeded with the current version of the TSV file."""
    expected = load_sssom_mapping_set()["metadata"].get("mapping_set_version")
    result = await client.run_query(
        "MATCH (ms:MappingSet) OPTIONAL MATCH (ms)-[:CONTAINS_MAPPING]->(m:SSSOMMapping) "
        "RETURN ms.mapping_set_version AS version, count(m) AS count"
    )
    if not result or not result[0]["count"]:
        return False
    return expected is None or result[0]["version"] == expected
