#!/usr/bin/env python3
"""Check skill indexes, plugin paths and marketplaces with the Python standard library."""

import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    buckets = ("engineering", "productivity", "in-progress", "misc", "deprecated")
    promoted = {"engineering", "productivity"}
    manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
    marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
    readme = (root / "README.md").read_text()
    errors = []
    stable_paths = set()
    skill_count = 0

    for bucket in buckets:
        directory = root / "skills" / bucket
        index = directory / "README.md"
        if not index.is_file():
            errors.append(f"Missing bucket index: skills/{bucket}/README.md")
            continue
        bucket_readme = index.read_text()
        for entry in sorted(directory.glob("*/SKILL.md")):
            skill_count += 1
            skill_path = entry.parent.relative_to(root).as_posix()
            if f"{entry.parent.name}/SKILL.md" not in bucket_readme:
                errors.append(f"Missing bucket README link: {skill_path}")
            if bucket in promoted:
                stable_paths.add(f"./{skill_path}")
                if f"{skill_path}/SKILL.md" not in readme:
                    errors.append(f"Missing root README link: {skill_path}")
                docs = root / "docs" / bucket / f"{entry.parent.name}.md"
                if not docs.is_file():
                    errors.append(f"Missing skill documentation: {docs.relative_to(root)}")
            elif f"{skill_path}/SKILL.md" in readme:
                errors.append(f"Non-stable skill appears in published index: {skill_path}")

    listed_paths = manifest.get("skills")
    if not isinstance(listed_paths, list) or not all(isinstance(p, str) for p in listed_paths):
        errors.append("Plugin skills must be an array of paths")
    else:
        if len(listed_paths) != len(set(listed_paths)):
            errors.append("Duplicate plugin skill paths")
        if set(listed_paths) != stable_paths:
            errors.append("Plugin skills must match all engineering and productivity skills")

    plugins = marketplace.get("plugins", [])
    root_entries = [p for p in plugins if p.get("source") == "./"]
    if len(root_entries) != 1 or root_entries[0].get("name") != manifest.get("name"):
        errors.append("Marketplace must list the skills bundle once, with source ./ and the manifest's name")

    # Standalone plugins live in plugins/<name>/ and are listed in the marketplace on their own.
    plugin_dirs = sorted(d for d in (root / "plugins").glob("*") if d.is_dir())
    listed = {p.get("source"): p.get("name") for p in plugins if p.get("source") != "./"}
    expected = {f"./plugins/{d.name}": d.name for d in plugin_dirs}
    if listed != expected:
        errors.append("Marketplace standalone plugins must match plugins/* (source ./plugins/<name>, same name)")
    codex_path = root / ".agents/plugins/marketplace.json"
    codex = json.loads(codex_path.read_text()) if codex_path.is_file() else {"plugins": []}
    codex_listed = {p.get("source", {}).get("path"): p.get("name") for p in codex.get("plugins", [])}
    for directory in plugin_dirs:
        rel = directory.relative_to(root).as_posix()
        plugin_manifest = directory / ".claude-plugin/plugin.json"
        if not plugin_manifest.is_file():
            errors.append(f"Missing plugin manifest: {rel}/.claude-plugin/plugin.json")
        elif json.loads(plugin_manifest.read_text()).get("name") != directory.name:
            errors.append(f"Plugin name must match its directory: {rel}")
        if not (directory / "README.md").is_file():
            errors.append(f"Missing plugin README: {rel}/README.md")
        if not list(directory.glob("skills/*/SKILL.md")):
            errors.append(f"Plugin has no skills: {rel}")
        if f"{rel}/README.md" not in readme:
            errors.append(f"Missing root README link: {rel}")
        codex_manifest = directory / ".codex-plugin/plugin.json"
        if codex_manifest.is_file():
            if json.loads(codex_manifest.read_text()).get("name") != directory.name:
                errors.append(f"Codex plugin name must match its directory: {rel}")
            if codex_listed.get(f"./{rel}") != directory.name:
                errors.append(f"Missing Codex marketplace entry: {rel}")
    for path in codex_listed:
        if not (root / str(path) / ".codex-plugin/plugin.json").is_file():
            errors.append(f"Codex marketplace entry has no .codex-plugin manifest: {path}")

    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    print(f"Repository checks passed: {skill_count} skills, {len(stable_paths)} published, "
          f"{len(plugin_dirs)} standalone plugins")


if __name__ == "__main__":
    main()
