"""A model's answer checked against its JSON schema in code (spec §7.2 step 1). A strict schema on the request is not
proof: a wrong type, an enum value outside the list, or a missing or unexpected field becomes a rejection reason,
never a crash further on. Covers the schema features prompts/schemas use: type, enum, required, properties,
additionalProperties and items.
"""

from __future__ import annotations

from typing import Any

TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}
ARTICLE = {"array": "an", "object": "an", "integer": "an"}


def _is(value: Any, name: str) -> bool:
    if name in ("number", "integer") and isinstance(value, bool):
        return False  # a bool is an int in Python, never a number in JSON
    return isinstance(value, TYPES.get(name, ()))


def schema_errors(value: Any, schema: dict, path: str = "") -> list[str]:
    """Every way `value` departs from `schema`, each as "<path>: <what>"; empty when it fits."""
    where = path or "answer"
    names = schema.get("type")
    if names is not None:
        allowed = [names] if isinstance(names, str) else list(names)
        if not any(_is(value, name) for name in allowed):
            wanted = " or ".join(f"{ARTICLE.get(n, 'a')} {n}" for n in allowed)
            return [f"{where}: expected {wanted}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{where}: {value!r} is not one of {', '.join(map(str, schema['enum']))}"]
    errors: list[str] = []
    if isinstance(value, dict):
        prefix = f"{path}: " if path else ""
        properties = schema.get("properties", {})
        errors += [f"{prefix}missing field: {name}" for name in schema.get("required", []) if name not in value]
        if schema.get("additionalProperties") is False:
            errors += [f"{prefix}unexpected field: {name}" for name in value if name not in properties]
        for name, sub in properties.items():
            if name in value:
                errors += schema_errors(value[name], sub, f"{path}.{name}" if path else name)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors += schema_errors(item, schema["items"], f"{where}[{i}]")
    return errors
