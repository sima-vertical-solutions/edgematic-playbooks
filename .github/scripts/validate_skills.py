#!/usr/bin/env python3
"""Check every skill in this repo against what sima-cli's installer requires.

Run it from the repository root:

    python3 .github/scripts/validate_skills.py

Deliberately dependency-free — no PyYAML, no sima-cli. The manifests here are
flat `key: value` files, so a real YAML parser would buy nothing and would make
this fail for a reason that has nothing to do with the skills.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"

# A directory holding any of these is a playbook root as far as sima-cli is
# concerned. One at the repo root would make the WHOLE repository a single
# playbook and every real skill would vanish from the install.
ROOT_MARKERS = (
    "SKILL.md",
    "AGENTS.md",
    "playbook.yml",
    "playbook.yaml",
    "skill.yaml",
    "skill.yml",
    "rule.yaml",
    "rule.yml",
    "manifest.json",
)

# sima-cli installs a skill into <agent home>/skills/<id> for each agent listed,
# and only these two are supported. A skill omitting one is silently installed
# for the other only — and `read_skill` resolves exactly one provider-derived
# root with no fallback, so the agent that missed out is told the skill exists
# and cannot open it.
REQUIRED_AGENTS = {"codex", "claude"}

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def parse_flat_yaml(text: str) -> dict[str, str]:
    """Top-level `key: value` pairs. Nested blocks are skipped, not parsed."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("#") or line[0].isspace():
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def frontmatter_of(path: Path) -> dict[str, str] | None:
    """The YAML frontmatter block of a Markdown file, or None if absent."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
    if match is None:
        fail(f"{path.relative_to(REPO)}: frontmatter has no closing '---'")
        return None
    return parse_flat_yaml(match.group(1))


def check_repo_root() -> None:
    for marker in ROOT_MARKERS:
        if (REPO / marker).exists():
            fail(
                f"{marker} at the repository root would make sima-cli treat the "
                "whole repo as ONE playbook, hiding every real skill"
            )


def check_skill(skill: Path) -> None:
    rel = skill.relative_to(REPO)
    doc = skill / "SKILL.md"
    manifest = skill / "playbook.yml"

    if not doc.is_file():
        fail(f"{rel}: no SKILL.md")
    if not manifest.is_file():
        fail(f"{rel}: no playbook.yml")
    if not doc.is_file() or not manifest.is_file():
        return

    fields = parse_flat_yaml(manifest.read_text(encoding="utf-8"))

    # id, directory name and the SKILL.md frontmatter name must agree: sima-cli
    # derives the installed id from the manifest, so a mismatch installs the
    # skill under a name the agent was never told about.
    manifest_id = fields.get("id", "")
    if manifest_id != skill.name:
        fail(f"{rel}: playbook.yml id is {manifest_id!r}, directory is {skill.name!r}")

    front = frontmatter_of(doc)
    if front is None:
        fail(f"{rel}/SKILL.md: no YAML frontmatter")
    else:
        if front.get("name", "") != skill.name:
            fail(
                f"{rel}/SKILL.md: frontmatter name is {front.get('name', '')!r}, "
                f"directory is {skill.name!r}"
            )
        if not front.get("description"):
            fail(
                f"{rel}/SKILL.md: frontmatter has no description — it is the "
                "signal an agent routes on"
            )

    raw_agents = fields.get("agents", "")
    agents = {a.strip().lower() for a in raw_agents.strip("[]").split(",") if a.strip()}
    missing = REQUIRED_AGENTS - agents
    if missing:
        fail(
            f"{rel}: playbook.yml agents is {raw_agents!r}, missing "
            f"{sorted(missing)} — the skill installs for one agent only"
        )

    if not fields.get("version"):
        fail(f"{rel}: playbook.yml has no version")


def main() -> int:
    if not SKILLS.is_dir():
        print("error: no skills/ directory", file=sys.stderr)
        return 1

    check_repo_root()

    skills = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    if not skills:
        print("error: skills/ holds no skills", file=sys.stderr)
        return 1

    for skill in skills:
        check_skill(skill)

    if errors:
        print(f"{len(errors)} problem(s) found:\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK — {len(skills)} skills valid: {', '.join(s.name for s in skills)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
