# CIS Ubuntu Test Target

A lightweight Docker container that acts as a **simulated Ubuntu 22.04 system** for testing the Aegis Security Hardening evaluate / remediate / rollback pipeline against the CIS Ubuntu 22.04 benchmark.

It is **not** a real OS — no real services are hardened. Instead, a JSON state file and mock shell commands let Aegis safely exercise the full enforcement workflow without touching production systems.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              cis-ubuntu-target container             │
│                                                     │
│  OpenSSH (port 22)  ←──── Aegis SSHConnector        │
│                                                     │
│  /aegis-state/state.json  ← central config store    │
│  /aegis-scripts/aegis-state.py  ← state manager     │
│                                                     │
│  Mock commands in /usr/local/bin/ (shadow real cmds)│
│    findmnt      → reads rule_1_tmp_options          │
│    dpkg         → reads rule_2_aide_installed       │
│    sysctl       → reads rule_4_ipv6_disabled        │
│    systemctl    → reads rule_8_auditd_active        │
│    sshd         → reads rule_5/6 ssh state         │
│    apparmor_status → reads rule_10_apparmor         │
│                                                     │
│  Real filesystem objects (rules 3, 7, 9):           │
│    /boot/grub/grub.cfg  ← permissions (755→400)     │
│    /etc/pam.d/common-password ← hash (md5→sha512)   │
│    /etc/passwd           ← permissions (664→644)    │
└─────────────────────────────────────────────────────┘
```

---

## The 10 CIS Rules

| # | Rule ID             | Category        | What is tested                        | Initial state     |
|---|---------------------|-----------------|---------------------------------------|-------------------|
| 1 | CIS-UBUNTU-1.1.1    | Filesystem      | `/tmp` mount options (nodev/nosuid/noexec) | Not mounted (state) |
| 2 | CIS-UBUNTU-1.3.1    | Filesystem      | AIDE intrusion detection installed    | Not installed (state) |
| 3 | CIS-UBUNTU-1.4.1    | Filesystem      | `/boot/grub/grub.cfg` permissions     | 755 (real file) |
| 4 | CIS-UBUNTU-3.1.1    | Network         | IPv6 disabled via sysctl              | Enabled (state) |
| 5 | CIS-UBUNTU-5.2.4    | SSH             | SSH Protocol 2 enforced               | Protocol 1 (state) |
| 6 | CIS-UBUNTU-5.2.7    | SSH             | SSH root login disabled               | PermitRootLogin yes (state) |
| 7 | CIS-UBUNTU-5.3.1    | Authentication  | Password hashing SHA-512              | md5 in pam.d (real file) |
| 8 | CIS-UBUNTU-4.1.1    | Audit           | auditd installed and active           | Inactive (state) |
| 9 | CIS-UBUNTU-6.1.2    | Filesystem      | `/etc/passwd` permissions 644         | 664 (real file) |
| 10 | CIS-UBUNTU-1.6.1   | General         | AppArmor enforcing profiles           | 0 enforcing (state) |

**Initial state:** all 10 rules start **non-compliant** so evaluation immediately shows 0/10 passing.

---

## Quick Start

### 1. Build and start the container

```bash
docker compose up -d --build cis-ubuntu-target
```

### 2. Verify the container is running

```bash
docker logs cis-ubuntu-target
# Expected: "Starting SSH daemon on port 22..."

# Check state (all rules non-compliant)
docker exec cis-ubuntu-target python3 /aegis-scripts/aegis-state.py dump

# Test SSH access
ssh -p 2222 aegis-test@localhost   # password: aegistest123
```

### 3. Seed the instance in Aegis

```bash
cd projects/cis-ubuntu-target/seed
pip install requests
python seed_instance.py --password <your-admin-password>
```

> The seed script:
> - Uploads the CIS Ubuntu 22.04 policy (if not already present)
> - Creates a solution type, hardening profile with 10 approved rules
> - Registers the instance with SSH endpoint credentials

If the Aegis API and the `cis-ubuntu-target` container are both inside Docker Compose, use:

```bash
python seed_instance.py \
  --base-url http://localhost:8000/api/v1 \
  --password <password> \
  --container-host cis-ubuntu-target \
  --container-port 22
```

---

## Testing the Enforcement Workflow

Use the Aegis UI or REST API:

### Evaluate (check compliance)

```bash
curl -s -X POST http://localhost:8000/api/v1/instances/<INSTANCE_ID>/evaluate \
  -H "Authorization: Bearer <token>" | jq .
# Expected: 0/10 rules compliant
```

### Remediate (apply fixes)

```bash
curl -s -X POST http://localhost:8000/api/v1/instances/<INSTANCE_ID>/remediate \
  -H "Authorization: Bearer <token>" | jq .
```

### Evaluate again (confirm compliance)

Re-run evaluation — expect 10/10 rules compliant.

### Rollback (restore non-compliant state)

```bash
curl -s -X POST http://localhost:8000/api/v1/instances/<INSTANCE_ID>/rollback \
  -H "Authorization: Bearer <token>" | jq .
```

Re-run evaluation — expect 0/10 rules compliant again.

---

## Manual State Inspection

```bash
# View all state values
docker exec cis-ubuntu-target python3 /aegis-scripts/aegis-state.py dump

# Check a single value
docker exec cis-ubuntu-target python3 /aegis-scripts/aegis-state.py get rule_5_ssh_protocol

# Manually set a value (useful for debugging)
docker exec cis-ubuntu-target python3 /aegis-scripts/aegis-state.py set rule_5_ssh_protocol 2

# Reset everything to initial non-compliant defaults
docker exec cis-ubuntu-target python3 /aegis-scripts/aegis-state.py reset
```

---

## SSH Credentials

| Field    | Value           |
|----------|-----------------|
| Host     | `cis-ubuntu-target` (Docker network) or `localhost` (host port 2222) |
| Port     | `22` (internal) / `2222` (host) |
| Username | `aegis-test` |
| Password | `aegistest123` |

The user has passwordless sudo for running privileged commands (chmod, chown, sed on system files).

---

## State Persistence

The state volume `cis_ubuntu_state` persists `/aegis-state/` across container restarts. To start fresh:

```bash
docker compose down -v --remove-orphans
docker compose up -d --build cis-ubuntu-target
```
