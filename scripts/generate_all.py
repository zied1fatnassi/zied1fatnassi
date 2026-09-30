#!/usr/bin/env python3
"""Unified generation orchestrator for Zied Fatnassi's GitHub profile assets.
Generates:
- card-stats-dark.svg & card-stats-light.svg
- card-<repo>-dark.svg & card-<repo>-light.svg
- radar-dark.svg & radar-light.svg (Capabilities)
- radar-langs-dark.svg & radar-langs-light.svg (Language distribution)
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def run():
    root = Path(__file__).resolve().parent.parent
    scripts = root / "scripts"
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    print("=== Generating Repository and Stats Cards ===")
    subprocess.run(
        [
            sys.executable,
            str(scripts / "cards.py"),
            "--user",
            "zied1fatnassi",
            "--out",
            str(assets),
            "--projects",
            str(assets / "projects.json"),
        ],
        check=True,
    )

    print("\n=== Generating Capability Radar Charts ===")
    subprocess.run(
        [
            sys.executable,
            str(scripts / "radar.py"),
            "--data",
            str(assets / "skills.json"),
            "-o",
            str(assets / "radar"),
        ],
        check=True,
    )

    print("\n=== Generating Language Mix Radar Charts ===")
    subprocess.run(
        [
            sys.executable,
            str(scripts / "radar.py"),
            "--langs",
            "-o",
            str(assets / "radar-langs"),
        ],
        check=True,
    )

    print("\n[SUCCESS] All profile assets generated successfully.")


if __name__ == "__main__":
    run()
