"""Mechanical evidence check for auditor findings.

An auditor model can invent files, line numbers or code. Every finding must point at a
file that was actually sent, a line that exists, and a quote that really appears within
a few lines of that spot. Anything else is discarded before the verdict is computed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

BLOCKING = {"critical", "high"}
WINDOW = 3
MIN_QUOTE = 8


@dataclass
class Checked:
    kept: list[dict] = field(default_factory=list)
    discarded: list[dict] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        blocking = [f for f in self.kept if str(f.get("severity", "")).lower() in BLOCKING]
        return "FAIL" if blocking else "PASS"


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def quote_found(lines: list[str], line: int, quote: str) -> bool:
    start = max(0, line - 1 - WINDOW)
    window = squash(" ".join(lines[start:line + WINDOW]))
    return squash(quote) in window


def bad_file(finding: dict, sources: dict[str, list[str]], rules: set[str] | None) -> str:
    return "" if str(finding.get("file", "")) in sources else "file was not sent to the auditor"


def bad_line(finding: dict, sources: dict[str, list[str]], rules: set[str] | None) -> str:
    lines = sources[str(finding.get("file"))]
    line = finding.get("line")
    if type(line) is int and 1 <= line <= len(lines):  # bool is an int subclass; reject true/false
        return ""
    return f"line {line!r} does not exist (file has {len(lines)} lines)"


def bad_quote(finding: dict, sources: dict[str, list[str]], rules: set[str] | None) -> str:
    quote = str(finding.get("quote", ""))
    if len(squash(quote)) < MIN_QUOTE:
        return f"quote shorter than {MIN_QUOTE} characters"
    found = quote_found(sources[str(finding.get("file"))], finding["line"], quote)
    return "" if found else "quoted code is not near the cited line"


def bad_rule(finding: dict, sources: dict[str, list[str]], rules: set[str] | None) -> str:
    if rules is None or str(finding.get("rule", "")) in rules:
        return ""
    return f"rule {finding.get('rule')!r} is not in the rule list"


CHECKS = (bad_file, bad_line, bad_quote, bad_rule)  # order matters: each check trusts the ones before it


def reject_reason(finding: dict, sources: dict[str, list[str]], rules: set[str] | None) -> str:
    for check in CHECKS:
        reason = check(finding, sources, rules)
        if reason:
            return reason
    return ""


def check_findings(findings: list[dict], sources: dict[str, list[str]], rules: set[str] | None = None) -> Checked:
    result = Checked()
    for finding in findings:
        reason = reject_reason(finding, sources, rules)
        if reason:
            result.discarded.append({**finding, "discard_reason": reason})
        else:
            result.kept.append(finding)
    return result
