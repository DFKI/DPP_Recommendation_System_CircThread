# Repair & Service Network Provider

Provider for repair and service data recorded by an independent network of repairers,
refurbishers, and authorised service partners.

It contributes fields such as:

- `repair_history`, `fault_code_history`, `total_repair_count`
- `last_service_date`, `next_service_due_date`, `inspection_date`, `service_provider_name`
- `service_contract_type`, `service_contract_expiry`
- `maintenance_schedule`, `lubrication_schedule`, `filter_replacement_interval_months`, `descaling_interval_months`
- `spare_parts_supplier`, `spare_parts_cost_index`, `repair_cost_estimate_eur`
- `refurbishment_grade`, `condition_grade`

For the CircThread partner products it only adds records that no other provider holds. For
the BSH appliances identified by their EPREL registration number (`2219971`, `2613426`) it is
the main source of use-phase data. `SP-SUNPOWER-002` is deliberately not covered.

Demo products:

```text
WM-BOSCH-001
2219971
```

Metadata endpoint:

```text
/.well-known/circthread-service
```

Tests (run from the repository root):

```bash
python -m unittest discover -s services/repair_service_provider/tests
```
