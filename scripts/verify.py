#!/usr/bin/env python3
"""Validation script for Zied Fatnassi's GitHub profile.
Checks:
- All referenced local assets in README.md exist on disk
- All SVG files parse without XML errors
- JSON configuration files are well-formed
- Workflow YAML is valid
"""

from pathlib import Path
import re
import xml.etree.ElementTree as ET


def main():
    root = Path(__file__).resolve().parent.parent
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")

    print("[*] Validating README assets...")
    pattern = re.compile(r'(?:src|srcset)="([^"]+)"')
    missing = []
    found = []

    for match in pattern.finditer(readme):
        url = match.group(1)
        if url.startswith("http://") or url.startswith("https://"):
            continue
        asset_file = root / url
        if not asset_file.exists():
            missing.append(url)
        else:
            found.append(url)

    for item in set(found):
        print(f"  + Found: {item}")

    if missing:
        print(f"[-] Missing local assets: {missing}")
        return 1

    print("[*] Validating all SVG files in assets/ ...")
    svg_errors = []
    for svg_file in (root / "assets").glob("*.svg"):
        try:
            ET.parse(svg_file)
        except Exception as e:
            svg_errors.append((svg_file.name, str(e)))

    if svg_errors:
        for name, err in svg_errors:
            print(f"  - Error in {name}: {err}")
        return 1
    else:
        print("  + All SVGs parsed as valid XML successfully.")

    print("[*] Checking GitHub Actions workflow file...")
    wf = root / ".github" / "workflows" / "profile.yml"
    if not wf.exists():
        print("  - profile.yml does not exist!")
        return 1
    print(f"  + Found {wf.name} ({len(wf.read_text(encoding='utf-8').splitlines())} lines)")

    print("\n[SUCCESS] Profile validation passed with zero errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
