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
# Two trees, because they install separately: a default Edgematic Studio install
# takes `skills/` alone, and `skills-ros/` is added only when ROS is asked for.
# Installed skills are visible to any agent reading the skill homes, Studio's or
# not, so a ROS skill in the wrong tree cannot be hidden later.
SKILLS = REPO / "skills"
SKILLS_ROS = REPO / "skills-ros"
TREES = (SKILLS, SKILLS_ROS)

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
    check_frontmatter_is_real_yaml(path, match.group(1))
    return parse_flat_yaml(match.group(1))


def check_frontmatter_is_real_yaml(path: Path, block: str) -> None:
    """Catch frontmatter this parser accepts and a real YAML parser rejects.

    `parse_flat_yaml` partitions on the first colon and never validates, so an
    unquoted value containing a colon-space reads as `key: value` here and as a
    nested mapping to PyYAML — which is what sima-cli uses. The installer then
    discards the skill with "mapping values are not allowed here", and the only
    visible symptom is a skill that is silently absent from the agent's roster.

    Checked textually rather than with a YAML library on purpose: this script is
    dependency-free so it fails for reasons about skills and nothing else.
    """
    for lineno, line in enumerate(block.splitlines(), start=2):
        if not line or line.startswith("#") or line[0].isspace() or ":" not in line:
            continue
        value = line.partition(":")[2].strip()
        if value[:1] in ("'", '"'):
            continue
        if ": " in value:
            fail(
                f"{path.relative_to(REPO)}:{lineno}: the value contains a "
                "colon-space, which a real YAML parser reads as a nested "
                "mapping — sima-cli discards the skill. Reword it (an em dash "
                "reads well) or quote the whole value."
            )


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


def check_robot_tui_workspace_contract() -> None:
    """Keep the TUI flow off the projects root that Studio cannot adopt."""
    flow = (
        SKILLS_ROS
        / "edgematic-robot-tui"
        / "references"
        / "automatic-flow.md"
    )
    if not flow.is_file():
        fail(f"{flow.relative_to(REPO)}: missing Robot TUI automatic flow")
        return

    text = flow.read_text(encoding="utf-8")
    skill = flow.parents[1] / "SKILL.md"
    combined = text + "\n" + skill.read_text(encoding="utf-8")
    required = (
        '"parent": "/workspace/robot-tui-demo"',
        "Never use `/workspace` itself",
        "selected dedicated parent",
        "<selected-workspace-parent>/<application>/src",
    )
    for phrase in required:
        if phrase not in text:
            fail(
                f"{flow.relative_to(REPO)}: missing workspace-safety contract "
                f"{phrase!r}"
            )

    forbidden = (
        '"parent": "/workspace",',
        "on the shared `/workspace` parent",
        "`parent`: `/workspace/<application>/src`",
        "`set_ros_pipelines`",
        "`run_command`",
    )
    for phrase in forbidden:
        if phrase in combined:
            fail(
                f"{flow.relative_to(REPO)}: unsafe or unavailable Robot TUI "
                f"instruction remains: {phrase!r}"
            )


# Edgematic Studio can be told that the legacy ROS 2 client repository does not
# exist for a deployment. It enforces that by hiding every installed skill whose
# TEXT names the repository — a skill is prose the model reads, so no tool gate
# can reach it, and reading the text is the only check that works on a skill set
# we install but do not control.
#
# The consequence for this repository is that a mention is load-bearing: one
# passing mention hides the whole skill, and the failure is silent, because a
# hidden skill looks exactly like a skill that was never installed. So no skill
# here names the repository.
LEGACY_REPO_SLUG = "vdp-simaai-ros2"


def check_legacy_repo_mentions(skill: Path) -> None:
    """No skill may name the legacy repository: naming it hides the skill."""
    for path in sorted(skill.rglob("*")):
        if not path.is_file() or path.suffix not in (".md", ".yml", ".yaml"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if LEGACY_REPO_SLUG in line:
                rel = path.relative_to(REPO)
                fail(
                    f"{rel}:{lineno}: names `{LEGACY_REPO_SLUG}`; Studio hides every "
                    "skill that names it on a deployment that has disowned that "
                    "repository. Describe the workspace without its name."
                )


# These names belong in user project evidence, never in distributable skills.
# Keep the check outside skills/ so the prohibited defaults are not agent input.
ROBOT_SPECIFIC_CONTENT = re.compile(
    r"rosbot[ _-]*xl|husarion|\bstiga\b|\bedgebot\b|"
    r"yolov8_(?:seg_)?rover|rosbot-xl-profile",
    re.IGNORECASE,
)


def check_robot_agnostic_content(skill: Path) -> None:
    for path in sorted(skill.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO).as_posix()
        if ROBOT_SPECIFIC_CONTENT.search(relative):
            fail(f"{relative}: robot-specific filename in shared skills")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"{relative}: non-text asset requires an explicit content audit")
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            if ROBOT_SPECIFIC_CONTENT.search(line):
                fail(f"{relative}:{lineno}: robot-specific content in shared skills")


# What marks a skill as belonging in `skills-ros/`. Patterns rather than a list of
# tool names, so a tool or skill added later is covered without touching this.
ROS_CONTENT = re.compile(
    r"\bROS\b|(?i:\bros2|\bros_|_ros_|colcon|foxglove|edgematic-ros|edgematic-robot)"
)


def check_base_skill_is_not_ros(skill: Path) -> None:
    """A base skill reaches every install, so it must not be about ROS.

    Also what stops a new ROS skill merged from another branch landing in
    `skills/` and quietly becoming part of every install.
    """
    for path in sorted(skill.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO)
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            match = ROS_CONTENT.search(line)
            if match:
                fail(
                    f"{rel}:{lineno}: mentions {match.group(0)!r}, but skills/ is "
                    "installed everywhere. Move a ROS skill to skills-ros/, or "
                    "reword a passing mention."
                )


MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")


def check_relative_links(tree: Path, skill: Path) -> None:
    """A relative link must resolve, and must stay inside its own tree.

    Installed skills sit side by side while this repo has two trees, so a link
    between the trees cannot be right in both places. And when only `skills/` is
    installed, a link from it into `skills-ros/` points at nothing. Name the other
    skill in prose instead.
    """
    for doc in sorted(skill.rglob("*.md")):
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            for target in MARKDOWN_LINK.findall(line):
                if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith(("#", "/")):
                    continue
                resolved = (doc.parent / target.split("#", 1)[0]).resolve()
                rel = doc.relative_to(REPO)
                if not resolved.is_relative_to(tree.resolve()):
                    fail(f"{rel}:{lineno}: link {target!r} leaves {tree.name}/")
                elif not resolved.exists():
                    fail(f"{rel}:{lineno}: link {target!r} does not resolve")


def main() -> int:
    check_repo_root()

    skills: list[Path] = []
    for tree in TREES:
        found = sorted(p for p in tree.iterdir() if p.is_dir()) if tree.is_dir() else []
        if not found:
            print(f"error: {tree.name}/ holds no skills", file=sys.stderr)
            return 1
        for skill in found:
            check_skill(skill)
            check_legacy_repo_mentions(skill)
            check_robot_agnostic_content(skill)
            check_relative_links(tree, skill)
            if tree == SKILLS:
                check_base_skill_is_not_ros(skill)
        skills.extend(found)
    check_robot_tui_workspace_contract()

    # Both trees install into one flat skill home, so the second copy would
    # silently overwrite the first on any install that takes both.
    names = [s.name for s in skills]
    for name in sorted({n for n in names if names.count(n) > 1}):
        fail(f"{name}: present in both skills/ and skills-ros/")

    if errors:
        print(f"{len(errors)} problem(s) found:\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK — {len(skills)} skills valid: {', '.join(s.name for s in skills)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
