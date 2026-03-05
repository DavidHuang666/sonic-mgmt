# CONTEXT — Transceiver DOM Test Development

## Repository
- Project: sonic-mgmt
- Focus area: Transceiver testing
- Current work branch:
  eeprom-and-system-test-plan-doc-update-transceiver-attribute-infra-dom-test

## Objective
Implement a new DOM (Digital Optical Monitoring) test framework under:
- tests/transceiver/dom/
- 以及其他的必须的路径 及其路径下的py等类型文件

This framework validates DOM functionality for optical transceivers,
based on documented test plans and configuration-driven attributes.

## Specification Sources
Authoritative requirements come from:
- docs/testplan/transceiver/test_plan.md
- docs/testplan/transceiver/dom_test_plan.md
- docs/testplan/transceiver/diagrams/
- ansible/files/transceiver/inventory/(只是一些模块配置例子)

The diagrams directory defines:
- required file organization
- data flow from inventory/config → validation
- validation sequencing and skip logic

## Configuration & Inventory Model
DOM tests are configuration-driven and rely on:
- JSON attribute definitions (examples in docs/testplan/transceiver/examples/)
- DUT-specific inventory data
- Attribute normalization and prerequisite checks

Existing infra modules under tests/transceiver/infra/ provide:
- attribute parsing
- configuration loading
- validation helpers

## Reference Implementations
Existing tests to study and reuse patterns from:
- tests/transceiver/*
- 实现架构重点参考 tests/transceiver/eeprom/test_eeprom_basic.py 以及其内部实现的调用链
- tests/platform_tests
- tests/ 目录下一些公用的Py
- ansible/ 目录下一些公用的py

## Execution Model
Tests are executed locally using pytest (typically inside a docker-based
sonic-mgmt environment). SSH access to DUTs may be used indirectly
through existing test infrastructure.

Exact docker/pytest commands will be finalized and documented later.
