import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))

import rsh_audit  # noqa: E402
from rsh_evidence import check_findings  # noqa: E402

SOURCES = {"app.py": ["def total(xs):", "    return sum(xs)", "", "def avg(xs):", "    return total(xs) / len(xs)"]}


def finding(**overrides) -> dict:
    base = {"file": "app.py", "line": 5, "quote": "return total(xs) / len(xs)", "severity": "high", "rule": "SPEC"}
    return {**base, **overrides}


def test_real_finding_is_kept_and_fails():
    checked = check_findings([finding()], SOURCES)
    assert checked.verdict == "FAIL" and len(checked.kept) == 1


def test_invented_evidence_is_discarded():
    bad = [finding(file="other.py"), finding(line=99), finding(line="5"), finding(quote="x = 1  # not there"),
           finding(quote="short"), finding(rule="R999")]
    checked = check_findings(bad, SOURCES, rules={"SPEC"})
    reasons = [d["discard_reason"] for d in checked.discarded]
    assert checked.kept == [] and checked.verdict == "PASS"
    assert len(reasons) == 6 and "not sent" in reasons[0] and "does not exist" in reasons[1]


def test_quote_may_sit_a_few_lines_away_and_whitespace_is_ignored():
    checked = check_findings([finding(line=3, quote="return   total(xs)  /  len(xs)")], SOURCES)
    assert len(checked.kept) == 1


def test_low_severity_alone_passes():
    assert check_findings([finding(severity="medium")], SOURCES).verdict == "PASS"


def run_demo(tmp_path: Path, answer: str) -> tuple[int, Path]:
    response = tmp_path / "answer.json"
    response.write_text(answer, encoding="utf-8")
    out = tmp_path / "report.json"
    code = rsh_audit.main(["--spec", str(KIT / "examples" / "spec_step01.md"), "--files", "examples/good_unit.py",
                           "--rules", str(KIT / "rules.example.txt"), "--response-file", str(response),
                           "--out", str(out)])
    return code, out


def test_replayed_demo_answer(tmp_path, monkeypatch):
    monkeypatch.chdir(KIT)
    code, out = run_demo(tmp_path, (KIT / "examples" / "auditor_answer.json").read_text(encoding="utf-8"))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0 and len(report["kept"]) == 1 and len(report["discarded"]) == 3


def test_broken_answer_is_an_error_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.chdir(KIT)
    assert run_demo(tmp_path, "not json")[0] == 2
    assert run_demo(tmp_path, '{"verdict": "PASS"}')[0] == 2
    assert run_demo(tmp_path, '{"findings": ["critical defect"]}')[0] == 2


def test_unwritable_report_path_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(KIT)
    code = rsh_audit.main(["--spec", "examples/spec_step01.md", "--files", "examples/good_unit.py",
                           "--response-file", "examples/auditor_answer.json", "--out", str(tmp_path)])
    assert code == 2


def test_missing_key_is_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(KIT)
    for name in ("RSH_AUDIT_API_KEY", "OPENAI_API_KEY", "RSH_AUDIT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    code = rsh_audit.main(["--spec", "examples/spec_step01.md", "--files", "examples/good_unit.py",
                           "--out", str(tmp_path / "r.json")])
    assert code == 2


def test_prompt_numbers_lines_and_includes_rules():
    prompt = rsh_audit.build_prompt("SPEC TEXT", SOURCES, "SPEC  contract")
    assert "   5| " in prompt and "=== RULES" in prompt and "=== FILE app.py ===" in prompt
