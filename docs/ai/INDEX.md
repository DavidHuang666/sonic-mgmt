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
- `tests/transceiver/attribute_parser/config_parser.py`
- `tests/transceiver/attribute_parser/attribute_manager.py`
- `tests/transceiver/attribute_parser/template_validator.py`
- `tests/transceiver/common/prerequisites.py`
- `tests/transceiver/common/health_checks.py`

## Latest Master Alignment
- `docs/testplan/transceiver/` is synchronized with the latest local `sonic-mgmt-master` transceiver test-plan tree.
- `docs/testplan/transceiver/dom_test_plan.md` includes Basic DOM TC4 consistency variation threshold attributes:
  - `tx_power_consistency_variation_threshold`
  - `rx_power_consistency_variation_threshold`
  - `tx_bias_consistency_variation_threshold`
  - `laser_temperature_consistency_variation_threshold`
  - `temperature_consistency_variation_threshold`
  - `voltage_consistency_variation_threshold`
- Top-level transceiver fixtures now use the latest shard-based `attribute_parser` package and shared `common` prerequisite/health-check modules.
- DOM tests opt into `presence_verified`, `gold_fw_verified`, and `links_verified` through `tests/transceiver/dom/conftest.py`.

## New DOM Fixtures
- `_dom_session_prerequisites`: Session autouse DOM category gate that requests shared presence, gold firmware, link-up, and DOM polling-enabled prerequisites before DOM tests run.
- `dom_port_context`: Filters `port_attributes_dict` to ports with non-empty `DOM_ATTRIBUTES`.
- `dom_ports`: DOM-enabled port list sorted by interface prefix + numeric suffix (e.g., `Ethernet0, Ethernet4, Ethernet8, Ethernet12`).
- `dom_operational_suffix`, `dom_lane_num_placeholder`, `dom_expand_operational_fields`, `dom_get_lane_count`: DOM field-expansion helpers exposed to test modules through fixtures.
- `dom_threshold_suffix`, `dom_threshold_field_suffixes`, `dom_threshold_value_tolerance`, `dom_operational_attr_candidates`: DOM threshold validation helpers exposed to test modules through fixtures.
- `dom_operational_fields_by_port`: Expands configured operational attributes to expected sensor fields, including `LANE_NUM` lane expansion.
- `dom_operational_ranges_by_port`: Builds per-port `field -> {attr_name, min, max}` maps for operational-range-aware validations.
- `dom_consistency_variation_rules`: Operational-attribute to variation-threshold mapping used by TC4.
- `dom_consistency_variation_thresholds_by_port`: Parses configured per-port consistency variation threshold attributes from `DOM_ATTRIBUTES`; missing optional variation thresholds use the defaults from `dom_test_plan.md`.
- `dom_threshold_fields_by_port`: Builds threshold key mappings for `TRANSCEIVER_DOM_THRESHOLD`.
- `dom_sensor_by_port` / `dom_threshold_by_port`: Bulk reads from STATE_DB hash tables.
- `dom_db_reader`: Callable fixture for repeated sensor/threshold reads during polling tests.
- `dom_per_test_snapshots`: Autouse per-test fixture that records interface status and DOM sensor snapshots before and after each DOM test, logs per-check link liveness/stability and freshness PASS/FAIL details, then dispatches the checks through the shared health-check framework.
- `parse_dom_numeric` / `parse_dom_update_time`: Robust parsers for numeric fields and `last_update_time`.
- `dom_now_utc`: DUT-time based UTC clock source for freshness checks.
- DOM parser compatibility: supports both standard HGETALL key/value line output and single-line serialized dict output from platform wrappers.
- DOM time parser compatibility: supports `Tue Mar 03 06:31:44 2026` style `last_update_time` values in addition to ISO and epoch formats.

## Shared Utility Modules
- DOM-specific constants, field mapping, threshold mapping, DB hash readers, parsers, and consistency defaults live in `tests/transceiver/dom/conftest.py` and are consumed through fixtures. There is no `tests/transceiver/dom/utils/` package in the current architecture.

## New DOM Test Files
- `tests/transceiver/dom/test_dom_availability.py`
  - TC1: `test_dom_data_availability_verification` validates configured expected fields and freshness; configured field/timestamp gaps fail.
- `tests/transceiver/dom/test_dom_operational_range.py`
  - TC2: `test_dom_sensor_operational_range_validation` validates freshness (`last_update_time`) and operational ranges for configured attributes only; configured field missing/non-numeric fails.
- `tests/transceiver/dom/test_dom_threshold.py`
  - TC3: threshold comparison, completeness, hierarchy validation, operational-vs-warning boundary checks; success logs include per-port checked threshold attribute names.
- `tests/transceiver/dom/test_dom_consistency.py`
  - TC4: polling-based consistency checks with timestamp progression and threshold-driven variation validation using flat consistency threshold attributes (`tx/rx power`, `tx bias`, `laser/module temperature`, `voltage`); absent `consistency_check_poll_count` and `max_update_time_sec` use `dom_test_plan.md` defaults of `3` and `60`; long polling waits log per-group wait/completion progress.
- `tests/transceiver/dom/advanced/test_dom_interface_state.py`
  - Advanced TC1 skeleton (currently explicit skip).
- `tests/transceiver/dom/advanced/test_dom_polling.py`
  - Advanced TC2 skeleton (currently explicit skip).

## New DOM Configuration Shards
- `ansible/files/transceiver/inventory/attributes/dom/dom.json`
  - Category-level DOM defaults for data freshness, polling interval, consistency poll count, and shutdown thresholds.
- `ansible/files/transceiver/inventory/attributes/dom/transceivers/vendors/ACCELIGHT/part_numbers/AGP80SC0CW41002/dom.json`
  - Per-PN operational ranges, threshold ranges, and TC4 consistency variation thresholds for the Accelight module.
- `ansible/files/transceiver/inventory/attributes/eeprom/eeprom.json`
  - Category-level EEPROM defaults migrated from the old flat `attributes/eeprom.json`.
- `ansible/files/transceiver/inventory/attributes/eeprom/transceivers/vendors/ACCELIGHT/part_numbers/AGP80SC0CW41002/eeprom.json`
  - Per-PN EEPROM attributes migrated from the old flat `attributes/eeprom.json`.
- `ansible/files/transceiver/inventory/templates/deployment_templates.json`
  - Updated to validate current `400G_STRAIGHT` BASE and DOM attribute coverage with the shard-based attribute names.
- Removed old architecture remnants:
  - `tests/transceiver/infra/`
  - `ansible/files/transceiver/inventory/attributes/dom.json`
  - `ansible/files/transceiver/inventory/attributes/eeprom/eeprom.json`
  - `ansible/files/transceiver/inventory/attributes/eeprom/transceivers/vendors/ACCELIGHT/part_numbers/AGP80SC0CW41002/eeprom.json`
  - `ansible/files/transceiver/inventory/attributes/backup.json`

## DOM Data/Validation Flow Notes
- Tests are fully attribute-driven and consume only `DOM_ATTRIBUTES` resolved by `tests/transceiver/attribute_parser/attribute_manager.py`.
- DOM config is loaded from shard files under `ansible/files/transceiver/inventory/attributes/dom/`; the legacy flat `attributes/dom.json` has been removed.
- Missing DOM attributes in DOM shards are treated as non-applicable and skipped.
- For attributes configured in DOM shards, required mapped STATE_DB fields must exist and be parseable for the corresponding test case; missing/non-parseable values are failures.
- Local data-flow validation was run with `DutInfoLoader -> AttributeManager -> TemplateValidator` for DUT `str-nexthop_4010-01`; `Ethernet0` and `Ethernet8` produced `DOM_ATTRIBUTES` and both ports were fully compliant with the `400G_STRAIGHT` template.
- TC4 consistency variation thresholds are optional per `dom_test_plan.md`; absent threshold attributes use default limits, while configured invalid threshold values still fail.
- DOM per-test setup now captures interface status before each test and checks admin/oper liveness before and after the test. The liveness and optional post-test stability checks are logged with per-port PASS/FAIL details before being submitted to the shared health-check framework. If the platform exposes a comparable `flap_count`/`last_change` style marker in interface status output, the post-test check verifies it did not advance.
- STATE_DB access uses `sonic-db-cli STATE_DB HGETALL`, with `redis-cli --raw -n 6` fallback.
- DB hash reads support multi-ASIC DUTs by trying `sonic-db-cli -n <frontend-asic-namespace> <DB> HGETALL ...` before falling back to the default namespace.
- DOM polling-state checks read CONFIG_DB `PORT|<port>` through the DOM `read_config_db_hash` helper; missing `dom_polling` is treated as default-enabled, `enabled` passes, `disabled` skips the DOM session prerequisite, and unexpected values skip with a clear diagnostic.
- `conftest.py` now contains DOM-specific fixtures, field-mapping helpers, and DOM DB/parsing helpers so non-DOM `tests/transceiver` files can stay aligned with `upstream/master`.
- DOM failure reporting style now follows EEPROM aggregation style: grouped by port with indented per-field/per-check failure details.
- DOM tests now use EEPROM-like result control flow: `field_failures`/`all_failures` + `has_configured_checks`, without per-port/pass counters such as `port_validated` or `validated_ports`.
- DOM test files include explicit step comments to align code blocks with the corresponding test-plan execution steps.
- Basic DOM TC1-TC4 test files do not declare explicit topology markers; topology selection is left to the shared pytest/testbed infrastructure.
- TC4 DOM consistency polling now batches ports by `(consistency_check_poll_count, max_update_time_sec)` and sleeps once per poll group instead of once per port, preserving per-port attribute-driven polling settings while reducing runtime on multi-port devices.

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
  - EEPROM shard files now provide category defaults and vendor+PN specific EEPROM attributes (`dual_bank_supported`, firmware versions, `cmis_revision`).
  - `prerequisites.json` EEPROM entry now points to an existing function (`test_eeprom_content_verification_via_show_cli`) to avoid missing-function pretest failures.
  - DOM shard files now use parser-compatible vendor key (`ACCELIGHT`) and global timing/freshness thresholds in `defaults` so `DOM_ATTRIBUTES` can resolve correctly for current module part number.
