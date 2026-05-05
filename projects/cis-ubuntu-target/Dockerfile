# Debian 12 is used as the base because Ubuntu's APT repos are unreachable in
# this environment. The container simulates a Ubuntu 22.04 target — the actual
# base OS does not affect any CIS check since all commands are mocked or the
# real files are created explicitly.
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install only what is needed: OpenSSH server, Python 3, sudo
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    python3 \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# ── SSH user setup ──────────────────────────────────────────────────────────
# aegis-test is the SSH user the Aegis SSHConnector will authenticate as.
# NOPASSWD sudo lets remediation/rollback code run privileged commands.
RUN useradd -m -s /bin/bash aegis-test \
    && echo 'aegis-test:aegistest123' | chpasswd \
    && echo 'aegis-test ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# ── SSH server setup ─────────────────────────────────────────────────────────
RUN mkdir -p /var/run/sshd \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && ssh-keygen -A

# ── Simulated filesystem: rule 3 ─────────────────────────────────────────────
# /boot/grub/grub.cfg starts non-compliant (permissions 755, should be 400).
RUN mkdir -p /boot/grub \
    && echo '# GRUB bootloader config (simulated for CIS testing)' > /boot/grub/grub.cfg \
    && chmod 755 /boot/grub/grub.cfg

# ── Simulated filesystem: rule 9 ─────────────────────────────────────────────
# /etc/passwd starts non-compliant (permissions 664, should be 644).
# SSH and PAM still work correctly because they read the file as root.
RUN chmod 664 /etc/passwd

# ── Simulated filesystem: rule 7 ─────────────────────────────────────────────
# /etc/pam.d/common-password starts non-compliant (md5, should be sha512).
# common-password only governs password-change PAM stack, not auth.
RUN printf 'password\t[success=1 default=ignore]\tpam_unix.so obscure md5\n' \
         > /etc/pam.d/common-password \
    && printf 'password\trequisite\t\t\tpam_deny.so\n' \
         >> /etc/pam.d/common-password \
    && printf 'password\trequired\t\t\tpam_permit.so\n' \
         >> /etc/pam.d/common-password

# ── State directory ───────────────────────────────────────────────────────────
RUN mkdir -p /aegis-state/backup

# ── Copy helper scripts ───────────────────────────────────────────────────────
COPY scripts/ /aegis-scripts/
RUN chmod +x /aegis-scripts/*.sh /aegis-scripts/*.py

# ── Install mock commands ─────────────────────────────────────────────────────
# Placed in /usr/local/bin which precedes /usr/bin and /sbin in Ubuntu PATH.
# The real binaries are still accessible via their full paths.
RUN ln -sf /aegis-scripts/mock-findmnt.sh      /usr/local/bin/findmnt        \
    && ln -sf /aegis-scripts/mock-dpkg.sh          /usr/local/bin/dpkg           \
    && ln -sf /aegis-scripts/mock-sysctl.sh        /usr/local/bin/sysctl         \
    && ln -sf /aegis-scripts/mock-systemctl.sh     /usr/local/bin/systemctl      \
    && ln -sf /aegis-scripts/mock-sshd.sh          /usr/local/bin/sshd           \
    && ln -sf /aegis-scripts/mock-apparmor-status.sh /usr/local/bin/apparmor_status

EXPOSE 22

ENTRYPOINT ["/aegis-scripts/init.sh"]
