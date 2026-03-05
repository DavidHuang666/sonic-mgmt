import pytest

pytestmark = [
    pytest.mark.topology("ptp-256", "m0"),
]

THRESHOLD_SUFFIX = "_threshold_range"
VALUE_TOLERANCE = 0.01


# Map attribute naming to STATE_DB threshold key prefixes.
THRESHOLD_PREFIX_OVERRIDES = {
    "temperature": "temp",
    "voltage": "vcc",
    "tx_power": "txpower",
    "rx_power": "rxpower",
    "tx_bias": "txbias",
    "laser_temperature": "lasertemp",
}


EXPECTED_THRESHOLD_KEYS = ("lowalarm", "lowwarning", "highwarning", "highalarm")

# Threshold attribute base -> related operational range attribute(s).
# Some threshold attributes map to lane-based operational attributes.
THRESHOLD_TO_OPERATIONAL_ATTR_CANDIDATES = {
    "tx_bias": ("txLANE_NUMbias_operational_range", "tx_bias_operational_range"),
    "tx_power": ("txLANE_NUMpower_operational_range", "tx_power_operational_range"),
    "rx_power": ("rxLANE_NUMpower_operational_range", "rx_power_operational_range"),
}


def _build_threshold_field_map(attr_name):
    base_name = attr_name[: -len(THRESHOLD_SUFFIX)]
    prefix = THRESHOLD_PREFIX_OVERRIDES.get(base_name, base_name.replace("_", ""))
    return {key: "{}{}".format(prefix, key) for key in EXPECTED_THRESHOLD_KEYS}


def _operational_attr_candidates(base_name):
    default = ("{}_operational_range".format(base_name),)
    return THRESHOLD_TO_OPERATIONAL_ATTR_CANDIDATES.get(base_name, default)


def test_dom_threshold_validation(
    dom_ports,
    dom_port_context,
    dom_threshold_by_port,
    parse_dom_numeric,
):
    """TC3: Validate threshold values, hierarchy, and operational-vs-threshold relationship."""
    # Step 0: Initialize per-test aggregation.
    all_failures = []
    has_configured_checks = False

    for port in dom_ports:
        # Step 1: Resolve per-port DOM attributes and threshold DB snapshot.
        dom_attrs = dom_port_context[port]["dom"]
        threshold_data = dom_threshold_by_port.get(port, {})
        field_failures = []

        for attr_name, attr_value in dom_attrs.items():
            if not attr_name.endswith(THRESHOLD_SUFFIX) or not isinstance(attr_value, dict):
                continue

            has_configured_checks = True

            # Step 2: Validate threshold attribute completeness in configuration.
            if not all(key in attr_value for key in EXPECTED_THRESHOLD_KEYS):
                field_failures.append(
                    "{} missing required keys {}; cannot validate threshold range".format(
                        attr_name, EXPECTED_THRESHOLD_KEYS
                    )
                )
                continue

            # Step 3: Validate threshold table/fields are present and parseable in STATE_DB.
            if not threshold_data:
                field_failures.append("{} threshold table missing in STATE_DB".format(attr_name))
                continue

            field_map = _build_threshold_field_map(attr_name)
            parsed_actual = {}
            parse_failed = False
            for logical_key, db_field in field_map.items():
                numeric = parse_dom_numeric(threshold_data.get(db_field))
                if numeric is None:
                    field_failures.append(
                        "{} threshold field {} missing/non-numeric in STATE_DB".format(attr_name, db_field)
                    )
                    parse_failed = True
                    break
                parsed_actual[logical_key] = numeric

            if parse_failed:
                continue

            # Step 4: Compare configured threshold values against STATE_DB values.
            for logical_key in EXPECTED_THRESHOLD_KEYS:
                expected = float(attr_value[logical_key])
                actual = parsed_actual[logical_key]
                if abs(actual - expected) > VALUE_TOLERANCE:
                    field_failures.append(
                        "{} expected {}={}, got {}".format(attr_name, logical_key, expected, actual)
                    )

            # Step 5: Validate threshold hierarchy ordering.
            if not (
                parsed_actual["lowalarm"]
                < parsed_actual["lowwarning"]
                < parsed_actual["highwarning"]
                < parsed_actual["highalarm"]
            ):
                field_failures.append(
                    "{} invalid hierarchy lowalarm < lowwarning < highwarning < highalarm violated".format(attr_name)
                )

            # Step 6: Validate operational range is inside warning window when both are configured.
            base_name = attr_name[: -len(THRESHOLD_SUFFIX)]
            for operational_attr in _operational_attr_candidates(base_name):
                operational_range = dom_attrs.get(operational_attr)
                if not isinstance(operational_range, dict):
                    continue

                op_min = operational_range.get("min")
                op_max = operational_range.get("max")
                if op_min is None or op_max is None:
                    field_failures.append(
                        "{} present but missing min/max in DOM_ATTRIBUTES".format(operational_attr)
                    )
                    continue

                if not (
                    parsed_actual["lowwarning"] < float(op_min)
                    and float(op_max) < parsed_actual["highwarning"]
                ):
                    field_failures.append(
                        "{} operational range [{}, {}] is not within warning bounds ({}, {})".format(
                            operational_attr,
                            op_min,
                            op_max,
                            parsed_actual["lowwarning"],
                            parsed_actual["highwarning"],
                        )
                    )

        if field_failures:
            all_failures.append("{}:\n  {}".format(port, "\n  ".join(field_failures)))

    # Step 7: Final decision for skip/fail.
    if not has_configured_checks:
        pytest.skip("No *_threshold_range attributes configured for DOM threshold validation")

    if all_failures:
        pytest.fail("DOM threshold validation failures:\n" + "\n".join(all_failures))
