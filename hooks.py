from __future__ import annotations

from scripts.generate_updates import main as generate_updates


def on_pre_build(config) -> None:
    generate_updates()
