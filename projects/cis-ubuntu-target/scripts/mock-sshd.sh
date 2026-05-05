#!/bin/bash
# mock-sshd.sh — simulates `sshd -T` for SSH configuration rules (5, 6)
#
# `sshd -T` prints the effective sshd configuration.
# The real sshd is invoked directly via its full path (/usr/sbin/sshd) for
# anything other than -T, so no recursion occurs.

STATE_PY="python3 /aegis-scripts/aegis-state.py"

if [[ "$*" == *"-T"* ]]; then
    PROTOCOL=$($STATE_PY get rule_5_ssh_protocol 2>/dev/null || echo "1")
    ROOT_LOGIN=$($STATE_PY get rule_6_ssh_root_login 2>/dev/null || echo "yes")

    # Output mimics the format of real `sshd -T`
    echo "protocol ${PROTOCOL}"
    echo "permitrootlogin ${ROOT_LOGIN}"
    echo "passwordauthentication yes"
    echo "challengeresponseauthentication no"
    echo "usepam yes"
    echo "x11forwarding yes"
    echo "printmotd no"
    echo "acceptenv LANG LC_*"
    echo "subsystem sftp /usr/lib/openssh/sftp-server"
    echo "maxauthtries 6"
    echo "loglevel INFO"
    echo "port 22"
    echo "addressfamily any"
else
    # Delegate to the real sshd binary (e.g., when called to start the daemon)
    exec /usr/sbin/sshd "$@"
fi
