#!/bin/bash
# mock-sysctl.sh — simulates sysctl for IPv6 kernel parameters (rule 4)
#
# In a container, IPv6 sysctl params are read-only (no kernel namespace access).
# The mock reads the desired state and returns the correct output format.

STATE_PY="python3 /aegis-scripts/aegis-state.py"

# Check which parameter is being queried
ARGS="$*"

if [[ "${ARGS}" == *"net.ipv6.conf.all.disable_ipv6"* ]]; then
    IS_DISABLED=$($STATE_PY get rule_4_ipv6_disabled 2>/dev/null || echo "false")
    if [[ "${IS_DISABLED}" == "true" ]]; then
        echo "net.ipv6.conf.all.disable_ipv6 = 1"
    else
        echo "net.ipv6.conf.all.disable_ipv6 = 0"
    fi

elif [[ "${ARGS}" == *"net.ipv6.conf.default.disable_ipv6"* ]]; then
    IS_DISABLED=$($STATE_PY get rule_4_ipv6_disabled 2>/dev/null || echo "false")
    if [[ "${IS_DISABLED}" == "true" ]]; then
        echo "net.ipv6.conf.default.disable_ipv6 = 1"
    else
        echo "net.ipv6.conf.default.disable_ipv6 = 0"
    fi

else
    # Delegate everything else to the real sysctl
    /sbin/sysctl "$@" 2>/dev/null || true
fi
