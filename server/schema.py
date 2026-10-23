"""A small JSON Schema checker for the structured answers a model returns.

The assistant tells a model the shape it must answer in (`INTENT_SCHEMA`),
and a local model is held to it by Ollama's `format`; a hosted provider's
JSON mode only promises an object. The server therefore checks the shape
itself before acting on it (assessment G5). The subset covers what the
project's schemas use: `type`, `properties`, `required`,
`additionalProperties`, `const`, `enum`, `minLength`, `items`, `oneOf`
and `anyOf`. Standard library only (ADR 0027).
"""

TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "integer": int, "number": (int, float), "null": type(None),
}


def problems(schema, value, path="$"):
    """Every way `value` fails `schema`, as "path: reason" strings."""
    out = []
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: must be one of {schema['enum']}")
    expected = schema.get("type")
    if expected is not None:
        kinds = expected if isinstance(expected, list) else [expected]
        ok = any(isinstance(value, TYPES[k]) and not (k in ("integer", "number")
                                                       and isinstance(value, bool))
                 for k in kinds)
        if not ok:
            out.append(f"{path}: must be {' or '.join(kinds)}")
            return out
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        out.append(f"{path}: must be at least {schema['minLength']} character(s)")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}.{key}: required")
        for key, item in value.items():
            if key in properties:
                out += problems(properties[key], item, f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}.{key}: not allowed")
            elif isinstance(schema.get("additionalProperties"), dict):
                out += problems(schema["additionalProperties"], item, f"{path}.{key}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            out += problems(schema["items"], item, f"{path}[{index}]")
        if len(value) > schema.get("maxItems", len(value)):
            out.append(f"{path}: at most {schema['maxItems']} item(s)")
    for keyword in ("oneOf", "anyOf"):
        if keyword in schema:
            passing = [s for s in schema[keyword] if not problems(s, value, path)]
            if not passing or (keyword == "oneOf" and len(passing) != 1):
                out.append(f"{path}: matches {len(passing)} of the {keyword} branches")
    return out


def valid(schema, value):
    return not problems(schema, value)
