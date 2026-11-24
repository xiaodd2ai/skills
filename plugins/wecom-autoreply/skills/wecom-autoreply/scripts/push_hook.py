"""Stop hook of the owner's Claude Code terminal: send the turn's last reply to WeCom.

tasks.py adds this hook to the session it starts (through --settings). It runs
after every turn, reads the hook payload on stdin and sends
`last_assistant_message` to the owner as the bot, through wecom-cli. A failed
send exits 1, which Claude Code shows in the terminal as a hook error.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

MAX_BYTES = 20480  # WeCom caps one message at 20480 UTF-8 bytes


def clip(text: str) -> str:
    data = text.encode("utf-8")
    if len(data) <= MAX_BYTES:
        return text
    marker = "\n\n...(内容过长，已截断，完整内容在终端里)"
    return data[: MAX_BYTES - len(marker.encode("utf-8"))].decode("utf-8", errors="ignore") + marker


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    text = str(event.get("last_assistant_message") or "").strip()
    owner = os.environ.get("OWNER_USERID", "")
    if not text or not owner:
        return 0
    payload = {"chat_id": owner, "msg_type": "markdown", "markdown": {"content": clip(text)}}
    sent = subprocess.run(["wecom-cli", "message", "aibot", "send", "--json", json.dumps(payload, ensure_ascii=False)],
                          capture_output=True, text=True, timeout=60, check=False)
    if sent.returncode != 0 or not re.search(r'"success"\s*:\s*true', sent.stdout):
        print(f"WeCom push failed: {(sent.stderr or sent.stdout).strip()[:300]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
