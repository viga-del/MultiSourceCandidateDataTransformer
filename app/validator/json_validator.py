# app/validator/json_validator.py
#
# Module 12: Schema Validation
#
# After all processing is done, we validate the final output JSON
# against a JSON Schema. This catches:
#   - Missing required fields
#   - Wrong data types (e.g. confidence as a string instead of number)
#   - Invalid formats (e.g. email without @)
#   - Out-of-range values (e.g. confidence > 1.0)
#
# If validation fails, we return a list of errors.
# Depending on configuration, we can either:
#   a) Return the errors to the caller (strict mode)
#   b) Log them and continue (lenient mode)

import json
import os
from typing import Dict, Any, Tuple, List
from jsonschema import validate, ValidationError, SchemaError
# jsonschema is the library that validates a dict against a JSON Schema.
# validate() raises ValidationError if the data doesn't match the schema.

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Path to the schema file we created
_SCHEMA_PATH = os.path.join("app", "validator", "schema.json")

# Load the schema once at module import time (not on every validation call)
# This is more efficient — we don't re-read the file for each candidate
try:
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        _SCHEMA = json.load(f)
    logger.debug("JSON Schema loaded successfully")
except FileNotFoundError:
    _SCHEMA = {}
    logger.error(f"Schema file not found: {_SCHEMA_PATH}")
except json.JSONDecodeError as e:
    _SCHEMA = {}
    logger.error(f"Invalid JSON in schema file: {e}")


def validate_candidate(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a candidate profile dict against the JSON Schema.

    Parameters:
        data (Dict): The final projected candidate profile dict

    Returns:
        Tuple[bool, List[str]]:
            - bool: True if valid, False if there are errors
            - List[str]: List of error messages (empty list if valid)

    Example:
        is_valid, errors = validate_candidate(output_dict)
        if not is_valid:
            for error in errors:
                print(error)
    """
    if not _SCHEMA:
        logger.warning("No schema available — skipping validation")
        return True, []

    errors = []

    try:
        # validate() checks the data against the schema.
        # If valid, it returns None silently.
        # If invalid, it raises ValidationError with details.
        validate(instance=data, schema=_SCHEMA)
        logger.info("Schema validation passed")
        return True, []

    except ValidationError as e:
        # e.message contains the human-readable error
        # e.path contains the JSON path to the invalid field (e.g. ["skills", 0, "confidence"])
        path = " → ".join(str(p) for p in e.path) if e.path else "root"
        error_msg = f"Validation error at '{path}': {e.message}"
        errors.append(error_msg)
        logger.warning(f"Validation failed: {error_msg}")

        # For detailed errors (all errors, not just first), use Draft7Validator
        # But for simplicity we catch the first error here
        return False, errors

    except SchemaError as e:
        # This means the schema itself is invalid — developer error
        logger.error(f"Schema is invalid: {e.message}")
        return False, [f"Schema error: {e.message}"]


def validate_and_collect_all_errors(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate and collect ALL validation errors (not just the first one).

    jsonschema's default validate() stops at the first error.
    This function uses Draft7Validator to collect every error.

    Parameters:
        data (Dict): The candidate profile dict

    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_all_errors)
    """
    from jsonschema import Draft7Validator

    if not _SCHEMA:
        return True, []

    validator = Draft7Validator(_SCHEMA)

    # iter_errors() yields all errors without raising exceptions
    all_errors = list(validator.iter_errors(data))

    if not all_errors:
        logger.info("Schema validation passed — no errors found")
        return True, []

    error_messages = []
    for error in all_errors:
        path = " → ".join(str(p) for p in error.path) if error.path else "root"
        error_messages.append(f"'{path}': {error.message}")

    logger.warning(f"Validation found {len(error_messages)} error(s)")
    for msg in error_messages:
        logger.warning(f"  • {msg}")

    return False, error_messages


def validate_custom_projection(data: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Lightweight structural validation for output produced by a *runtime*
    projection config (config_projection_engine.project_with_config).

    Unlike validate_and_collect_all_errors(), which checks against the
    fixed default schema.json, this checks the output against whatever
    shape the config itself declared (required fields + basic types).

    Parameters:
        data   (Dict): The projected output to validate
        config (Dict): The same config used to produce `data`

    Returns:
        (is_valid, errors)
    """
    errors: List[str] = []
    type_checks = {
        "string":   lambda v: isinstance(v, str),
        "number":   lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean":  lambda v: isinstance(v, bool),
        "string[]": lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
        "object":   lambda v: isinstance(v, dict),
    }

    for field_cfg in config.get("fields", []):
        path = field_cfg["path"]
        required = field_cfg.get("required", False)
        expected_type = field_cfg.get("type")

        if path not in data:
            if required and config.get("on_missing") != "omit":
                errors.append(f"Required field '{path}' is missing from output")
            continue

        value = data[path]
        if value is None:
            if required and config.get("on_missing") not in ("null",):
                errors.append(f"Required field '{path}' is null")
            continue

        if expected_type and expected_type in type_checks:
            if not type_checks[expected_type](value):
                errors.append(f"Field '{path}' expected type '{expected_type}', got {type(value).__name__}")

    return (len(errors) == 0, errors)
