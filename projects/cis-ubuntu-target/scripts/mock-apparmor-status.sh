#!/bin/bash
# mock-apparmor-status.sh — simulates apparmor_status output (rule 10)
#
# Outputs the number of enforcing profiles based on Aegis state.
# The CIS check pipes: apparmor_status | grep 'profiles are in enforce mode'

STATE_PY="python3 /aegis-scripts/aegis-state.py"

COUNT=$($STATE_PY get rule_10_apparmor_enforcing 2>/dev/null || echo "0")

echo "apparmor module is loaded."
if [[ "${COUNT}" == "0" ]]; then
    TOTAL=0
    COMPLAIN=0
else
    TOTAL=$((COUNT + 2))
    COMPLAIN=2
fi

echo "${TOTAL} profiles are loaded."
echo "${COUNT} profiles are in enforce mode."
echo "${COMPLAIN} profiles are in complain mode."
echo "0 processes have profiles defined."
echo "0 processes are in enforce mode."
echo "0 processes are in complain mode."
echo "0 processes are unconfined but have a profile defined."
