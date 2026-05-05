#!/bin/bash
# mock-findmnt.sh — simulates findmnt for /tmp CIS rule 1
#
# Real findmnt output for a separately-mounted /tmp looks like:
#   tmpfs /tmp tmpfs rw,nosuid,nodev,noexec,relatime 0 0
# When options are empty (non-compliant) it outputs nothing.

STATE_PY="python3 /aegis-scripts/aegis-state.py"

if [[ "$*" == *"/tmp"* ]]; then
    OPTIONS=$($STATE_PY get rule_1_tmp_options 2>/dev/null || true)

    if [ -z "${OPTIONS}" ]; then
        # /tmp not separately mounted — nothing returned (non-compliant)
        exit 0
    fi

    # The CIS check pipes: findmnt -n /tmp | grep -E 'nodev|nosuid|noexec'
    echo "tmpfs /tmp tmpfs ${OPTIONS} 0 0"
else
    # Delegate non-/tmp queries to the real binary
    /usr/bin/findmnt "$@" 2>/dev/null || true
fi
