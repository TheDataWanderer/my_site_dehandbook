from __future__ import annotations

import re
import subprocess
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
UPDATES_FILE = DOCS_DIR / "_meta" / "updates.md"
MAX_ITEMS = 12


def clean_title(title: str) -> str:
    return title.strip().strip("*_` ")


def run_git(args: list[str]) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def collect_nav_titles() -> dict[str, str]:
    config_path = ROOT / "mkdocs.yml"
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    titles: dict[str, str] = {}
    parents_by_indent: dict[int, str] = {}
    in_nav = False

    for line in lines:
        if line.strip() == "nav:":
            in_nav = True
            continue
        if in_nav and line and not line.startswith(" "):
            break
        if not in_nav:
            continue

        match = re.match(r"^(\s*)-\s+(.+?):(?:\s+(.+))?$", line)
        if not match:
            continue

        indent = len(match.group(1))
        title = match.group(2).strip().strip("'\"")
        value = (match.group(3) or "").strip().strip("'\"")

        for known_indent in list(parents_by_indent):
            if known_indent >= indent:
                del parents_by_indent[known_indent]

        if value.endswith(".md"):
            normalized = value.replace("\\", "/")
            parent_title = parents_by_indent.get(max(parents_by_indent, default=-1), "")
            if title == "Обзор" and normalized.endswith("/index.md") and parent_title:
                titles[normalized] = parent_title
            else:
                titles[normalized] = title
        else:
            parents_by_indent[indent] = title

    return titles


def fallback_title(relative_path: str, nav_titles: dict[str, str]) -> str:
    if relative_path in nav_titles:
        return nav_titles[relative_path]

    path = Path(relative_path)
    if path.name == "index.md" and len(path.parts) > 1:
        return path.parts[-2].replace("_", " ").title()

    return path.stem.replace("_", " ").title()


def page_title(path: Path, relative_path: str, nav_titles: dict[str, str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return fallback_title(relative_path, nav_titles)

    for line in text.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return clean_title(match.group(1))

    if relative_path in nav_titles:
        return nav_titles[relative_path]

    for line in text.splitlines():
        match = re.match(r"^#{2,6}\s+(.+)$", line.strip())
        if match:
            return clean_title(match.group(1))

    return fallback_title(relative_path, nav_titles)


def section_name(relative_path: str) -> str:
    parts = Path(relative_path).parts

    if not parts:
        return "Сайт"
    if parts[0] == "knowledge":
        return "База знаний"
    if parts[0] == "courses":
        if len(parts) > 1 and parts[1] == "excel":
            return "Курс Excel"
        if len(parts) > 1 and parts[1] == "postgresql":
            return "Курс PostgreSQL"
        return "Курсы"

    return {
        "index.md": "Главная",
        "about.md": "Обо мне",
        "projects.md": "Проекты",
        "media.md": "Медиа",
        "resources.md": "Полезные ресурсы",
    }.get(relative_path, "Сайт")


def collect_updates() -> OrderedDict[str, dict[str, str]]:
    log = run_git(["log", "--date=short", "--format=%ad", "--name-only", "--", "docs"])
    updates: OrderedDict[str, dict[str, str]] = OrderedDict()
    nav_titles = collect_nav_titles()
    current_date = ""

    for raw_line in log.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if re.match(r"^\d{4}-\d{2}-\d{2}$", line):
            current_date = line
            continue

        if not current_date:
            continue
        if not line.startswith("docs/") or not line.endswith(".md"):
            continue
        if line == "docs/_meta/updates.md":
            continue

        relative = line.removeprefix("docs/")
        page_path = DOCS_DIR / relative
        if not page_path.exists():
            continue
        if relative in updates:
            continue

        updates[relative] = {
            "date": current_date,
            "section": section_name(relative),
            "title": page_title(page_path, relative, nav_titles),
            "link": relative.replace("\\", "/"),
        }

        if len(updates) >= MAX_ITEMS:
            break

    return updates


def render_updates(updates: OrderedDict[str, dict[str, str]]) -> str:
    lines = [
        "<!-- Этот файл генерируется автоматически из истории git. -->",
        "<!-- Не редактируйте его вручную: изменения будут перезаписаны при сборке сайта. -->",
        "",
    ]

    if not updates:
        lines.append("_Пока нет данных об обновлениях._")
        return "\n".join(lines) + "\n"

    for item in updates.values():
        lines.append(
            f"- **{item['date']}** - {item['section']}: "
            f"[{item['title']}]({item['link']})"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    UPDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    UPDATES_FILE.write_text(render_updates(collect_updates()), encoding="utf-8")


if __name__ == "__main__":
    main()
