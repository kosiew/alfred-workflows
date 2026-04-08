import json
import os
import sys
from typing import Iterable


def parse_query(raw_query: str) -> list[int]:
    return [value for part in raw_query.split() if (value := _parse_index(part)) is not None]


def _parse_index(raw: str) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None

    return value if 1 <= value <= 20 else None


def read_clipboard_entries(count: int = 20, prefix: str = "cb") -> list[str]:
    return [os.getenv(f"{prefix}{i}", "") for i in range(1, count + 1)]


def build_items(entries: list[str], selected_indices: Iterable[int]) -> list[dict[str, object]]:
    selected_set = set(selected_indices)

    return [
        {
            "title": value,
            "icon": {
                "path": f"icons/icon-picked-{index}.png" if index in selected_set else f"icons/icon-{index}.png"
            },
        }
        for index, value in enumerate(entries, start=1)
    ]


def build_clipboard_variable(entries: list[str], selection: list[int]) -> str:
    if not selection:
        return "\n".join(entries)

    return "\n".join(entries[index - 1] for index in selection)


def main() -> None:
    query_raw = sys.argv[1] if len(sys.argv) > 1 else ""
    selection = parse_query(query_raw)

    entries = read_clipboard_entries()
    results_json = {
        "items": build_items(entries, selection),
        "variables": {"cb": build_clipboard_variable(entries, selection)},
    }

    print(json.dumps(results_json))


if __name__ == "__main__":
    main()