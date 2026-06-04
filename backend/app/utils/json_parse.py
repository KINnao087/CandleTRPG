import json
from dataclasses import is_dataclass, asdict
from typing import Any


def get_json_value(data: str, key: str) -> Any:
    parsed = json.loads(data)

    current: Any = parsed
    for part in key.split("."):
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(key)

    return current

def normalize_to_json(value: Any) -> Any:
    if is_dataclass(value):
        return normalize_to_json(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): normalize_to_json(value[key])
            for key in sorted(value.keys(), key=lambda item: str(item))
        }

    if isinstance(value, (list, tuple)):
        return [normalize_to_json(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)

def stable_json_dumps(value: Any) -> str:
    return json.dumps(
        normalize_to_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
