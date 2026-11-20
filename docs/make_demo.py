"""Render docs/demo.gif from the real output of the kit commands (no mock text).

    python docs/make_demo.py      (needs Pillow; runs from the repository root)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "kit"
OUT = ROOT / "docs" / "demo.gif"
FONT_NAMES = ("consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc", "LiberationMono-Regular.ttf")
REPORT = "<tmp>/report.json"  # shown as-is; replaced by a private temp file when run
LINE_H, PAD, WIDTH, ROWS = 21, 16, 1240, 15
COLORS = {"#": "#7f899b", "$": "#eef1f6", "K": "#3ecf8e", "D": "#ff7a33", "v": "#f2c14e"}
STEPS = [  # (caption, command, exit code the demo must see)
    ("# 1) The lint hook rejects code an agent cannot be held to", ["rsh_lint.py", "check", "examples/bad_unit.py"], 1),
    ("# 2) The audit keeps real findings and drops invented evidence",
     ["rsh_audit.py", "--spec", "examples/spec_step01.md", "--files", "examples/good_unit.py",
      "--response-file", "examples/auditor_answer.json", "--out", REPORT], 0),
]


def default_font() -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=15)
    except TypeError:  # Pillow before 10.1 has no size argument
        return ImageFont.load_default()


def load_font() -> ImageFont.ImageFont:
    for name in FONT_NAMES:
        try:
            return ImageFont.truetype(name, 15)
        except OSError:
            continue
    return default_font()


def require_exit(done: subprocess.CompletedProcess, name: str, expected: int) -> None:
    if done.returncode != expected:
        raise SystemExit(f"demo aborted: {name} exited {done.returncode}, expected {expected}\n{done.stderr}")


def run(args: list[str], report: str, expected: int) -> list[str]:
    real = [report if arg == REPORT else arg for arg in args]
    done = subprocess.run([sys.executable, *real], cwd=KIT, capture_output=True, text=True, timeout=60)
    require_exit(done, args[0], expected)
    return [line for line in done.stdout.splitlines() if line.strip()]


def color_of(line: str) -> str:
    key = "K" if line.startswith("KEPT") else "D" if line.startswith("DISCARDED") else line[:1]
    return COLORS.get("v" if line.startswith("verdict") else key, "#b9c0cd")


def render(lines: list[str], font: ImageFont.ImageFont) -> Image.Image:
    image = Image.new("RGB", (WIDTH, PAD * 2 + LINE_H * ROWS), "#0c0e12")
    draw = ImageDraw.Draw(image)
    for row, line in enumerate(lines[-ROWS:]):
        draw.text((PAD, PAD + row * LINE_H), line, font=font, fill=color_of(line))
    return image


def typed(screen: list[str], text: str) -> list[tuple[list[str], int]]:
    frames = [(screen + [text[:end]], 35) for end in range(4, len(text), 4)]
    return frames + [(screen + [text], 400)]


def frames(report: str) -> list[tuple[list[str], int]]:
    screen: list[str] = []
    out: list[tuple[list[str], int]] = []
    for caption, args, expected in STEPS:
        screen = screen + ([""] if screen else []) + [caption]
        command = "$ python " + " ".join(args)
        out += typed(screen, command)
        screen = screen + [command]
        for line in run(args, report, expected):
            screen = screen + [line]
            out.append((screen, 350))
        out.append((screen, 1800))
    return out


def main() -> int:
    font = load_font()
    with tempfile.TemporaryDirectory() as tmp:
        shots = frames(str(Path(tmp) / "report.json"))
    images = [render(lines, font) for lines, _ in shots]
    images[0].save(OUT, save_all=True, append_images=images[1:], duration=[ms for _, ms in shots], loop=0)
    print(f"{OUT} ({len(images)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
