"""Small standard-library executor for the packaged JSON Schema contract subset."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class SchemaValidationError(ValueError):
    """A runtime value violates its packaged schema."""


_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def _validate(value: Any, schema: dict[str, Any], path: str) -> None:
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_matches_type(value, item) for item in expected):
            raise SchemaValidationError(f"{path} type must be one of {expected}")
    elif isinstance(expected, str) and not _matches_type(value, expected):
        raise SchemaValidationError(f"{path} type must be {expected}")
    if "const" in schema and value != schema["const"]:
        raise SchemaValidationError(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path} must be one of {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise SchemaValidationError(f"{path} is too short")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise SchemaValidationError(f"{path} does not match required pattern")
    if isinstance(value, int) and not isinstance(value, bool) and value < schema.get("minimum", value):
        raise SchemaValidationError(f"{path} is below minimum")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            raise SchemaValidationError(f"{path} items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [item for item in required if item not in value]
        if missing:
            raise SchemaValidationError(f"{path} missing required field {missing[0]}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise SchemaValidationError(f"{path} has unsupported field {extras[0]}")
        for name, child in properties.items():
            if name in value:
                _validate(value[name], child, f"{path}.{name}")


class SchemaRuntime:
    def __init__(self, skill_root: Path):
        root = skill_root.resolve()
        installed = root / "references" / "schemas"
        self.schema_root = installed if installed.is_dir() else root / "schemas"

    def validate(self, schema_name: str, value: Any) -> None:
        path = self.schema_root / schema_name
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SchemaValidationError(f"cannot load packaged schema {schema_name}") from error
        _validate(value, schema, schema_name.removesuffix(".schema.json"))
