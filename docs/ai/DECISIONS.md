
# DECISIONS — Transceiver DOM Tests

## 1. Source of Truth Priority
For DOM implementation and behavior, resolve conflicts in this strict order:
1. `docs/testplan/transceiver/**/*.md`
2. `docs/testplan/transceiver/diagrams/**/*.md`
3. `docs/ai/DECISIONS.md` and `docs/ai/CONTEXT.md`
4. Existing code behavior

If implementation conflicts with test plan/design docs, implementation must be changed to match design docs.

## 2. Architecture First
All DOM test code MUST comply with the architecture described in:
- docs/testplan/transceiver/diagrams/

If implementation conflicts with diagrams, diagrams win.

## 3. Configuration-Driven Testing
- No hardcoded thresholds or limits
- All validations must originate from configuration / inventory data
- JSON definitions are the source of truth

## 4. Missing/Unsupported Handling
- If a DOM attribute is absent from `dom.json`, it is non-applicable and should be skipped.
- If a DOM attribute is present in `dom.json`, required mapped fields must be present and parseable in STATE_DB for that test case.
- For configured attributes, missing/unparseable required STATE_DB fields are test failures (not skips).
- Skip is allowed only for truly non-applicable checks (for example: attribute not configured).

## 5. Test File Responsibilities
- One test file = one validation theme
  (e.g. availability, freshness, threshold, range)
- Avoid mixing unrelated validations in the same file

## 6. Fixture Design
- Shared setup logic belongs in conftest.py
- Fixtures should expose processed, ready-to-validate data
- Tests should not perform raw parsing logic

## 7. Reuse Over Reinvention
- Prefer existing utilities in tests/transceiver/infra/
- Do not duplicate attribute parsing or validation logic

## 8. Verification Is Mandatory
- Every change must be verified with pytest locally
- Tests are considered incomplete until executed

## 9. Knowledge Preservation
- Every meaningful implementation must update docs/ai/INDEX.md
- INDEX.md is the authoritative map of how DOM tests work
