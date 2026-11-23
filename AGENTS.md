# Repository instructions

This repository stores personal Agent Skills. Keep skills small, practical, and composable.

## Organization

- `skills/engineering/` and `skills/productivity/` contain stable skills shipped in the plugin.
- `skills/in-progress/` contains experimental skills.
- `skills/misc/` contains retained, infrequently used skills.
- `skills/deprecated/` contains retired skills and migration notes.
- Each skill lives in its own lowercase, hyphenated directory with a `SKILL.md` entry point.
- Keep long reference material in `references/`, executable helpers in `scripts/`, and reusable resources in `assets/`, only when needed.
- Use `docs/skill-template.md` as a starting point. Do not install the template as a real skill.
- `plugins/<name>/` contains standalone plugins that install separately (skills that ship scripts, resident services, or need their own install): `.claude-plugin/plugin.json`, optional `.codex-plugin/plugin.json`, skills under `skills/<skill>/SKILL.md`, and a Simplified Chinese `README.md` as the user guide.

## Keeping indexes consistent

- Every skill must be linked from its bucket's `README.md` with a one-line description.
- Every stable skill must also be linked from the root `README.md`, listed explicitly in `.claude-plugin/plugin.json`, and documented in `docs/<bucket>/<skill-name>.md`.
- Experimental, miscellaneous, and deprecated skills must not be listed in the plugin manifest or the published-skill index.
- Every standalone plugin must be listed in `.claude-plugin/marketplace.json` with source `./plugins/<name>` and linked from the root `README.md`; one with `.codex-plugin/plugin.json` must also be listed in `.agents/plugins/marketplace.json`. Its skills are not listed in the root `plugin.json`.
- Stable skill docs should explain what the skill does, when to use it, common questions, and how to judge completion.
- Update all related indexes when adding, renaming, moving, or retiring a skill.
- Record attribution and preserve license notices when adapting third-party material.
- Keep credentials, personal data, and company-specific private material out of this public repository.

## Language and validation

- Write user-facing documentation and commit messages in Simplified Chinese.
- Write code, identifiers, code comments, and reusable skill-template instructions in English.
- Describe concrete task triggers and completion criteria in each skill.
- Run `bash scripts/list-skills.sh` and `python3 scripts/check-repository.py` before committing.
- When changing plugin metadata, also run `claude plugin validate . --strict` (and `claude plugin validate plugins/<name> --strict` for a standalone plugin) if the CLI is available.
