# AGENTS.md — sonic-mgmt / Transceiver DOM Tests

## Scope & Goal
You are working in the `sonic-mgmt` repository.
Current goal: implement and extend transceiver DOM tests under:
- tests/transceiver/dom/

The implementation MUST strictly follow the architecture and constraints defined in:
- docs/testplan/transceiver/dom_test_plan.md
- docs/testplan/transceiver/test_plan.md
- docs/testplan/transceiver/system_test_plan.md
- docs/testplan/transceiver/eeprom_test_plan.md
- docs/testplan/transceiver/diagrams/

## Mandatory Reading (before any implementation)
Before writing or modifying any code, you MUST read:
1) docs/ai/CONTEXT.md
2) docs/ai/DECISIONS.md
3) docs/testplan/transceiver/diagrams/README.md
4) docs/testplan/transceiver/diagrams/file_organization.md
5) docs/testplan/transceiver/diagrams/data_flow.md
6) docs/testplan/transceiver/diagrams/validation_flow.md
7) docs/testplan/transceiver/dom_test_plan.md
8) docs/testplan/transceiver/test_plan.md
9) docs/testplan/transceiver/system_test_plan.md
10) docs/testplan/transceiver/eeprom_test_plan.md

## Allowed Modifications
You are allowed to modify or create files ONLY under:
- tests/transceiver/dom/**
- docs/ai/**
- tests/transceiver/infra/**
- 以及其他为了实现dom_test_plan.md 中所需要修改的目录

You may READ (but should minimize changes to):
- tests/transceiver/eeprom/**
- tests/transceiver/infra/**
- tests/transceiver/transceiver_test_base.py
- tests/transceiver/conftest.py
- tests/platform_tests/*

Do NOT modify unrelated test areas.

## Architectural Rules
- Directory structure MUST comply with diagrams/file_organization.md
- Data loading and validation MUST follow diagrams/data_flow.md and validation_flow.md
- All DOM tests MUST be configuration-driven
- Missing or unsupported attributes MUST be handled according to dom_test_plan.md (skip, not fail)
- Reuse existing infra utilities whenever possible

## Implementation Process
1) Start with minimal, runnable test skeletons
2) Introduce fixtures in conftest.py before adding test logic
3) Keep each test file focused on a single validation category
4) Avoid hardcoding platform-specific values

## Verification Requirement
- Every change MUST be validated locally using pytest
- Always provide the exact pytest command for manual execution
- Never assume tests pass without execution

## Documentation Update
After completing a task:
- Update docs/ai/INDEX.md with:
  - new fixtures
  - new test files
  - key data/validation flow notes




