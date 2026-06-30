# app/projection/config_projection_engine.py
#
# Runtime-configurable projection layer ("the required twist").
#
# The default projection_engine.py just includes/excludes whole top-level
# fields. This module goes further: given an arbitrary JSON config it can,
# WITHOUT touching any code:
#   - select a subset of fields
#   - rename / remap a field from a canonical path (the "from" key)
#   - apply per-field normalization (E164 phones, canonical skill names)
#   - toggle provenance / confidence on or off
#   - decide what happens when a value is missing: null | omit | error
#
# This keeps a clean separation between the internal canonical record
# (CandidateProfile -> full serialized dict) and this projection layer.

import re
from typing import Dict, Any, List, Optional

from app.projection.projection_engine import _serialize_profile
from app.normalizers.phone_normalizer import normalize_phone
from app.normalizers.skill_normalizer import normalize_skill as normalize_skill_name
from app.utils.logger import get_logger

logger = get_logger(__name__)

_PATH_TOKEN = re.compile(r"([^\[\].]+)|\[(\d*)\]")


class ProjectionConfigError(ValueError):
    """Raised when a runtime projection config is malformed or a
    required field is missing and on_missing == 'error'."""


def _tokenize(path: str) -> List[Any]:
    """
    Turn a dotted/bracket path like "skills[].name" or "emails[0]"
    into a list of tokens: strings for dict keys, "*" for "take every
    item in the list", and ints for a specific index.
    """
    tokens: List[Any] = []
    for key, idx in _PATH_TOKEN.findall(path):
        if key != "":
            tokens.append(key)
        elif idx == "":
            tokens.append("*")
        else:
            tokens.append(int(idx))
    return tokens


def _resolve(data: Any, tokens: List[Any]) -> Any:
    """Walk `data` following `tokens`, returning the resolved value (or None)."""
    if not tokens:
        return data
    if data is None:
        return None

    token, rest = tokens[0], tokens[1:]

    if token == "*":
        if not isinstance(data, list):
            return None
        return [_resolve(item, rest) for item in data]

    if isinstance(token, int):
        if not isinstance(data, list) or token >= len(data):
            return None
        return _resolve(data[token], rest)

    # dict key
    if isinstance(data, dict):
        return _resolve(data.get(token), rest)

    return None


_NORMALIZERS = {
    "e164": lambda v: normalize_phone(v) if v else v,
    "canonical": lambda v: normalize_skill_name(v) if v else v,
    "lower": lambda v: v.lower() if isinstance(v, str) else v,
    "upper": lambda v: v.upper() if isinstance(v, str) else v,
    "none": lambda v: v,
}


def _apply_normalize(value: Any, normalize: Optional[str]) -> Any:
    if not normalize:
        return value
    fn = _NORMALIZERS.get(normalize.lower())
    if not fn:
        logger.warning(f"Unknown normalize type '{normalize}' — leaving value as-is")
        return value
    if isinstance(value, list):
        return [fn(v) for v in value]
    return fn(value)


def project_with_config(profile, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Project a CandidateProfile into a custom output shape driven entirely
    by a runtime JSON config — no code changes required.

    Config shape:
        {
          "fields": [
            {"path": "full_name", "type": "string", "required": true},
            {"path": "primary_email", "from": "emails[0]", "type": "string", "required": true},
            {"path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164"},
            {"path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical"}
          ],
          "include_confidence": true,
          "include_provenance": false,
          "on_missing": "null"   # "null" | "omit" | "error"
        }

    Returns:
        Dict: the projected output, ready for json.dumps()
    """
    if "fields" not in config or not isinstance(config["fields"], list):
        raise ProjectionConfigError("Config must contain a 'fields' list")

    on_missing = config.get("on_missing", "null")
    if on_missing not in ("null", "omit", "error"):
        raise ProjectionConfigError(f"Invalid on_missing value: {on_missing}")

    full_dict = _serialize_profile(profile)
    output: Dict[str, Any] = {}

    for field_cfg in config["fields"]:
        out_path = field_cfg.get("path")
        if not out_path:
            raise ProjectionConfigError(f"Field config missing 'path': {field_cfg}")

        from_path = field_cfg.get("from", out_path)
        tokens = _tokenize(from_path)
        value = _resolve(full_dict, tokens)
        value = _apply_normalize(value, field_cfg.get("normalize"))

        is_missing = value is None or value == [] or value == ""
        required = field_cfg.get("required", False)

        if is_missing:
            if on_missing == "error" or (required and on_missing != "omit"):
                raise ProjectionConfigError(
                    f"Required field '{out_path}' (from '{from_path}') is missing"
                )
            if on_missing == "omit":
                continue
            value = None  # on_missing == "null"

        output[out_path] = value

    if config.get("include_confidence", False):
        output["overall_confidence"] = full_dict.get("overall_confidence")

    if config.get("include_provenance", False):
        output["provenance"] = full_dict.get("provenance")

    logger.info(f"Custom projection complete — {len(output)} field(s) in output")
    return output
