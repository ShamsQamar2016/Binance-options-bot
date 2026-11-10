"""FULL_CODE.md ни ясайди: лойиҳанинг ҳамма файллари битта Markdown файлда (аудит учун).

Ишлатиш:
    python make_full_code.py          # FULL_CODE.md ни охирги коммит асосида қайта ясайди
    python make_full_code.py --check  # FULL_CODE.md эскирганми — текширади (эскирган бўлса, чиқиш коди 1)

GitHub'да `.github/workflows/full-code.yml` бу скриптни ҳар push'дан кейин ишга туширади ва FULL_CODE.md
ўзгарган бўлса, уни автоматик коммит қилади. Файл фақат коммит қилинган кодга қараб ясалади, шунинг учун
бир хил код учун ҳар доим бир хил FULL_CODE.md чиқади.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_NAME = "FULL_CODE.md"
SKIP = {OUT_NAME, ".gitignore"}

# Ўқиш учун қулай тартиб; рўйхатда йўқ янги файллар охирига алфавит бўйича қўшилади
ORDER = [
    "README.md", "requirements.txt", ".env.example",
    "serial.py", "series_planner.py", "claude_client.py", "fileutil.py",
    "book_sources.py", "book_reader.py", "visuals.py", "fal_api.py", "dubbing.py", "sound.py",
    "episode_builder.py", "telegram_sender.py", "video.py", "check_script.py", "make_full_code.py",
    "main.py", "scenario.py",
]
DESCRIPTIONS = {
    "README.md": "Қўлланма: ўрнатиш ва ишлатиш",
    "requirements.txt": "Керакли Python кутубхоналари",
    ".env.example": "Калитлар ва созламалар намунаси",
}
LANGS = {".py": "python", ".md": "markdown", ".txt": "text", ".example": "bash", ".yml": "yaml", ".json": "json"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def committed_files() -> list[str]:
    names = [n for n in git("ls-tree", "--name-only", "HEAD", "./").splitlines() if n]
    names = [Path(n).name for n in names]
    files = [n for n in names if n not in SKIP and not git("cat-file", "-t", f"HEAD:./{n}").startswith("tree")]
    known = [n for n in ORDER if n in files]
    return known + sorted(n for n in files if n not in ORDER)


def describe(name: str, text: str) -> str:
    if name in DESCRIPTIONS:
        return DESCRIPTIONS[name]
    if name.endswith(".py"):
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            doc = ""
        if doc:
            return doc.strip().splitlines()[0].rstrip(".")
    return ""


def build() -> str:
    version = git("log", "-1", "--format=%h|%cs", "--", ".", f":(exclude){OUT_NAME}").strip()
    sha, date = version.split("|") if version else ("—", "—")
    files = committed_files()
    contents = {n: git("show", f"HEAD:./{n}") for n in files}
    fence = "````"
    while any(fence in c for c in contents.values()):
        fence += "`"

    lines = [
        "# book_to_video — тўлиқ код",
        "",
        "> Бу файл `make_full_code.py` орқали автоматик ясалади — уни қўлда таҳрирламанг.",
        "",
        f"Код версияси: коммит `{sha}` ({date}). Файллар: {len(files)} та, жами "
        f"{sum(c.count(chr(10)) for c in contents.values())} қатор.",
        "",
        "| № | Файл | Вазифаси | Қатор | Охирги ўзгариш |",
        "|---|---|---|---|---|",
    ]
    for i, name in enumerate(files, 1):
        last = git("log", "-1", "--format=%h (%cs)", "--", name).strip() or "—"
        lines.append(f"| {i} | `{name}` | {describe(name, contents[name])} | {contents[name].count(chr(10))} | {last} |")
    lines.append("")
    for i, name in enumerate(files, 1):
        lang = LANGS.get(Path(name).suffix, "")
        lines += ["---", "", f"## {i}. `{name}`", ""]
        if describe(name, contents[name]):
            lines += [describe(name, contents[name]), ""]
        lines += [f"{fence}{lang}", contents[name].rstrip("\n"), fence, ""]
    return "\n".join(lines)


def main() -> int:
    out = HERE / OUT_NAME
    text = build()
    current = out.read_text(encoding="utf-8") if out.exists() else ""
    if "--check" in sys.argv:
        if current != text:
            print(f"{OUT_NAME} эскирган: python make_full_code.py ни ишга туширинг")
            return 1
        print(f"{OUT_NAME} янги")
        return 0
    if git("status", "--porcelain", "--", ".", f":(exclude){OUT_NAME}").strip():
        print("⚠️  Коммит қилинмаган ўзгаришлар бор — улар FULL_CODE.md га кирмайди (фақат охирги коммит олинади).")
    if current == text:
        print(f"{OUT_NAME} ўзгармади")
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"✓ {OUT_NAME} янгиланди")
    return 0


if __name__ == "__main__":
    sys.exit(main())
