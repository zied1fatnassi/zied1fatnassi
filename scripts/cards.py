#!/usr/bin/env python3
"""Generate SVG repository cards and statistics cards for Zied Fatnassi's GitHub profile.

Supports Dark and Light themes, resilient API queries with local fallbacks,
and responsive SVG rendering.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif,'Apple Color Emoji','Segoe UI Emoji'"

THEMES = {
    "dark": {
        "bg": "#0D1117",
        "border": "#30363D",
        "title": "#58A6FF",
        "value": "#00F5D4",
        "text": "#C9D1D9",
        "muted": "#8B949E",
        "accent": "#00F5D4",
        "badge_bg": "#161B22",
    },
    "light": {
        "bg": "#FFFFFF",
        "border": "#D0D7DE",
        "title": "#0969DA",
        "value": "#059669",
        "text": "#24292F",
        "muted": "#57606A",
        "accent": "#059669",
        "badge_bg": "#F6F8FA",
    },
}

LANG_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "React": "#61DAFB",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "SQL": "#e38c00",
    "Shell": "#89e051",
    "Docker": "#384d54",
}

ICON_REPO = "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.6-1.2-1.6 1.2a.25.25 0 0 1-.4-.2Z"
ICON_STAR = "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"
ICON_FORK = "M5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm0 2.122a2.25 2.25 0 1 0-1.5 0v.878A2.25 2.25 0 0 0 5.75 8.5h4.5A2.25 2.25 0 0 0 12.5 6.25v-.878a2.25 2.25 0 1 0-1.5 0v.878a.75.75 0 0 1-.75.75h-4.5A.75.75 0 0 1 5 6.25ZM10.5 4a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Zm-4.75 7.75a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm.75-2.128A2.251 2.251 0 0 0 5 11.75a2.25 2.25 0 1 0 1.5 0v-.878A2.25 2.25 0 0 0 5.75 8.5h4.5a.75.75 0 0 0 0-1.5h-4.5A.75.75 0 0 0 5 7.75v1.872Z"
ICON_EXTERNAL = "M15 3h6v6m0-6L10 14"


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text_width(s: str, size: float) -> float:
    return len(s) * size * 0.54


def wrap(text: str, size: float, max_w: float, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and words:
        used = len(" ".join(lines).split())
        if used < len(words):
            while lines and text_width(lines[-1] + "...", size) > max_w:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
            lines[-1] += "..."
    return lines


def icon(path: str, x: float, y: float, size: float, color: str) -> str:
    scale = size / 16.0
    return (
        f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
        f'<path d="{path}" fill="{color}" fill-rule="evenodd"/>'
        f"</g>"
    )


def frame(w: int, h: int, c: dict[str, str], body: str, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{esc(label)}" '
        f'font-family="{FONT}">'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1"/>'
        f"{body}</svg>"
    )


def rest(path: str, token: str | None = None):
    url = f"https://api.github.com{path}"
    headers = {
        "User-Agent": "ZiedFatnassi-Profile-Generator",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: GitHub API request failed ({path}): {e}", file=sys.stderr)
        return None


def fetch_contributions(user: str, token: str | None = None):
    if not token:
        return None
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "ZiedFatnassi-Profile-Generator",
            "Content-Type": "application/json",
        },
        data=json.dumps({"query": query, "variables": {"user": user}}).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [
            (dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cal["weeks"]
            for d in w["contributionDays"]
        ]
        days.sort()

        longest = run = 0
        for _, c in days:
            run = run + 1 if c > 0 else 0
            longest = max(longest, run)

        current = 0
        for date, c in reversed(days):
            if c > 0:
                current += 1
            elif date != days[-1][0]:
                break
        return cal["totalContributions"], current, longest
    except Exception as e:
        print(f"Notice: GraphQL contributions failed: {e}", file=sys.stderr)
        return None


def render_stats(user: str, stats: list[tuple[str, str]], theme: str) -> str:
    c = THEMES[theme]
    pad = 22
    tiles = [(v, k) for k, v in stats]
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    rh, W = 48, 500
    H = pad + 50 + (rows - 1) * rh + 20 + pad
    tw = (W - 2 * pad) / cols

    out = [
        f'<text x="{pad}" y="{pad + 14}" font-size="15" font-weight="700" '
        f'fill="{c["title"]}">~/ {esc(user)} / metrics</text>',
        f'<text x="{W - pad}" y="{pad + 14}" font-size="11" text-anchor="end" '
        f'fill="{c["muted"]}">system overview</text>',
        f'<line x1="{pad}" y1="{pad + 26}" x2="{W - pad}" y2="{pad + 26}" '
        f'stroke="{c["border"]}"/>',
    ]
    top = pad + 56
    for i, (value, label) in enumerate(tiles):
        cx = pad + (i % cols) * tw
        cy = top + (i // cols) * rh
        out.append(
            f'<text x="{cx:.0f}" y="{cy:.0f}" font-size="22" font-weight="700" '
            f'fill="{c["value"]}">{esc(value)}</text>'
        )
        out.append(
            f'<text x="{cx:.0f}" y="{cy + 17:.0f}" font-size="10.5" '
            f'fill="{c["muted"]}">{esc(label)}</text>'
        )
    return frame(W, H, c, "".join(out), f"{user} GitHub statistics")


def render_repo(repo: dict, theme: str) -> str:
    c = THEMES[theme]
    W, H = 430, 140
    pad = 18
    out = []

    out.append(icon(ICON_REPO, pad, pad, 15, c["accent"]))
    display_title = repo.get("display_name") or repo["name"]
    out.append(
        f'<text x="{pad + 24}" y="{pad + 12}" font-size="14" font-weight="700" '
        f'fill="{c["title"]}">{esc(display_title)}</text>'
    )

    desc = repo.get("description") or "Production codebase."
    for i, line in enumerate(wrap(desc, 11, W - 2 * pad, 3)):
        out.append(
            f'<text x="{pad}" y="{pad + 38 + i * 16}" font-size="11" '
            f'fill="{c["text"]}">{esc(line)}</text>'
        )

    fy = H - pad - 2
    x = pad
    lang = repo.get("language")
    if lang:
        col = LANG_COLORS.get(lang, c["muted"])
        out.append(f'<circle cx="{x + 5}" cy="{fy - 4}" r="5" fill="{col}"/>')
        out.append(
            f'<text x="{x + 15}" y="{fy}" font-size="11" fill="{c["muted"]}">'
            f'{esc(lang)}</text>'
        )
        x += 15 + text_width(lang, 11) + 16

    for path, count in ((ICON_STAR, repo.get("stars", 0)), (ICON_FORK, repo.get("forks", 0))):
        out.append(icon(path, x, fy - 11, 12, c["muted"]))
        out.append(
            f'<text x="{x + 16}" y="{fy}" font-size="11" fill="{c["muted"]}">'
            f'{count}</text>'
        )
        x += 16 + text_width(str(count), 11) + 16

    if repo.get("live_url"):
        out.append(
            f'<rect x="{W - pad - 62}" y="{fy - 14}" width="62" height="18" rx="4" '
            f'fill="{c["badge_bg"]}" stroke="{c["border"]}"/>'
            f'<text x="{W - pad - 31}" y="{fy - 2}" font-size="9.5" font-weight="600" '
            f'fill="{c["accent"]}" text-anchor="middle">LIVE DEMO</text>'
        )

    return frame(W, H, c, "".join(out), f'{repo["name"]} repository card')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--user", default="zied1fatnassi")
    p.add_argument("--out", type=Path, default=Path("assets"))
    p.add_argument(
        "--projects",
        type=Path,
        default=Path("assets/projects.json"),
        help="JSON file defining curated projects",
    )
    args = p.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    args.out.mkdir(parents=True, exist_ok=True)

    user_data = rest(f"/users/{args.user}", token)
    repos = []
    if user_data:
        batch = rest(f"/users/{args.user}/repos?per_page=100&type=owner", token)
        if batch and isinstance(batch, list):
            repos = batch

    public_repos = user_data["public_repos"] if user_data else 4
    followers = user_data["followers"] if user_data else 1
    stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork", False))

    tiles = [
        ("Total stars", f"{stars:,}"),
        ("Public repos", f"{public_repos:,}"),
        ("Followers", f"{followers:,}"),
    ]

    contrib = fetch_contributions(args.user, token)
    if contrib:
        total, current, longest = contrib
        tiles += [
            ("Contributions (1y)", f"{total:,}"),
            ("Current streak", f"{current:,}"),
            ("Longest streak", f"{longest:,}"),
        ]
    else:
        # Verified baseline metrics
        tiles += [
            ("Primary Focus", "AI Agents"),
            ("Status", "Building MatchOp"),
            ("Ecosystem", "GDG / GDSC"),
        ]

    for theme in ("dark", "light"):
        dest = args.out / f"card-stats-{theme}.svg"
        dest.write_text(render_stats(args.user, tiles, theme), encoding="utf-8")
    print(f"[OK] Wrote card-stats-*.svg ({len(tiles)} tiles)")

    if not args.projects.exists():
        print(f"Warning: {args.projects} not found.")
        return

    wanted = json.loads(args.projects.read_text(encoding="utf-8")).get("projects", [])
    by_name = {r["name"].lower(): r for r in repos} if repos else {}

    for entry in wanted:
        repo_key = entry["repo"].lower()
        src = by_name.get(repo_key, {})
        card = {
            "name": entry["repo"],
            "display_name": entry.get("display_name", entry["repo"]),
            "description": entry.get("description") or src.get("description", ""),
            "language": entry.get("language") or src.get("language", "TypeScript"),
            "stars": src.get("stargazers_count", entry.get("stars", 0)),
            "forks": src.get("forks_count", entry.get("forks", 0)),
            "live_url": entry.get("live_url", ""),
        }
        for theme in ("dark", "light"):
            dest = args.out / f"card-{entry['repo']}-{theme}.svg"
            dest.write_text(render_repo(card, theme), encoding="utf-8")
        print(f"[OK] Wrote card-{entry['repo']}-*.svg")


if __name__ == "__main__":
    main()
