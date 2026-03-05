import logging
import re
import json
import ast
from datetime import datetime, timezone

import pytest

logger = logging.getLogger(__name__)

DOM_CATEGORY_KEY = "DOM_ATTRIBUTES"
STATE_DB_SENSOR_KEY_TEMPLATE = "TRANSCEIVER_DOM_SENSOR|{}"
STATE_DB_THRESHOLD_KEY_TEMPLATE = "TRANSCEIVER_DOM_THRESHOLD|{}"

OPERATIONAL_SUFFIX = "_operational_range"
THRESHOLD_SUFFIX = "_threshold_range"
LANE_NUM_PLACEHOLDER = "LANE_NUM"

THRESHOLD_FIELD_SUFFIXES = ("lowalarm", "lowwarning", "highwarning", "highalarm")
THRESHOLD_PREFIX_OVERRIDES = {
    "temperature": "temp",
    "voltage": "vcc",
    "tx_power": "txpower",
    "rx_power": "rxpower",
    "tx_bias": "txbias",
    "laser_temperature": "lasertemp",
}

_FLOAT_PATTERN = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_PORT_SUFFIX_PATTERN = re.compile(r"^(.*?)(\d+)$")


def _parse_hgetall_output(stdout_lines):
    lines = [line.strip() for line in stdout_lines if str(line).strip()]
    if not lines:
        return {}

    # Some platforms return HGETALL as a single serialized dict line.
    if len(lines) == 1:
        raw = lines[0]
        if raw in ("{}", "[]"):
            return {}

        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(raw)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}

    if len(lines) % 2 != 0:
        logger.warning("Unexpected HGETALL output line count=%d lines=%s", len(lines), lines)
        return {}

    parsed = {}
    for idx in range(0, len(lines), 2):
        parsed[lines[idx]] = lines[idx + 1]
    return parsed


def _read_state_db_hash(duthost, key):
    commands = [
        'sonic-db-cli STATE_DB HGETALL "{}"'.format(key),
        'redis-cli --raw -n 6 HGETALL "{}"'.format(key),
    ]

    for cmd in commands:
        result = duthost.command(cmd, module_ignore_errors=True)
        if result.get("rc", 1) != 0:
            continue
        parsed = _parse_hgetall_output(result.get("stdout_lines", []))
        if parsed:
            return parsed

    return {}


def _parse_numeric(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.upper() in ("N/A", "NA", "NONE"):
        return None

    match = _FLOAT_PATTERN.search(text)
    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_update_time(value):
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    # Epoch seconds or milliseconds.
    numeric = _parse_numeric(raw)
    if numeric is not None and raw.replace(".", "", 1).isdigit():
        epoch_sec = numeric / 1000.0 if numeric > 1e12 else numeric
        try:
            return datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass

    iso_text = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%a %b %d %H:%M:%S %Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Normalize repeated spaces (e.g., day-of-month formatting differences) and try again.
    normalized = " ".join(raw.split())
    if normalized != raw:
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


def _port_sort_key(port_name):
    text = str(port_name)
    match = _PORT_SUFFIX_PATTERN.match(text)
    if not match:
        return (text, -1, text)
    return (match.group(1), int(match.group(2)), text)


def _get_lane_count(base_attrs):
    media_lane_count = base_attrs.get("media_lane_count")
    if isinstance(media_lane_count, int) and media_lane_count > 0:
        return media_lane_count

    host_lane_count = base_attrs.get("host_lane_count")
    if isinstance(host_lane_count, int) and host_lane_count > 0:
        return host_lane_count

    return 0


def _expand_operational_fields(attr_name, lane_count):
    base_name = attr_name[: -len(OPERATIONAL_SUFFIX)]
    if LANE_NUM_PLACEHOLDER not in base_name:
        return [base_name]

    if lane_count <= 0:
        return []

    return [base_name.replace(LANE_NUM_PLACEHOLDER, str(lane)) for lane in range(1, lane_count + 1)]


def _build_operational_field_range_map(dom_attrs, lane_count):
    field_map = {}
    for attr_name, attr_value in dom_attrs.items():
        if not attr_name.endswith(OPERATIONAL_SUFFIX) or not isinstance(attr_value, dict):
            continue
        for field in _expand_operational_fields(attr_name, lane_count):
            field_map[field] = {
                "attr_name": attr_name,
                "min": attr_value.get("min"),
                "max": attr_value.get("max"),
            }
    return field_map


def _threshold_field_map(attr_name):
    if not attr_name.endswith(THRESHOLD_SUFFIX):
        return {}

    base_name = attr_name[: -len(THRESHOLD_SUFFIX)]
    prefix = THRESHOLD_PREFIX_OVERRIDES.get(base_name, base_name.replace("_", ""))
    return {suffix: "{}{}".format(prefix, suffix) for suffix in THRESHOLD_FIELD_SUFFIXES}


@pytest.fixture(scope="module")
def dom_port_context(port_attributes_dict):
    context = {}
    for port, attrs in port_attributes_dict.items():
        dom_attrs = attrs.get(DOM_CATEGORY_KEY, {})
        if not isinstance(dom_attrs, dict) or not dom_attrs:
            continue
        context[port] = {
            "base": attrs.get("BASE_ATTRIBUTES", {}),
            "dom": dom_attrs,
        }

    if not context:
        pytest.skip("No ports with non-empty DOM_ATTRIBUTES found in port_attributes_dict")

    return context


@pytest.fixture(scope="module")
def dom_ports(dom_port_context):
    return sorted(dom_port_context.keys(), key=_port_sort_key)


@pytest.fixture(scope="module")
def dom_operational_fields_by_port(dom_port_context):
    fields_by_port = {}
    for port, context in dom_port_context.items():
        dom_attrs = context["dom"]
        lane_count = _get_lane_count(context["base"])
        field_range_map = _build_operational_field_range_map(dom_attrs, lane_count)
        fields_by_port[port] = sorted(field_range_map.keys())
    return fields_by_port


@pytest.fixture(scope="module")
def dom_operational_ranges_by_port(dom_port_context):
    ranges_by_port = {}
    for port, context in dom_port_context.items():
        dom_attrs = context["dom"]
        lane_count = _get_lane_count(context["base"])
        ranges_by_port[port] = _build_operational_field_range_map(dom_attrs, lane_count)
    return ranges_by_port


@pytest.fixture(scope="module")
def dom_threshold_fields_by_port(dom_port_context):
    fields_by_port = {}
    for port, context in dom_port_context.items():
        dom_attrs = context["dom"]
        attr_to_fields = {}
        for attr_name, attr_value in dom_attrs.items():
            if not attr_name.endswith(THRESHOLD_SUFFIX) or not isinstance(attr_value, dict):
                continue
            field_map = _threshold_field_map(attr_name)
            if field_map:
                attr_to_fields[attr_name] = field_map
        fields_by_port[port] = attr_to_fields
    return fields_by_port


@pytest.fixture(scope="module")
def dom_sensor_by_port(duthost, dom_ports):
    return {
        port: _read_state_db_hash(duthost, STATE_DB_SENSOR_KEY_TEMPLATE.format(port))
        for port in dom_ports
    }


@pytest.fixture(scope="module")
def dom_threshold_by_port(duthost, dom_ports):
    return {
        port: _read_state_db_hash(duthost, STATE_DB_THRESHOLD_KEY_TEMPLATE.format(port))
        for port in dom_ports
    }


@pytest.fixture(scope="module")
def dom_db_reader(duthost):
    def _read_sensor(port):
        return _read_state_db_hash(duthost, STATE_DB_SENSOR_KEY_TEMPLATE.format(port))

    def _read_threshold(port):
        return _read_state_db_hash(duthost, STATE_DB_THRESHOLD_KEY_TEMPLATE.format(port))

    return {
        "sensor": _read_sensor,
        "threshold": _read_threshold,
    }


@pytest.fixture(scope="module")
def parse_dom_numeric():
    return _parse_numeric


@pytest.fixture(scope="module")
def parse_dom_update_time():
    return _parse_update_time


@pytest.fixture(scope="module")
def dom_now_utc(duthost):
    def _now():
        result = duthost.command("date +%s", module_ignore_errors=True)
        if result.get("rc", 1) == 0:
            text = result.get("stdout", "").strip()
            if text.isdigit():
                return datetime.fromtimestamp(int(text), tz=timezone.utc)
        return datetime.now(tz=timezone.utc)
    return _now
