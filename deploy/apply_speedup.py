#!/usr/bin/env python3
"""apply_speedup.py — Push the v1.1 perf-tuning bundle to the VPS in one shot.

What it does, in order, on the remote VPS:
  1. `git pull` so the box has the latest harness code.
  2. `ollama pull` the new fast model (default: qwen2.5:7b-instruct).
  3. `deploy/tune_ollama.sh --apply` to set KEEP_ALIVE=-1, KV cache q4_0,
     flash attention, NUM_THREAD=nproc.
  4. Rewrite /opt/hora-model-host/.env so MODEL_ID points at the new model
     (legacy GEMMA_MODEL is left in place — gateway honors both).
  5. systemctl restart gateway.
  6. Update /root/.openclaw/openclaw.json so agent.model points at the new
     ollama/<MODEL_ID>. Restart the openclaw user-service.
  7. Run a quick benchmark via the gateway.

Reusable for any deployment — drives entirely off your local .env:
    VPS_HOST=185.194.218.92   (or your IP)
    VPS_USER=root
    BW_PASSWORD=<root password>
    NEW_MODEL_ID=qwen2.5:7b-instruct   (optional override)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env")

VPS_HOST = os.getenv("VPS_HOST", "185.194.218.92")
VPS_USER = os.getenv("VPS_USER", "root")
PASSWORD = os.getenv("BW_PASSWORD")
NEW_MODEL = os.getenv("NEW_MODEL_ID", "qwen2.5:7b-instruct")
REPO_DIR = "/opt/hora-model-host"
OPENCLAW_CONFIG = "/root/.openclaw/openclaw.json"


def banner(msg: str) -> None:
    print(f"\n{'=' * 70}\n{msg}\n{'=' * 70}", flush=True)


def run(ssh: paramiko.SSHClient, cmd: str, *, tolerate_fail: bool = False) -> int:
    print(f"\n$ {cmd}", flush=True)
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    for line in iter(stdout.readline, ""):
        if not line:
            break
        print(line.rstrip(), flush=True)
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if err:
        print(err, flush=True)
    if exit_code != 0 and not tolerate_fail:
        raise RuntimeError(f"Command failed (exit {exit_code}): {cmd}")
    return exit_code


def main() -> int:
    if not PASSWORD:
        print("ERROR: BW_PASSWORD missing in local .env", file=sys.stderr)
        return 1

    banner(f"Applying v1.1 speedup to {VPS_USER}@{VPS_HOST} (model -> {NEW_MODEL})")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {VPS_HOST}...", flush=True)
    t0 = time.time()
    ssh.connect(VPS_HOST, username=VPS_USER, password=PASSWORD, timeout=30)
    print(f"SSH established ({time.time() - t0:.1f}s)", flush=True)

    try:
        banner("Step 1/7 — pull latest harness code")
        # Handle both cases: existing git checkout, OR an SFTP-deployed
        # directory we need to convert into a tracked checkout. The .env
        # and any other gitignored files survive `git reset --hard`.
        bootstrap_git = (
            f"cd {REPO_DIR} && "
            "if [ ! -d .git ]; then "
            "  git init -q && "
            "  git remote add origin https://github.com/aarshps/hora-model-host.git; "
            "fi && "
            "git fetch --all --prune && "
            "git reset --hard origin/master"
        )
        run(ssh, bootstrap_git)

        banner("Step 2/7 — install gettext (envsubst) if missing")
        run(ssh, "command -v envsubst >/dev/null || apt-get install -y gettext")

        banner(f"Step 3/7 — pull {NEW_MODEL} via Ollama")
        run(ssh, f"ollama pull {NEW_MODEL}")

        banner("Step 4/7 — apply tune_ollama.sh")
        run(ssh, f"cd {REPO_DIR} && chmod +x deploy/tune_ollama.sh && deploy/tune_ollama.sh --apply")

        banner(f"Step 5/7 — set MODEL_ID={NEW_MODEL} in {REPO_DIR}/.env")
        # If MODEL_ID line exists, update it; otherwise append it.
        env_patch = (
            f"cd {REPO_DIR} && "
            f"if grep -q '^MODEL_ID=' .env; then "
            f"  sed -i 's|^MODEL_ID=.*|MODEL_ID={NEW_MODEL}|' .env; "
            f"else "
            f"  echo 'MODEL_ID={NEW_MODEL}' >> .env; "
            f"fi && "
            f"grep -E '^(MODEL_ID|GEMMA_MODEL)=' .env"
        )
        run(ssh, env_patch)
        run(ssh, "systemctl restart gateway && sleep 2 && systemctl is-active gateway")

        banner(f"Step 6/7 — point OpenClaw at ollama/{NEW_MODEL} and restart")
        # Use Python on the remote to rewrite the JSON safely.
        openclaw_patch = (
            f"python3 - <<'PY'\n"
            f"import json, pathlib\n"
            f"p = pathlib.Path('{OPENCLAW_CONFIG}')\n"
            f"if not p.exists():\n"
            f"    print('openclaw config not found at', p, '- skipping')\n"
            f"else:\n"
            f"    cfg = json.loads(p.read_text())\n"
            f"    old = cfg.get('agent', {{}}).get('model')\n"
            f"    cfg.setdefault('agent', {{}})['model'] = 'ollama/{NEW_MODEL}'\n"
            f"    p.write_text(json.dumps(cfg, indent=2))\n"
            f"    print(f'agent.model: {{old}} -> ollama/{NEW_MODEL}')\n"
            f"PY"
        )
        run(ssh, openclaw_patch, tolerate_fail=True)
        run(
            ssh,
            "export XDG_RUNTIME_DIR=/run/user/0 && "
            "systemctl --user restart openclaw-gateway && "
            "sleep 2 && systemctl --user is-active openclaw-gateway",
            tolerate_fail=True,
        )

        banner(f"Step 7/7 — benchmark {NEW_MODEL} through the gateway")
        run(
            ssh,
            f"cd {REPO_DIR} && "
            f"HORA_BASE_URL=http://localhost:8000/v1 "
            f"venv/bin/python deploy/benchmark_model.py --model {NEW_MODEL}",
            tolerate_fail=True,
        )

        banner("DONE — Con Taboclo should feel dramatically faster on Telegram.")
        return 0

    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
