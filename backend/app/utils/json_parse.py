import json
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
