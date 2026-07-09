#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.DOTALL)
PORT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SKILL_FOLDER_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FORBIDDEN_SKILL_DOCS = {
    "README.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
    "CHANGELOG.md",
}


class ValidationError(Exception):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValidationError(f"{path}: expected a YAML object")
    return loaded


def load_skill_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text()
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValidationError(f"{path}: missing YAML frontmatter block")
    try:
        frontmatter = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path}: invalid frontmatter YAML: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise ValidationError(f"{path}: frontmatter must be an object")
    return frontmatter


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_manifest(repo: Path) -> dict[str, Any]:
    manifest_path = repo / "skills.yaml"
    manifest = load_yaml(manifest_path)

    require(manifest.get("schema_version") == 1, "skills.yaml: schema_version must be 1")
    constraints = manifest.get("constraints")
    defaults = manifest.get("defaults")
    skills = manifest.get("skills")
    require(isinstance(constraints, dict), "skills.yaml: constraints must be an object")
    require(isinstance(defaults, dict), "skills.yaml: defaults must be an object")
    require(isinstance(skills, dict) and skills, "skills.yaml: skills must be a non-empty object")

    allowed_statuses = set(_required_string_list(constraints, "allowed_statuses", "constraints"))
    allowed_backends = set(_required_string_list(constraints, "allowed_execution_backends", "constraints"))
    allowed_permissions = set(_required_string_list(constraints, "allowed_permissions", "constraints"))
    allowed_models = set(_required_string_list(constraints, "allowed_models", "constraints"))

    require(_non_empty_string(defaults.get("source_repo")), "skills.yaml: defaults.source_repo is required")
    require(_non_empty_string(defaults.get("source_ref")), "skills.yaml: defaults.source_ref is required")

    seen_source_paths: set[str] = set()
    for skill_id, skill in skills.items():
        validate_skill(repo, skill_id, skill, allowed_statuses, allowed_backends, allowed_permissions, allowed_models)
        source_path = skill["source_path"]
        require(source_path not in seen_source_paths, f"{skill_id}: duplicate source_path {source_path}")
        seen_source_paths.add(source_path)

    validate_folder_coverage(repo, seen_source_paths)
    return manifest


def validate_skill(
    repo: Path,
    skill_id: str,
    skill: Any,
    allowed_statuses: set[str],
    allowed_backends: set[str],
    allowed_permissions: set[str],
    allowed_models: set[str],
) -> None:
    require(PORT_ID_RE.match(skill_id) is not None, f"{skill_id}: Port skill id must be lowercase snake_case")
    require(isinstance(skill, dict), f"{skill_id}: skill entry must be an object")
    require(_non_empty_string(skill.get("description")), f"{skill_id}: description is required")
    require(skill.get("status") in allowed_statuses, f"{skill_id}: status is not in constraints.allowed_statuses")
    require(skill.get("execution_backend") in allowed_backends, f"{skill_id}: execution_backend is not allowed")
    require(skill.get("required_ad_group") in allowed_permissions, f"{skill_id}: required_ad_group is not allowed")
    require(isinstance(skill.get("approval_required"), bool), f"{skill_id}: approval_required must be a boolean")
    require(_non_empty_string(skill.get("owner")), f"{skill_id}: owner is required")
    require(VERSION_RE.match(str(skill.get("version", ""))) is not None, f"{skill_id}: version must look like 0.1.0")
    require(DATE_RE.match(str(skill.get("last_validated_at", ""))) is not None, f"{skill_id}: last_validated_at must be YYYY-MM-DD")

    models = _required_string_list(skill, "allowed_models", skill_id)
    unknown_models = sorted(set(models) - allowed_models)
    require(not unknown_models, f"{skill_id}: unknown allowed_models: {unknown_models}")

    source_path = skill.get("source_path")
    require(_non_empty_string(source_path), f"{skill_id}: source_path is required")
    require(str(source_path).startswith("skills/"), f"{skill_id}: source_path must start with skills/")
    folder_name = str(source_path).removeprefix("skills/")
    require(SKILL_FOLDER_RE.match(folder_name) is not None, f"{skill_id}: source_path folder must be lowercase hyphen-case")

    skill_folder = repo / str(source_path)
    skill_md = skill_folder / "SKILL.md"
    require(skill_folder.is_dir(), f"{skill_id}: missing skill folder {source_path}")
    require(skill_md.is_file(), f"{skill_id}: missing {source_path}/SKILL.md")
    validate_skill_folder(skill_id, skill_folder, skill_md)

    if skill.get("execution_backend") == "swarm":
        validate_swarm(skill_id, skill.get("swarm"))
    else:
        require("swarm" not in skill, f"{skill_id}: non-swarm skills must not define swarm")

    if "can_write_artifacts" in skill:
        require(isinstance(skill["can_write_artifacts"], bool), f"{skill_id}: can_write_artifacts must be a boolean")


def validate_skill_folder(skill_id: str, skill_folder: Path, skill_md: Path) -> None:
    forbidden = sorted(path.name for path in skill_folder.iterdir() if path.name in FORBIDDEN_SKILL_DOCS)
    require(not forbidden, f"{skill_id}: remove unsupported skill docs: {forbidden}")

    frontmatter = load_skill_frontmatter(skill_md)
    require(set(frontmatter) == {"name", "description"}, f"{skill_md}: frontmatter must contain only name and description")
    require(frontmatter["name"] == skill_folder.name, f"{skill_md}: frontmatter name must match folder name")
    require(_non_empty_string(frontmatter["description"]), f"{skill_md}: frontmatter description is required")


def validate_swarm(skill_id: str, swarm: Any) -> None:
    require(isinstance(swarm, dict), f"{skill_id}: swarm skills must define swarm")
    require(isinstance(swarm.get("max_rounds"), int) and swarm["max_rounds"] > 0, f"{skill_id}: swarm.max_rounds must be positive")
    _required_string_list(swarm, "acceptance_criteria", f"{skill_id}.swarm")
    roles = swarm.get("roles")
    require(isinstance(roles, list) and roles, f"{skill_id}: swarm.roles must be a non-empty list")
    for index, role in enumerate(roles):
        label = f"{skill_id}.swarm.roles[{index}]"
        require(isinstance(role, dict), f"{label}: role must be an object")
        require(_non_empty_string(role.get("id")), f"{label}: id is required")
        require(_non_empty_string(role.get("role")), f"{label}: role is required")
        require(_non_empty_string(role.get("phase")), f"{label}: phase is required")
        if "blocking_rules" in role:
            _required_string_list(role, "blocking_rules", label)


def validate_folder_coverage(repo: Path, manifest_source_paths: set[str]) -> None:
    skills_dir = repo / "skills"
    require(skills_dir.is_dir(), "skills/: directory is required")
    folder_paths = {
        f"skills/{path.name}"
        for path in skills_dir.iterdir()
        if path.is_dir()
    }
    missing_manifest_entries = sorted(folder_paths - manifest_source_paths)
    missing_folders = sorted(manifest_source_paths - folder_paths)
    require(not missing_manifest_entries, f"skills.yaml: folders missing manifest entries: {missing_manifest_entries}")
    require(not missing_folders, f"skills.yaml: manifest entries missing folders: {missing_folders}")


def _required_string_list(source: dict[str, Any], key: str, label: str) -> list[str]:
    value = source.get(key)
    require(isinstance(value, list) and value, f"{label}.{key}: must be a non-empty list")
    require(all(_non_empty_string(item) for item in value), f"{label}.{key}: items must be non-empty strings")
    return value


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an ai-skills GitOps repository")
    parser.add_argument("--repo", default="ai-skills", help="Path to the ai-skills repository root")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    try:
        manifest = validate_manifest(repo)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(manifest['skills'])} AI skills in {repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
