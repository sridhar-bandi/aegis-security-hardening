#!/usr/bin/env python3
"""
seed_instance.py — register the CIS Ubuntu test target in Aegis.

What this script does:
  1. Authenticates as an admin user.
  2. Finds or creates the default workspace.
  3. Finds or uploads the CIS Ubuntu 22.04 policy.
  4. Finds or creates a "CIS Ubuntu 22.04 Test" solution type.
  5. Finds or creates the test hardening profile and populates the 10
     profile rules with evaluation / remediation / rollback code.
  6. Approves all 10 profile rules so they are ready for enforcement.
  7. Finds or creates a solution instance pointing at cis-ubuntu-target
     with the SSH endpoint config for the Aegis SSH connector.

Usage:
    python seed_instance.py \\
        --base-url  http://localhost:8000/api/v1 \\
        --email     admin@aegis.com \\
        --password  <password> \\
        --container-host cis-ubuntu-target   # hostname or IP of the container
        [--container-port 2222]              # default 22

Requirements:  pip install requests
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
POLICY_FILE = HERE.parent.parent / "sample-policies" / "cis-ubuntu-2204.json"
PROFILE_FILE = HERE / "hardening_profile.json"

POLICY_NAME = "CIS Ubuntu 22.04 LTS Benchmark"
ST_NAME     = "CIS Ubuntu 22.04 Test Target"
PROFILE_NAME = "CIS Ubuntu 22.04 — Test Target Profile"
INSTANCE_NAME = "cis-ubuntu-target"

# The 10 rule IDs this script cares about (subset of the full policy)
TARGET_RULE_IDS = {
    "CIS-UBUNTU-1.1.1",
    "CIS-UBUNTU-1.3.1",
    "CIS-UBUNTU-1.4.1",
    "CIS-UBUNTU-3.1.1",
    "CIS-UBUNTU-5.2.4",
    "CIS-UBUNTU-5.2.7",
    "CIS-UBUNTU-5.3.1",
    "CIS-UBUNTU-4.1.1",
    "CIS-UBUNTU-6.1.2",
    "CIS-UBUNTU-1.6.1",
}

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})


# ── helpers ───────────────────────────────────────────────────────────────────

def ok(resp: requests.Response, label: str) -> dict:
    if not resp.ok:
        print(f"[ERROR] {label}: HTTP {resp.status_code} — {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def login(base_url: str, email: str, password: str) -> str:
    resp = SESSION.post(
        f"{base_url}/auth/login",
        json={"identifier": email, "password": password},
        timeout=30,
    )
    data = ok(resp, "login")
    token = data["access_token"]
    SESSION.headers["Authorization"] = f"Bearer {token}"
    print(f"[OK] Authenticated as {email}")
    return token


def list_workspaces(base_url: str) -> list[dict]:
    resp = SESSION.get(f"{base_url}/workspaces", timeout=30)
    return ok(resp, "list workspaces")


def find_or_create_workspace(base_url: str) -> dict:
    workspaces = list_workspaces(base_url)
    if workspaces:
        ws = workspaces[0]
        print(f"[OK] Using workspace: {ws['name']} ({ws['id']})")
        return ws
    resp = SESSION.post(f"{base_url}/workspaces", json={"name": "Default"}, timeout=30)
    ws = ok(resp, "create workspace")
    print(f"[OK] Created workspace: {ws['name']} ({ws['id']})")
    return ws


def find_or_upload_policy(base_url: str, workspace_id: str) -> dict:
    # Check existing policies
    resp = SESSION.get(f"{base_url}/policies", params={"workspace_id": workspace_id}, timeout=30)
    policies = ok(resp, "list policies")
    for p in policies:
        if p["name"] == POLICY_NAME:
            print(f"[OK] Using existing policy: {p['name']} ({p['id']})")
            return p

    # Upload
    print(f"[..] Uploading policy from {POLICY_FILE} ...")
    with POLICY_FILE.open("rb") as fh:
        resp = requests.post(
            f"{base_url}/policies/upload",
            headers={"Authorization": SESSION.headers["Authorization"]},
            params={
                "workspace_id": workspace_id,
                "name": POLICY_NAME,
                "standard": "CIS",
                "format": "json",
            },
            files={"file": (POLICY_FILE.name, fh, "application/json")},
            timeout=60,
        )
    policy = ok(resp, "upload policy")
    print(f"[OK] Uploaded policy: {policy['name']} ({policy['id']})")
    time.sleep(3)   # let the async codegen task start but don't block on it
    return policy


def list_policy_rules(base_url: str, policy_id: str) -> list[dict]:
    resp = SESSION.get(f"{base_url}/policies/{policy_id}/rules", timeout=30)
    return ok(resp, "list policy rules")


def find_or_create_solution_type(base_url: str, workspace_id: str) -> dict:
    resp = SESSION.get(f"{base_url}/solution-types", params={"workspace_id": workspace_id}, timeout=30)
    sts = ok(resp, "list solution types")
    for st in sts:
        if st["name"] == ST_NAME:
            print(f"[OK] Using existing solution type: {st['name']} ({st['id']})")
            return st
    resp = SESSION.post(
        f"{base_url}/solution-types",
        json={
            "workspace_id": workspace_id,
            "name": ST_NAME,
            "description": "Simulated Ubuntu 22.04 target for CIS benchmark testing",
        },
        timeout=30,
    )
    st = ok(resp, "create solution type")
    print(f"[OK] Created solution type: {st['name']} ({st['id']})")
    return st


def set_component_selection(base_url: str, st_id: str) -> None:
    """Set component_selection so the hardening profile auto-creates profile_rules."""
    resp = SESSION.patch(
        f"{base_url}/solution-types/{st_id}/components",
        json={"component_selection": ["ubuntu"]},
        timeout=30,
    )
    if resp.ok:
        print("[OK] Set component_selection = ['ubuntu']")
    else:
        print(f"[WARN] Could not set component_selection: {resp.status_code} {resp.text}")


def find_or_create_profile(base_url: str, st_id: str, policy_id: str) -> dict:
    resp = SESSION.get(f"{base_url}/profiles", params={"solution_type_id": st_id}, timeout=30)
    profiles = ok(resp, "list profiles")
    for p in profiles:
        if p["name"] == PROFILE_NAME:
            print(f"[OK] Using existing profile: {p['name']} ({p['id']})")
            return p
    resp = SESSION.post(
        f"{base_url}/profiles",
        json={
            "name": PROFILE_NAME,
            "solution_type_id": st_id,
            "policy_id": policy_id,
        },
        timeout=30,
    )
    profile = ok(resp, "create profile")
    print(f"[OK] Created profile: {profile['name']} ({profile['id']})")
    return profile


def load_code_map() -> dict[str, dict]:
    """Return {rule_id: {evaluation_code, remediation_code, rollback_code}}."""
    data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    return {r["rule_id"]: r for r in data["rules"]}


def seed_profile_rules(
    base_url: str,
    profile_id: str,
    policy_rules: list[dict],
    code_map: dict[str, dict],
) -> None:
    """Fetch profile rules, match by policy_rule_id → rule_id, update code, approve."""
    resp = SESSION.get(f"{base_url}/profiles/{profile_id}/rules", timeout=30)
    profile_rules = ok(resp, "list profile rules")

    # Build a lookup: policy_rule_id → ProfileRule
    pr_by_prid = {pr["policy_rule_id"]: pr for pr in profile_rules}

    # Build a lookup: policy rule_id (e.g. CIS-UBUNTU-1.1.1) → policy_rule UUID
    prid_by_ruleid = {r["rule_id"]: r["id"] for r in policy_rules if r["rule_id"] in TARGET_RULE_IDS}

    if not prid_by_ruleid:
        print("[WARN] No matching policy rules found — check that the policy was uploaded correctly.")
        return

    updated = 0
    for cis_rule_id, code_entry in code_map.items():
        policy_rule_uuid = prid_by_ruleid.get(cis_rule_id)
        if not policy_rule_uuid:
            print(f"[SKIP] Policy rule not found for {cis_rule_id}")
            continue

        profile_rule = pr_by_prid.get(policy_rule_uuid)
        if not profile_rule:
            print(f"[SKIP] ProfileRule not found for policy_rule {policy_rule_uuid} ({cis_rule_id})")
            continue

        pr_id = profile_rule["id"]

        # Update code
        resp = SESSION.patch(
            f"{base_url}/profiles/{profile_id}/rules/{pr_id}/code",
            json={
                "evaluation_code":  code_entry["evaluation_code"],
                "remediation_code": code_entry["remediation_code"],
                "rollback_code":    code_entry["rollback_code"],
            },
            timeout=30,
        )
        if not resp.ok:
            print(f"[WARN] Could not update code for {cis_rule_id}: {resp.text}")
            continue

        # Approve so the rule is eligible for enforcement
        resp2 = SESSION.post(
            f"{base_url}/profiles/{profile_id}/rules/{pr_id}/approve",
            timeout=30,
        )
        if resp2.ok:
            print(f"  [OK] Rule {cis_rule_id} — code set & approved")
            updated += 1
        else:
            print(f"  [WARN] Rule {cis_rule_id} code set but approval failed: {resp2.text}")

    print(f"[OK] {updated}/{len(code_map)} rules updated and approved")


def find_or_create_instance(
    base_url: str,
    workspace_id: str,
    st_id: str,
    profile_id: str,
    container_host: str,
    container_port: int,
) -> dict:
    resp = SESSION.get(f"{base_url}/instances", params={"workspace_id": workspace_id}, timeout=30)
    instances = ok(resp, "list instances")
    for inst in instances:
        if inst["name"] == INSTANCE_NAME:
            print(f"[OK] Using existing instance: {inst['name']} ({inst['id']})")
            return inst

    resp = SESSION.post(
        f"{base_url}/instances",
        json={
            "workspace_id": workspace_id,
            "name": INSTANCE_NAME,
            "solution_type_id": st_id,
            "profile_id": profile_id,
        },
        timeout=30,
    )
    inst = ok(resp, "create instance")
    print(f"[OK] Created instance: {inst['name']} ({inst['id']})")

    # Patch config_json with SSH endpoint details
    endpoint_config = {
        "host":     container_host,
        "port":     container_port,
        "username": "aegis-test",
        "password": "aegistest123",
        "connector_type": "ssh",
    }
    resp2 = SESSION.patch(
        f"{base_url}/instances/{inst['id']}",
        json={"config_json": endpoint_config},
        timeout=30,
    )
    if resp2.ok:
        print(f"[OK] Instance endpoint config set: {container_host}:{container_port}")
    else:
        print(f"[WARN] Could not patch instance config: {resp2.status_code} {resp2.text}")
        print(f"       Set it manually: host={container_host}, port={container_port},")
        print(f"       username=aegis-test, password=aegistest123")

    return inst


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed CIS Ubuntu test instance in Aegis")
    parser.add_argument("--base-url",       default="http://localhost:8000/api/v1")
    parser.add_argument("--email",          default="admin@aegis.com")
    parser.add_argument("--password",       required=True)
    parser.add_argument("--container-host", default="cis-ubuntu-target",
                        help="Hostname or IP the Aegis API uses to reach the container")
    parser.add_argument("--container-port", type=int, default=22)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    login(base, args.email, args.password)

    ws      = find_or_create_workspace(base)
    ws_id   = ws["id"]

    policy  = find_or_upload_policy(base, ws_id)
    pol_id  = policy["id"]

    policy_rules = list_policy_rules(base, pol_id)
    print(f"[OK] Found {len(policy_rules)} policy rules")

    st      = find_or_create_solution_type(base, ws_id)
    st_id   = st["id"]

    set_component_selection(base, st_id)

    profile  = find_or_create_profile(base, st_id, pol_id)
    prof_id  = profile["id"]

    code_map = load_code_map()
    seed_profile_rules(base, prof_id, policy_rules, code_map)

    inst = find_or_create_instance(
        base, ws_id, st_id, prof_id,
        args.container_host, args.container_port,
    )

    print()
    print("=" * 60)
    print("CIS Ubuntu test target is ready!")
    print(f"  Instance ID : {inst['id']}")
    print(f"  Profile  ID : {prof_id}")
    print(f"  Endpoint    : {args.container_host}:{args.container_port}")
    print()
    print("To run evaluation:")
    print(f"  POST {base}/instances/{inst['id']}/evaluate")
    print()
    print("To run remediation:")
    print(f"  POST {base}/instances/{inst['id']}/remediate")
    print()
    print("To run rollback:")
    print(f"  POST {base}/instances/{inst['id']}/rollback")
    print("=" * 60)


if __name__ == "__main__":
    main()
