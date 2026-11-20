import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))

import rsh_lint  # noqa: E402


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def rules_of(path: Path) -> list[str]:
    return [issue.rule for issue in rsh_lint.check_file(path)]


def test_bad_example_is_caught():
    assert sorted(rules_of(KIT / "examples" / "bad_unit.py")) == ["R03", "R05", "R06"]


def test_kit_passes_its_own_lint():
    offenders = [str(i) for i in rsh_lint.check_paths([str(KIT)]) if "bad_unit" not in i.path]
    assert offenders == []


def test_file_length(tmp_path):
    path = write(tmp_path, "long.py", "x = 1\n" * 201)
    assert rules_of(path) == ["R01"]


def test_function_length_ignores_blank_comment_and_docstring(tmp_path):
    body = '    """doc\n    more doc\n    """\n' + "    # note\n\n" * 10 + "    x = 1\n" * 35
    assert rules_of(write(tmp_path, "ok.py", "def f():\n" + body)) == []
    assert rules_of(write(tmp_path, "big.py", "def f():\n" + body + "    x = 2\n")) == ["R02"]


def test_complexity_counts_branches_and_boolean_operators(tmp_path):
    five = "def f(a, b):\n    if a and b:\n        return 1\n    for i in a:\n        if i:\n            return i\n"
    six = five + "    while b:\n        b -= 1\n"
    assert rules_of(write(tmp_path, "five.py", five)) == []
    assert rules_of(write(tmp_path, "six.py", six)) == ["R03"]


def test_nested_functions_are_measured_separately(tmp_path):
    inner = "    def inner(a):\n" + "".join(f"        if a == {i}:\n            return {i}\n" for i in range(5))
    code = "def outer(x):\n" + inner + "    return inner(x)\n"
    issues = [i.message for i in rsh_lint.check_file(write(tmp_path, "nest.py", code))]
    assert issues == ["inner: complexity 6 > 5"]


def test_comprehension_loops_count(tmp_path):
    loops = " ".join(f"for v{i} in range(2)" for i in range(5))
    code = f"def f():\n    return [1 {loops}]\n"
    assert rules_of(write(tmp_path, "comp.py", code)) == ["R03"]


def test_swallowed_except_and_sleep(tmp_path):
    nap = "time." + "sleep"  # built at runtime so this test file itself stays lint-clean
    code = ("import time\ntry:\n    x = 1\nexcept ValueError:\n    pass\n"
            f"{nap}(1)\n{nap}(2)  # rate-limit: api quota\n")
    assert rules_of(write(tmp_path, "p.py", code)) == ["R05", "R06"]


def test_syntax_error_is_reported(tmp_path):
    assert rules_of(write(tmp_path, "broken.py", "def f(:\n")) == ["R00"]


def test_hook_blocks_bad_python_and_ignores_others(tmp_path, capsys):
    bad = str(KIT / "examples" / "bad_unit.py")
    assert rsh_lint.run_hook(json.dumps({"tool_input": {"file_path": bad}})) == 2
    assert "R05" in capsys.readouterr().err
    assert rsh_lint.run_hook(json.dumps({"tool_input": {"file_path": str(KIT / "examples" / "good_unit.py")}})) == 0
    assert rsh_lint.run_hook(json.dumps({"tool_input": {"file_path": "notes.md"}})) == 0
    assert rsh_lint.run_hook("not json") == 0
    assert rsh_lint.run_hook("[1, 2]") == 0


def test_cli_exit_codes(tmp_path):
    assert rsh_lint.main(["check", str(KIT / "examples" / "good_unit.py")]) == 0
    assert rsh_lint.main(["check", str(KIT / "examples" / "bad_unit.py")]) == 1
    assert rsh_lint.main([]) == 2
    assert rsh_lint.main(["check"]) == 2
