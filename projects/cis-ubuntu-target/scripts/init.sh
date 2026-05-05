#!/bin/bash
# init.sh — container entrypoint for the CIS Ubuntu test target
set -e

echo "[cis-ubuntu-target] Starting up..."

# Initialise state file from the bundled default on first boot
if [ ! -f /aegis-state/state.json ]; then
    cp /aegis-scripts/initial-state.json /aegis-state/state.json
    echo "[cis-ubuntu-target] State initialised from defaults (all rules non-compliant)"
fi

chmod 755 /aegis-state
chmod 644 /aegis-state/state.json

echo "[cis-ubuntu-target] Current state:"
python3 /aegis-scripts/aegis-state.py dump

echo "[cis-ubuntu-target] Starting SSH daemon on port 22..."
exec /usr/sbin/sshd -D
