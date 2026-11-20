"""Red-Sandwich lite audit: a model from another vendor reviews the change, the tool checks its evidence.

  python rsh_audit.py --spec step01.md --files app.py util.py [--rules rules.txt] [--out report.json]
  python rsh_audit.py ... --response-file saved.json      replay a saved auditor answer (offline)

Any OpenAI-compatible chat endpoint works:
  RSH_AUDIT_API_KEY (or OPENAI_API_KEY), RSH_AUDIT_MODEL, RSH_AUDIT_BASE_URL (default OpenAI).
Exit codes: 0 PASS, 1 FAIL, 2 error (never treat an error as PASS).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import rsh_http
from rsh_evidence import check_findings

DEFAULT_BASE = "https://api.openai.com/v1"
SYSTEM = (
    "You are an adversarial code auditor from a different vendor than the model that wrote this code. "
    "Find defects against the spec: crashes, wrong results, missing spec items, data loss, security. "
    "Ignore style. Answer ONLY with JSON: {\"findings\": [{\"file\": str, \"line\": int, "
    "\"quote\": \"exact code copied from that line\", \"severity\": \"critical|high|medium|low\", "
    "\"rule\": str, \"reason\": str}]}. An empty list means no defects."
)


def numbered(path: str, lines: list[str]) -> str:
    body = "\n".join(f"{no:>4}| {text}" for no, text in enumerate(lines, 1))
    return f"=== FILE {path} ===\n{body}"


def build_prompt(spec: str, sources: dict[str, list[str]], rules: str) -> str:
    parts = [f"=== SPEC ===\n{spec}"]
    if rules:
        parts.append(f"=== RULES (cite one id per finding) ===\n{rules}")
    parts.extend(numbered(path, lines) for path, lines in sources.items())
    return "\n\n".join(parts)


def call_model(prompt: str) -> str:
    key = os.environ.get("RSH_AUDIT_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("RSH_AUDIT_MODEL")
    if not key or not model:
        raise RuntimeError("set RSH_AUDIT_API_KEY (or OPENAI_API_KEY) and RSH_AUDIT_MODEL")
    base = os.environ.get("RSH_AUDIT_BASE_URL", DEFAULT_BASE).rstrip("/")
    body = {"model": model, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    return rsh_http.chat_content(rsh_http.post_json(f"{base}/chat/completions", headers, body))


def parse_findings(answer: str) -> list[dict]:
    data = json.loads(answer)
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        raise ValueError("auditor answer has no 'findings' list")
    if not all(isinstance(f, dict) for f in findings):
        raise ValueError("every finding must be a JSON object")
    return findings


def load_rules(path: str | None) -> tuple[str, set[str] | None]:
    if not path:
        return "", None
    text = Path(path).read_text(encoding="utf-8")
    ids = {line.split()[0] for line in text.splitlines() if line.strip()}
    return text, ids


def audit(args: argparse.Namespace) -> dict:
    sources = {f: Path(f).read_text(encoding="utf-8").splitlines() for f in args.files}
    rules_text, rule_ids = load_rules(args.rules)
    if args.response_file:
        answer = Path(args.response_file).read_text(encoding="utf-8")
    else:
        answer = call_model(build_prompt(Path(args.spec).read_text(encoding="utf-8"), sources, rules_text))
    checked = check_findings(parse_findings(answer), sources, rule_ids)
    return {"verdict": checked.verdict, "kept": checked.kept, "discarded": checked.discarded}


def print_summary(report: dict) -> None:
    for item in report["kept"]:
        print(f"KEPT      {item['file']}:{item['line']} [{item.get('severity')}] {item.get('reason', '')}")
    for item in report["discarded"]:
        print(f"DISCARDED {item.get('file')}:{item.get('line')} - {item['discard_reason']}")
    print(f"verdict: {report['verdict']}  (kept {len(report['kept'])}, discarded {len(report['discarded'])})")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--rules")
    parser.add_argument("--out", default="audit_report.json")
    parser.add_argument("--response-file")
    args = parser.parse_args(argv)
    try:
        report = audit(args)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, RuntimeError, KeyError) as err:
        print(f"audit error (not a PASS): {err}", file=sys.stderr)
        return 2
    print_summary(report)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
