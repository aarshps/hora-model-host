#!/usr/bin/env python3
"""benchmark_model.py — Measure tokens/sec for any Ollama model via the gateway.

Usage:
    python deploy/benchmark_model.py --model qwen2.5:7b-instruct
    python deploy/benchmark_model.py --model phi-4-mini --base http://1.2.3.4:8000/v1
    python deploy/benchmark_model.py --all   # benchmark every loaded model

Runs a standard 3-prompt warm/hot/long workload so numbers across models are
comparable. Writes results to performance_report.md (gitignored).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

DEFAULT_BASE = os.getenv("HORA_BASE_URL", "http://localhost:8000/v1")
DEFAULT_KEY = os.getenv("API_KEY", "")
REPORT_PATH = Path(__file__).resolve().parent.parent / "performance_report.md"

PROMPTS = [
    ("short",  "Reply with the single word: ready."),
    ("medium", "In one short sentence, explain what an LLM is."),
    ("long",   "Write a 150-word explanation of how a CPU executes an instruction, "
               "covering fetch, decode, execute, and writeback."),
]


def stream_completion(base: str, key: str, model: str, prompt: str) -> tuple[float, float, int]:
    """Returns (ttft_s, total_s, tokens_streamed)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    t0 = time.perf_counter()
    ttft = None
    tokens = 0

    with httpx.stream("POST", f"{base}/chat/completions", json=payload, headers=headers, timeout=600.0) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.read().decode('utf-8', errors='replace')}")
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
            if delta:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                # Crude token estimate: whitespace-split — close enough for comparison.
                tokens += max(1, len(delta.split()))
    total = time.perf_counter() - t0
    return (ttft or total, total, tokens)


def benchmark(base: str, key: str, model: str) -> dict:
    print(f"\n=== Benchmarking {model} ===")
    rows = []
    for label, prompt in PROMPTS:
        try:
            ttft, total, tokens = stream_completion(base, key, model, prompt)
        except Exception as exc:
            print(f"  [{label}] FAILED: {exc}")
            rows.append({"label": label, "error": str(exc)})
            continue
        gen_time = max(total - ttft, 0.001)
        tps = tokens / gen_time
        print(f"  [{label}] ttft={ttft:.2f}s  total={total:.2f}s  ~tokens={tokens}  t/s={tps:.2f}")
        rows.append({"label": label, "ttft_s": round(ttft, 2), "total_s": round(total, 2),
                     "tokens": tokens, "tps": round(tps, 2)})
    return {"model": model, "rows": rows}


def discover_models(base: str, key: str) -> list[str]:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = httpx.get(f"{base}/models", headers=headers, timeout=15.0)
    r.raise_for_status()
    body = r.json()
    return [m["id"] for m in body.get("data", [])]


def write_report(results: list[dict], base: str) -> None:
    lines = ["# Performance Report", "", f"Gateway: `{base}`", ""]
    for res in results:
        lines += [f"## {res['model']}", "", "| Phase | TTFT (s) | Total (s) | ~Tokens | t/s |", "|---|---|---|---|---|"]
        for r in res["rows"]:
            if "error" in r:
                lines.append(f"| {r['label']} | — | — | — | ERROR: {r['error']} |")
            else:
                lines.append(f"| {r['label']} | {r['ttft_s']} | {r['total_s']} | {r['tokens']} | {r['tps']} |")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", help="Ollama model tag to benchmark")
    p.add_argument("--all", action="store_true", help="Benchmark all models reported by /v1/models")
    p.add_argument("--base", default=DEFAULT_BASE, help=f"Gateway base URL (default: {DEFAULT_BASE})")
    p.add_argument("--key", default=DEFAULT_KEY, help="Bearer API key (default: from .env)")
    args = p.parse_args()

    if not args.model and not args.all:
        p.error("Provide --model <tag> or --all")

    models = [args.model] if args.model else discover_models(args.base, args.key)
    if not models:
        print("No models found.")
        return 1

    results = [benchmark(args.base, args.key, m) for m in models]
    write_report(results, args.base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
