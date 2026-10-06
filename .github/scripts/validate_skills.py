#!/usr/bin/env python3
"""Check every skill in this repo against what sima-cli's installer requires.

Run it from the repository root:

    python3 .github/scripts/validate_skills.py

Deliberately dependency-free — no PyYAML, no sima-cli. The manifests here are
flat `key: value` files, so a real YAML parser would buy nothing and would make
this fail for a reason that has nothing to do with the skills.
"""

from __future__ import annotations

import json
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

    if skill.name == "edgematic-ros2-contract-builder":
        check_rosbot_xl_profile(skill)


def check_rosbot_xl_profile(skill: Path) -> None:
    """Validate the machine-readable ROSBOT XL profile's safety invariants."""
    profile_path = skill / "references" / "rosbot-xl-profile.json"
    rel = profile_path.relative_to(REPO)
    if not profile_path.is_file():
        fail(f"{rel}: missing ROSBOT XL profile")
        return

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"{rel}: cannot parse profile: {exc}")
        return
    if not isinstance(profile, dict):
        fail(f"{rel}: profile root must be an object")
        return

    if profile.get("schema_version") != 1:
        fail(f"{rel}: schema_version must be 1")

    match = profile.get("match", {})
    if not isinstance(match, dict) or match.get("robot_name") != "rosbot_xl":
        fail(f"{rel}: match.robot_name must be 'rosbot_xl'")
        match = {}
    expected_links = {
        "base_link",
        "body_link",
        "imu_link",
        "camera_color_optical_frame",
    }
    if not expected_links.issubset(set(match.get("required_links", []))):
        fail(f"{rel}: match must require the ROSBOT XL base, IMU, and camera links")
    expected_joints = {
        "fl_wheel_joint",
        "fr_wheel_joint",
        "rl_wheel_joint",
        "rr_wheel_joint",
    }
    if set(match.get("required_joints", [])) != expected_joints:
        fail(f"{rel}: match must require all four ROSBOT XL wheel joints")
    expected_plugins = {
        "rosbot_hardware_interfaces/RosbotImuSensor",
        "rosbot_hardware_interfaces/RosbotSystem",
    }
    if set(match.get("required_ros2_control_plugins", [])) != expected_plugins:
        fail(f"{rel}: match must require both ROSBOT XL ros2_control plugins")

    sources = profile.get("vendor_sources", [])
    if not isinstance(sources, list) or len(sources) < 2:
        fail(f"{rel}: vendor_sources must contain the pinned base and sensor sources")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                fail(f"{rel}: vendor_sources[{index}] must be an object")
                continue
            repository = source.get("repository", "")
            revision = source.get("revision", "")
            if not repository.startswith("https://github.com/husarion/"):
                fail(f"{rel}: vendor_sources[{index}] is not an official Husarion repository")
            if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                fail(f"{rel}: vendor_sources[{index}] revision is not an immutable Git SHA")

    generation = profile.get("contract_generation", {})
    if not isinstance(generation, dict):
        fail(f"{rel}: contract_generation must be an object")
        generation = {}
    expected_files = {
        "robot_contract.yaml",
        "build_target.yaml",
        "acceptance.yaml",
    }
    if set(generation.get("materialized_files", [])) != expected_files:
        fail(f"{rel}: contract_generation must materialize the three derived YAML files")
    if generation.get("default_physical_motion_required") is not False:
        fail(f"{rel}: physical motion must default to false")
    tui = generation.get("tui", {})
    if not isinstance(tui, dict) or tui.get("read_only") is not True:
        fail(f"{rel}: the generated TUI must remain read-only")

    modes = generation.get("supported_input_modes", [])
    modes_by_transport = {
        mode.get("transport"): mode
        for mode in modes
        if isinstance(mode, dict) and isinstance(mode.get("transport"), str)
    }
    rosbag = modes_by_transport.get("rosbag", {})
    live = modes_by_transport.get("managed_rtsp", {})
    if rosbag.get("input_mode") != "rosbag":
        fail(f"{rel}: rosbag transport must materialize input_mode 'rosbag'")
    if live.get("input_mode") != "live":
        fail(f"{rel}: managed RTSP transport must materialize input_mode 'live'")
    if live.get("live_hardware_drivers_required") is not False:
        fail(f"{rel}: managed RTSP must not claim proof of a physical camera driver")
    live_topics = {
        topic.get("name"): topic.get("type")
        for topic in live.get("required_topics", [])
        if isinstance(topic, dict)
    }
    if live_topics.get("/camera/image_raw") != "sensor_msgs/msg/Image":
        fail(f"{rel}: managed RTSP must expose a typed raw image topic")
    common_topics = {
        topic.get("name"): topic.get("type")
        for topic in generation.get("common_required_topics", [])
        if isinstance(topic, dict)
    }
    required_common_topics = {
        "/detections": "simaai_common/msg/DetectionArray",
        "/detections_overlay": "sensor_msgs/msg/Image",
        "/tf": "tf2_msgs/msg/TFMessage",
        "/tf_static": "tf2_msgs/msg/TFMessage",
    }
    for topic, message_type in required_common_topics.items():
        if common_topics.get(topic) != message_type:
            fail(f"{rel}: common acceptance is missing {topic} ({message_type})")

    mutable = set(profile.get("mutable_target_fields", []))
    required_mutable = {
        "target.ros_distro",
        "target.architecture",
        "target.sdk",
        "target.platform_version",
        "target.neat_core",
        "target.middleware",
    }
    if not required_mutable.issubset(mutable):
        fail(f"{rel}: mutable target fields must cover SDK and board runtime identity")

    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    if profile_path.name not in skill_text:
        fail(f"{rel}: profile is not discoverable from SKILL.md")


# Edgematic Studio can be told that the legacy ROS 2 client repository does not
# exist for a deployment. It enforces that by hiding every installed skill whose
# TEXT names the repository — a skill is prose the model reads, so no tool gate
# can reach it, and reading the text is the only check that works on a skill set
# we install but do not control.
#
# The consequence for this repository is that a mention is load-bearing. These
# skills are the ones a deployment still has once the repository is disowned, so
# a mention inside one of them removes the very guidance that mode depends on —
# and the failure is silent, because a hidden skill looks exactly like a skill
# that was never installed.
LEGACY_REPO_SLUG = "vdp-simaai-ros2"
MUST_SURVIVE_WITHOUT_THE_LEGACY_REPO = (
    "edgematic-ros2-portable-pipeline",
    # The orchestrator runs on BOTH paths and branches on which one it is on, so
    # it is the one skill that must never be hidden — a deployment that lost it
    # would lose the flow that tells it the client-repository path is gone.
    "edgematic-ros2-autonomous-run",
)


def check_legacy_repo_mentions(skill: Path) -> None:
    """A skill that must outlive the legacy repository must not name it."""
    if skill.name not in MUST_SURVIVE_WITHOUT_THE_LEGACY_REPO:
        return
    for path in sorted(skill.rglob("*")):
        if not path.is_file() or path.suffix not in (".md", ".yml", ".yaml"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if LEGACY_REPO_SLUG in line:
                rel = path.relative_to(REPO)
                fail(
                    f"{rel}:{lineno}: names `{LEGACY_REPO_SLUG}`, but this skill is "
                    "what a deployment falls back to once that repository is "
                    "disowned — naming it makes the skill invisible to exactly "
                    "the deployments that need it. Describe the repository "
                    "without its name."
                )


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
        check_legacy_repo_mentions(skill)

    if errors:
        print(f"{len(errors)} problem(s) found:\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK — {len(skills)} skills valid: {', '.join(s.name for s in skills)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
