#!/usr/bin/env python3
"""
aegis-state.py — simple JSON state manager for the CIS Ubuntu test container.

All simulated CIS-rule states live in /aegis-state/state.json.
Rules that test real file-system objects (rules 3, 7, 9) modify actual files;
all other rules use entries in this state file that the mock commands read.

Usage:
    python3 aegis-state.py get  <key>
    python3 aegis-state.py set  <key> <value>
    python3 aegis-state.py dump
    python3 aegis-state.py reset          # restore initial defaults
"""
from __future__ import annotations

import json
import os
import shutil
import sys

STATE_FILE = "/aegis-state/state.json"
INITIAL_FILE = "/aegis-scripts/initial-state.json"


def _load() -> dict:
    with open(STATE_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _save(state: dict) -> None:
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, STATE_FILE)          # atomic on Linux


def _cast(value: str):
    """Coerce CLI string to an appropriate Python type."""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value                         # keep as string


def cmd_get(key: str) -> None:
    state = _load()
    val = state.get(key, "")
    # Print in a shell-friendly way
    if isinstance(val, bool):
        print(str(val).lower())
    else:
        print(val)


def cmd_set(key: str, raw_value: str) -> None:
    state = _load()
    state[key] = _cast(raw_value)
    _save(state)
    print(f"[aegis-state] {key} = {state[key]!r}")


def cmd_dump() -> None:
    state = _load()
    print(json.dumps(state, indent=2))


def cmd_reset() -> None:
    shutil.copyfile(INITIAL_FILE, STATE_FILE)
    print("[aegis-state] State reset to initial defaults")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        if len(sys.argv) < 3:
            print("Usage: aegis-state.py get <key>", file=sys.stderr)
            sys.exit(1)
        cmd_get(sys.argv[2])

    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: aegis-state.py set <key> <value>", file=sys.stderr)
            sys.exit(1)
        cmd_set(sys.argv[2], sys.argv[3])

    elif command == "dump":
        cmd_dump()

    elif command == "reset":
        cmd_reset()

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
