import time

import pytest

pytestmark = [
    pytest.mark.topology("ptp-256", "m0"),
]


def test_dom_data_consistency_verification(
    dom_ports,
    dom_port_context,
    dom_operational_fields_by_port,
    dom_operational_ranges_by_port,
    dom_consistency_variation_thresholds_by_port,
    dom_consistency_variation_rules,
    dom_db_reader,
    parse_dom_numeric,
    parse_dom_update_time,
):
    """TC4: Validate DOM data consistency across polling cycles."""
    all_failures = []
    has_configured_checks = bool(dom_ports)

    read_sensor = dom_db_reader["sensor"]

    for port in dom_ports:
        # Step 1: Resolve per-port polling configuration and expected DOM fields.
        dom_attrs = dom_port_context[port]["dom"]
        expected_fields = dom_operational_fields_by_port.get(port, [])
        field_ranges = dom_operational_ranges_by_port.get(port, {})
        variation_config = dom_consistency_variation_thresholds_by_port.get(port, {})
        field_failures = []
        invalid_range_attrs = set()
        invalid_variation_rule_attrs = set()

        for error in variation_config.get("errors", []):
            field_failures.append(error)

        variation_thresholds = variation_config.get("thresholds", {})

        poll_count_raw = dom_attrs.get("consistency_check_poll_count")
        poll_interval_raw = dom_attrs.get("max_update_time_sec")

        if "consistency_check_poll_count" not in dom_attrs:
            field_failures.append(
                "missing required DOM attribute consistency_check_poll_count for consistency validation"
            )
        if "max_update_time_sec" not in dom_attrs:
            field_failures.append("missing required DOM attribute max_update_time_sec for consistency validation")

        if field_failures:
            all_failures.append("{}:\n  {}".format(port, "\n  ".join(field_failures)))
            continue

        poll_count = None
        try:
            poll_count = int(poll_count_raw)
        except (TypeError, ValueError):
            field_failures.append(
                "invalid consistency_check_poll_count={} in DOM_ATTRIBUTES".format(poll_count_raw)
            )
        if poll_count is not None and poll_count < 2:
            field_failures.append(
                "invalid consistency_check_poll_count={} (must be >= 2)".format(poll_count)
            )

        poll_interval_sec = None
        try:
            poll_interval_sec = int(poll_interval_raw)
        except (TypeError, ValueError):
            field_failures.append("invalid max_update_time_sec={} in DOM_ATTRIBUTES".format(poll_interval_raw))
        if poll_interval_sec is not None and poll_interval_sec < 1:
            field_failures.append("invalid max_update_time_sec={} (must be >= 1)".format(poll_interval_sec))

        if field_failures:
            all_failures.append("{}:\n  {}".format(port, "\n  ".join(field_failures)))
            continue

        # Step 2: Capture baseline DOM sensor snapshot.
        previous = read_sensor(port)
        if not previous:
            field_failures.append("initial DOM sensor read missing")
            all_failures.append("{}:\n  {}".format(port, "\n  ".join(field_failures)))
            continue

        previous_ts = parse_dom_update_time(previous.get("last_update_time"))
        if previous_ts is None:
            field_failures.append("baseline last_update_time missing or unparsable")

        # Step 3/4: Poll repeatedly, validate timestamp progression and reasonable sensor behavior.
        for poll_idx in range(1, poll_count):
            time.sleep(poll_interval_sec)
            current = read_sensor(port)
            if not current:
                field_failures.append("DOM sensor read failed during consistency polling")
                break

            curr_ts = parse_dom_update_time(current.get("last_update_time"))
            if curr_ts is None:
                field_failures.append("last_update_time missing or unparsable during consistency polling")
            elif previous_ts is not None:
                if curr_ts <= previous_ts:
                    field_failures.append(
                        "last_update_time did not advance (prev={}, curr={})".format(
                            previous_ts.isoformat(), curr_ts.isoformat()
                        )
                    )

            for field in expected_fields:
                prev_val = parse_dom_numeric(previous.get(field))
                curr_val = parse_dom_numeric(current.get(field))
                if prev_val is None or curr_val is None:
                    field_failures.append("{} missing/non-numeric value during consistency polling".format(field))
                    continue

                range_info = field_ranges.get(field)
                if range_info is None:
                    continue

                attr_name = range_info["attr_name"]
                min_cfg = parse_dom_numeric(range_info.get("min"))
                max_cfg = parse_dom_numeric(range_info.get("max"))
                if min_cfg is None or max_cfg is None:
                    if attr_name not in invalid_range_attrs:
                        field_failures.append(
                            "{} missing/non-numeric min or max in DOM_ATTRIBUTES".format(attr_name)
                        )
                        invalid_range_attrs.add(attr_name)
                    continue

                if min_cfg > max_cfg:
                    if attr_name not in invalid_range_attrs:
                        field_failures.append(
                            "{} has invalid range with min={} > max={}".format(attr_name, min_cfg, max_cfg)
                        )
                        invalid_range_attrs.add(attr_name)
                    continue

                if not min_cfg <= curr_val <= max_cfg:
                    field_failures.append(
                        "{} value {} out of configured operational range [{}, {}] during poll {}".format(
                            field, curr_val, min_cfg, max_cfg, poll_idx + 1
                        )
                    )

                variation_rule = dom_consistency_variation_rules.get(attr_name)
                if variation_rule is None:
                    if attr_name not in invalid_variation_rule_attrs:
                        field_failures.append(
                            "{} has no mapped consistency variation threshold rule".format(attr_name)
                        )
                        invalid_variation_rule_attrs.add(attr_name)
                    continue

                threshold_attr, mode = variation_rule
                threshold_value = variation_thresholds.get(threshold_attr)
                if threshold_value is None:
                    if threshold_attr not in invalid_variation_rule_attrs:
                        field_failures.append(
                            "{} missing parsed variation threshold {}".format(attr_name, threshold_attr)
                        )
                        invalid_variation_rule_attrs.add(threshold_attr)
                    continue

                if mode == "abs":
                    allowed_delta = threshold_value
                elif mode == "pct":
                    allowed_delta = abs(prev_val) * threshold_value / 100.0
                else:
                    if attr_name not in invalid_variation_rule_attrs:
                        field_failures.append("{} has invalid consistency variation mode {}".format(attr_name, mode))
                        invalid_variation_rule_attrs.add(attr_name)
                    continue

                delta = abs(curr_val - prev_val)
                if delta > allowed_delta:
                    field_failures.append(
                        "{} unreasonable change between polls (prev={}, curr={}, delta={}, "
                        "allowed_delta={}, threshold_attr={})".format(
                            field, prev_val, curr_val, delta, allowed_delta, threshold_attr
                        )
                    )

            previous = current
            if curr_ts is not None:
                previous_ts = curr_ts

        if field_failures:
            all_failures.append("{}:\n  {}".format(port, "\n  ".join(field_failures)))

    # Step 5: Final decision for skip/fail.
    if not has_configured_checks:
        pytest.skip("No DOM ports configured for consistency validation")

    if all_failures:
        pytest.fail("DOM consistency validation failures:\n" + "\n".join(all_failures))
