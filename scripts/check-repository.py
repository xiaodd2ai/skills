#!/usr/bin/env python3
"""Check skill indexes and plugin paths with the Python standard library."""

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
    if len(plugins) != 1 or plugins[0].get("name") != manifest.get("name"):
        errors.append("Marketplace plugin name must match the plugin manifest")
    elif plugins[0].get("source") != "./":
        errors.append("Marketplace plugin source must point to this repository")

    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    print(f"Repository checks passed: {skill_count} skills, {len(stable_paths)} published")


if __name__ == "__main__":
    main()
