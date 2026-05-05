#!/bin/bash
# mock-dpkg.sh — simulates dpkg -s for packages tracked via state (rules 2, 8)
#
# Unknown packages are delegated to the real /usr/bin/dpkg.

STATE_PY="python3 /aegis-scripts/aegis-state.py"

# Extract the package name (last non-option argument)
PKG_NAME=""
for arg in "$@"; do
    if [[ "$arg" != -* ]]; then
        PKG_NAME="$arg"
    fi
done

case "${PKG_NAME}" in
    aide)
        IS_INSTALLED=$($STATE_PY get rule_2_aide_installed 2>/dev/null || echo "false")
        if [[ "${IS_INSTALLED}" == "true" ]]; then
            echo "Package: aide"
            echo "Status: install ok installed"
            echo "Version: 0.17.3-4ubuntu1"
            echo "Description: Advanced Intrusion Detection Environment (simulated)"
        else
            echo "dpkg-query: package 'aide' is not installed and no information is available" >&2
            exit 1
        fi
        ;;

    auditd)
        IS_INSTALLED=$($STATE_PY get rule_8_auditd_active 2>/dev/null || echo "false")
        if [[ "${IS_INSTALLED}" == "true" ]]; then
            echo "Package: auditd"
            echo "Status: install ok installed"
            echo "Version: 1:3.0.7-1build1"
            echo "Description: User space tools for security auditing (simulated)"
        else
            echo "dpkg-query: package 'auditd' is not installed and no information is available" >&2
            exit 1
        fi
        ;;

    *)
        # Fall through to real dpkg for any other package
        exec /usr/bin/dpkg "$@"
        ;;
esac
