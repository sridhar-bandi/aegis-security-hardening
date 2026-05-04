#!/usr/bin/env python3
"""
Seed sample hardening policies into Aegis via the REST API.

Usage:
    python seed_policies.py \
        --base-url http://localhost:8000/api/v1 \
        --email admin@aegis.com \
        --password <your-password> \
        --workspace-id <workspace-uuid>

The script authenticates as an admin/security_officer, then uploads each
JSON policy file in this directory using the /policies/upload endpoint.
Each file is uploaded as format=text (the LLM-assisted text parser reads
the pre-structured JSON directly and extracts the rules reliably).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

POLICY_FILES = [
    {
        "file": "cis-ubuntu-2204.json",
        "name": "CIS Ubuntu 22.04 LTS Benchmark",
        "standard": "CIS",
    },
    {
        "file": "cis-vmware-esxi.json",
        "name": "CIS VMware ESXi Hypervisor Benchmark",
        "standard": "CIS",
    },
    {
        "file": "cis-network-switch.json",
        "name": "CIS Network Switch (Cisco/Aruba) Benchmark",
        "standard": "CIS",
    },
    {
        "file": "hpe-ilo-security.json",
        "name": "HPE iLO Security Best Practices",
        "standard": "Custom",
    },
]


def login(base_url: str, email: str, password: str) -> str:
    resp = requests.post(
        f"{base_url}/auth/login",
        json={"identifier": email, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def upload_policy(
    base_url: str,
    token: str,
    workspace_id: str,
    name: str,
    standard: str,
    policy_path: Path,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "workspace_id": workspace_id,
        "name": name,
        "standard": standard,
        "format": "text",
    }
    with policy_path.open("rb") as fh:
        resp = requests.post(
            f"{base_url}/policies/upload",
            headers=headers,
            params=params,
            files={"file": (policy_path.name, fh, "application/json")},
            timeout=120,  # LLM parsing may take a moment
        )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed sample hardening policies into Aegis.")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1", help="Aegis API base URL")
    parser.add_argument("--email", required=True, help="Admin or security_officer email")
    parser.add_argument("--password", required=True, help="Account password")
    parser.add_argument("--workspace-id", required=True, help="Target workspace UUID")
    args = parser.parse_args()

    script_dir = Path(__file__).parent

    print(f"Authenticating as {args.email} ...")
    try:
        token = login(args.base_url, args.email, args.password)
    except requests.HTTPError as exc:
        print(f"ERROR: Login failed: {exc.response.text}", file=sys.stderr)
        sys.exit(1)
    print("  ✓ Authenticated")

    for entry in POLICY_FILES:
        policy_path = script_dir / entry["file"]
        if not policy_path.exists():
            print(f"  SKIP: {entry['file']} not found", file=sys.stderr)
            continue

        print(f"\nUploading: {entry['name']} ({entry['file']}) ...")
        try:
            result = upload_policy(
                base_url=args.base_url,
                token=token,
                workspace_id=args.workspace_id,
                name=entry["name"],
                standard=entry["standard"],
                policy_path=policy_path,
            )
            print(f"  ✓ Created policy id={result['id']} name='{result['name']}'")
        except requests.HTTPError as exc:
            status_code = exc.response.status_code
            try:
                detail = exc.response.json().get("detail", exc.response.text)
            except Exception:
                detail = exc.response.text
            print(f"  ERROR [{status_code}]: {detail}", file=sys.stderr)

    print("\nDone.")


if __name__ == "__main__":
    main()
