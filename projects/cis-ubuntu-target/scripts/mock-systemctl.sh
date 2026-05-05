#!/bin/bash
# mock-systemctl.sh — simulates systemctl for container services (rules 8, 10)
#
# Containers have no systemd. This mock reads Aegis state and returns the
# appropriate exit code and output so CIS checks behave correctly.

STATE_PY="python3 /aegis-scripts/aegis-state.py"

SUBCOMMAND="${1}"
SERVICE="${2}"

case "${SUBCOMMAND}" in
    is-active)
        case "${SERVICE}" in
            auditd)
                IS_ACTIVE=$($STATE_PY get rule_8_auditd_active 2>/dev/null || echo "false")
                if [[ "${IS_ACTIVE}" == "true" ]]; then
                    echo "active"
                    exit 0
                else
                    echo "inactive"
                    exit 1
                fi
                ;;
            apparmor)
                COUNT=$($STATE_PY get rule_10_apparmor_enforcing 2>/dev/null || echo "0")
                if [[ "${COUNT}" != "0" ]] && [[ -n "${COUNT}" ]]; then
                    echo "active"
                    exit 0
                else
                    echo "inactive"
                    exit 1
                fi
                ;;
            *)
                echo "inactive"
                exit 1
                ;;
        esac
        ;;

    enable|start|stop|restart|daemon-reload)
        # No-op in the test container — remediation code calls these for realism
        echo "[mock-systemctl] ${SUBCOMMAND} ${SERVICE}: no-op in test container"
        exit 0
        ;;

    status)
        echo "[mock-systemctl] ${SERVICE}: simulated (test container)"
        exit 0
        ;;

    *)
        echo "[mock-systemctl] Unhandled: ${SUBCOMMAND} ${*}"
        exit 0
        ;;
esac
