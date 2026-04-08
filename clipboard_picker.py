import json
import os
import sys


def parse_query(raw_query: str) -> list[int]:
    numbers = []
    for part in raw_query.split():
        try:
            value = int(part)
        except ValueError:
            continue

        if 1 <= value <= 20:
            numbers.append(value)

    return numbers


def main():
    query_raw = sys.argv[1] if len(sys.argv) > 1 else ""
    query = parse_query(query_raw)

    results_json = {"items": []}

    clipboard_all = []

    # preserve user-supplied order, similar to PHP array_combine($query, $query)
    clipboard = {n: n for n in query}

    query_set = set(query)

    for i in range(1, 21):
        cb_value = os.getenv(f"cb{i}", "")
        clipboard_all.append(cb_value)

        if i in query_set:
            if i in clipboard:
                clipboard[i] = cb_value
            icon = f"icons/icon-picked-{i}.png"
        else:
            icon = f"icons/icon-{i}.png"

        results_json["items"].append(
            {
                "title": cb_value,
                "icon": {
                    "path": icon,
                },
            }
        )

    results_json["variables"] = {
        "cb": "\n".join(clipboard.values()) if clipboard else "\n".join(clipboard_all),
    }

    print(json.dumps(results_json))


if __name__ == "__main__":
    main()