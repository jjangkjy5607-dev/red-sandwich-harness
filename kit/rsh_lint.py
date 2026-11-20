"""Red-Sandwich lite lint: small, checkable units for AI-written Python.

Rules (numbers follow the full harness):
  R01 file longer than 200 lines
  R02 function longer than 35 logic lines (blank, comment and docstring lines excluded)
  R03 cyclomatic complexity above 5
  R05 bare `except:` or an except block that only passes
  R06 `time.sleep` without a `# rate-limit` reason on the same line

Usage:
  python rsh_lint.py check <file-or-folder> ...   exit 1 when anything is found
  python rsh_lint.py hook                          Claude Code PostToolUse hook (reads JSON on stdin)
Standard library only.
"""
from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_LINES = 200
MAX_FUNC_LINES = 35
MAX_COMPLEXITY = 5
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist"}
BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler, ast.match_case)


@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} [{self.rule}] {self.message}"


def docstring_node(node: ast.AST) -> ast.Expr | None:
    body = getattr(node, "body", [])
    first = body[0] if body else None
    value = getattr(first, "value", None)
    is_doc = isinstance(first, ast.Expr) and isinstance(value, ast.Constant) and isinstance(value.value, str)
    return first if is_doc else None


def docstring_lines(node: ast.AST) -> set[int]:
    doc = docstring_node(node)
    if doc is None:
        return set()
    return set(range(doc.lineno, doc.end_lineno + 1))


def logic_lines(func: ast.AST, lines: list[str]) -> int:
    skip = docstring_lines(func)
    count = 0
    for no in range(func.lineno + 1, func.end_lineno + 1):
        text = lines[no - 1].strip()
        if text and not text.startswith("#") and no not in skip:
            count += 1
    return count


def own_nodes(func: ast.AST) -> list[ast.AST]:
    """Nodes of this function only: nested functions and classes are measured on their own."""
    found: list[ast.AST] = []
    stack = list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        found.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))
    return found


def complexity(func: ast.AST) -> int:
    score = 1
    for node in own_nodes(func):
        if isinstance(node, BRANCHES):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
    return score


def function_issues(path: str, tree: ast.AST, lines: list[str]) -> list[Issue]:
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        size = logic_lines(node, lines)
        if size > MAX_FUNC_LINES:
            issues.append(Issue(path, node.lineno, "R02", f"{node.name}: {size} logic lines > {MAX_FUNC_LINES}"))
        score = complexity(node)
        if score > MAX_COMPLEXITY:
            issues.append(Issue(path, node.lineno, "R03", f"{node.name}: complexity {score} > {MAX_COMPLEXITY}"))
    return issues


def swallowed(handler: ast.ExceptHandler) -> bool:
    return handler.type is None or all(isinstance(stmt, ast.Pass) for stmt in handler.body)


def is_sleep(call: ast.Call) -> bool:
    func = call.func
    return (isinstance(func, ast.Attribute) and func.attr == "sleep") or (isinstance(func, ast.Name) and func.id == "sleep")


def unexplained_sleep(node: ast.AST, lines: list[str]) -> bool:
    return isinstance(node, ast.Call) and is_sleep(node) and "# rate-limit" not in lines[node.lineno - 1]


def node_issue(path: str, node: ast.AST, lines: list[str]) -> Issue | None:
    if isinstance(node, ast.ExceptHandler) and swallowed(node):
        return Issue(path, node.lineno, "R05", "bare except or except that only passes")
    if unexplained_sleep(node, lines):
        return Issue(path, node.lineno, "R06", "sleep without '# rate-limit' reason")
    return None


def pattern_issues(path: str, tree: ast.AST, lines: list[str]) -> list[Issue]:
    found = (node_issue(path, node, lines) for node in ast.walk(tree))
    return [issue for issue in found if issue is not None]


def check_file(path: Path) -> list[Issue]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    name = path.as_posix()
    try:
        tree = ast.parse(text, filename=name)
    except SyntaxError as err:
        return [Issue(name, err.lineno or 1, "R00", f"syntax error: {err.msg}")]
    issues = []
    if len(lines) > MAX_FILE_LINES:
        issues.append(Issue(name, 1, "R01", f"{len(lines)} lines > {MAX_FILE_LINES}"))
    return issues + function_issues(name, tree, lines) + pattern_issues(name, tree, lines)


def iter_python(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix == ".py" else []
    return sorted(p for p in target.rglob("*.py") if not SKIP_DIRS.intersection(p.parts))


def check_paths(targets: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for target in targets:
        for path in iter_python(Path(target)):
            issues.extend(check_file(path))
    return issues


def run_check(targets: list[str]) -> int:
    issues = check_paths(targets)
    for issue in issues:
        print(issue)
    print(f"rsh-lint: {len(issues)} issue(s)")
    return 1 if issues else 0


def hook_path(raw: str) -> Path | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else {}
    file_path = str(tool_input.get("file_path", "")) if isinstance(tool_input, dict) else ""
    return Path(file_path) if file_path.endswith(".py") else None


def run_hook(raw: str) -> int:
    """Claude Code PostToolUse hook: exit 2 sends the findings back to the agent."""
    path = hook_path(raw)
    if path is None or not path.is_file():
        return 0
    issues = check_file(path)
    if not issues:
        return 0
    sys.stderr.write("rsh-lint blocked this edit. Split or simplify, then save again:\n")
    sys.stderr.write("\n".join(str(i) for i in issues) + "\n")
    return 2


def main(argv: list[str]) -> int:
    if argv[:1] == ["hook"]:
        return run_hook(sys.stdin.read())
    if argv[:1] == ["check"] and argv[1:]:
        return run_check(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
