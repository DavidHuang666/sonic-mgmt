# INDEX — Transceiver DOM Test Framework

This document tracks the structure, data flow, and key components
of the transceiver DOM test framework.

---

## DOM Test Directory
- tests/transceiver/dom/
  - __init__.py
  - conftest.py
  - test_dom_availability.py
  - test_dom_operational_range.py
  - test_dom_threshold.py
  - test_dom_consistency.py
  - advanced/test_dom_interface_state.py
  - advanced/test_dom_polling.py



## Data Flow Summary
1) Inventory & attribute JSON loaded
2) Normalization and prerequisite checks applied
3) DOM operational data retrieved
4) Validation rules executed
5) Absent attributes are skipped; configured checks must pass or fail explicitly

## Reference Infra Modules
- tests/transceiver/infra/config_parser.py
- tests/transceiver/infra/attribute_manager.py
- tests/transceiver/infra/template_validator.py

## New DOM Fixtures
- `dom_port_context`: Filters `port_attributes_dict` to ports with non-empty `DOM_ATTRIBUTES`.
- `dom_ports`: DOM-enabled port list sorted by interface prefix + numeric suffix (e.g., `Ethernet0, Ethernet4, Ethernet8, Ethernet12`).
- `dom_operational_fields_by_port`: Expands configured operational attributes to expected sensor fields, including `LANE_NUM` lane expansion.
- `dom_operational_ranges_by_port`: Builds per-port `field -> {attr_name, min, max}` maps for operational-range-aware validations.
- `dom_consistency_variation_rules`: Operational-attribute to variation-threshold mapping used by TC4.
- `dom_consistency_variation_thresholds_by_port`: Validates and parses per-port consistency variation threshold attributes from `DOM_ATTRIBUTES`.
- `dom_threshold_fields_by_port`: Builds threshold key mappings for `TRANSCEIVER_DOM_THRESHOLD`.
- `dom_sensor_by_port` / `dom_threshold_by_port`: Bulk reads from STATE_DB hash tables.
- `dom_db_reader`: Callable fixture for repeated sensor/threshold reads during polling tests.
- `parse_dom_numeric` / `parse_dom_update_time`: Robust parsers for numeric fields and `last_update_time`.
- `dom_now_utc`: DUT-time based UTC clock source for freshness checks.
- DOM parser compatibility: supports both standard HGETALL key/value line output and single-line serialized dict output from platform wrappers.
- DOM time parser compatibility: supports `Tue Mar 03 06:31:44 2026` style `last_update_time` values in addition to ISO and epoch formats.

## New DOM Test Files
- `tests/transceiver/dom/test_dom_availability.py`
  - TC1: `test_dom_data_availability_verification` validates configured expected fields and freshness; configured field/timestamp gaps fail.
- `tests/transceiver/dom/test_dom_operational_range.py`
  - TC2: `test_dom_sensor_operational_range_validation` validates freshness (`last_update_time`) and operational ranges for configured attributes only; configured field missing/non-numeric fails.
- `tests/transceiver/dom/test_dom_threshold.py`
  - TC3: threshold comparison, completeness, hierarchy validation, operational-vs-warning boundary checks.
- `tests/transceiver/dom/test_dom_consistency.py`
  - TC4: polling-based consistency checks with timestamp progression and threshold-driven variation validation using flat consistency threshold attributes (`tx/rx power`, `tx bias`, `laser/module temperature`, `voltage`); `consistency_check_poll_count` and `max_update_time_sec` are treated as required config for this test and missing/invalid values fail explicitly.
- `tests/transceiver/dom/advanced/test_dom_interface_state.py`
  - Advanced TC1 skeleton (currently explicit skip).
- `tests/transceiver/dom/advanced/test_dom_polling.py`
  - Advanced TC2 skeleton (currently explicit skip).

## DOM Data/Validation Flow Notes
- Tests are fully attribute-driven and consume only `DOM_ATTRIBUTES` resolved by infra priority rules.
- Missing DOM attributes in `dom.json` are treated as non-applicable and skipped.
- For attributes configured in `dom.json`, required mapped STATE_DB fields must exist and be parseable for the corresponding test case; missing/non-parseable values are failures.
- STATE_DB access uses `sonic-db-cli STATE_DB HGETALL`, with `redis-cli --raw -n 6` fallback.
- DOM failure reporting style now follows EEPROM aggregation style: grouped by port with indented per-field/per-check failure details.
- DOM tests now use EEPROM-like result control flow: `field_failures`/`all_failures` + `has_configured_checks`, without per-port/pass counters such as `port_validated` or `validated_ports`.
- DOM test files include explicit step comments to align code blocks with the corresponding test-plan execution steps.
- Basic DOM TC1-TC4 test files do not declare explicit topology markers; topology selection is left to the shared pytest/testbed infrastructure.

## EEPROM Bring-Up Notes
- Inventory files updated for Accelight OSFP module bring-up:
  - `ansible/files/transceiver/inventory/dut_info/lab-dut-01.json`
  - `ansible/files/transceiver/inventory/dut_info/sonic.json`
  - `ansible/files/transceiver/inventory/dut_info/str-nexthop_4010-01.json`
  - `ansible/files/transceiver/inventory/normalization_mappings.json`
  - `ansible/files/transceiver/inventory/attributes/eeprom.json`
  - `ansible/files/transceiver/inventory/prerequisites.json`
- Key data flow alignment:
  - `dut_info` now scopes to currently detected optics ports (`Ethernet0/4/8/12`) to avoid failing on absent modules.
  - `normalization_mappings` now maps `Accelight` and `AGP80SC0CW41002` for vendor/PN based attribute resolution.
  - `eeprom.json` now provides vendor+PN specific EEPROM attributes (`dual_bank_supported`, firmware versions, `cmis_revision`).
  - `prerequisites.json` EEPROM entry now points to an existing function (`test_eeprom_content_verification_via_show_cli`) to avoid missing-function pretest failures.
  - `dom.json` now uses infra-compatible vendor key (`ACCELIGHT`) and global timing/freshness thresholds in `defaults` so `DOM_ATTRIBUTES` can resolve correctly for current module part number.
