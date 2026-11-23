"""PreToolUse hook that lets owner-approved tool calls through (task runs).

When the owner approves calls that auto mode blocked, the bot resumes the
task session for ONE run with this hook installed and the approved calls in
the WECOM_APPROVED_CALLS environment variable. The hook allows exactly those
calls and prints nothing for any other call, so auto mode still decides the
rest. Approvals live only in that run's environment, never in a file the task
session could write to approve itself.

A deny from another hook (e.g. the team harness guard) still wins over this
allow: Claude Code ranks deny above allow.
"""

import json
import os
import sys

APPROVED_ENV = "WECOM_APPROVED_CALLS"
# Fields that do not change what a call does; Claude rewrites them on a retry.
IGNORED_INPUT_KEYS = ("description", "timeout")


def call_key(tool_name: str, tool_input: dict | None) -> str:
    kept = {k: v for k, v in (tool_input or {}).items() if k not in IGNORED_INPUT_KEYS}
    return f"{tool_name} {json.dumps(kept, sort_keys=True, ensure_ascii=False)}"


def main() -> None:
    try:
        approved = set(json.loads(os.environ.get(APPROVED_ENV) or "[]"))
        event = json.load(sys.stdin)
    except ValueError:
        return  # silent = no decision; auto mode handles the call as usual
    if call_key(event.get("tool_name", ""), event.get("tool_input")) in approved:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "approved by the bot owner in WeCom",
        }}))


if __name__ == "__main__":
    main()
