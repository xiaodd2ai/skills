"""Owner-dispatched tasks for the WeCom bot: Claude Code with tools, one at a time.

The owner sends `/task <dir> <what to do>` in a single chat with the bot. Each
task gets its own Claude Code session in that directory, resumed for every
later run of the same task, and a single worker runs one task at a time.

Claude runs in auto mode with the owner's normal settings (plugins, MCP
servers, auto mode rules). A call that auto mode blocks is not executed: the
run finishes what it can, then the blocked calls (`permission_denials` in the
JSON result) are pushed to the owner. On /yes the session is resumed with
approve_hook.py allowing exactly those calls for that one run; on /no Claude
is told not to make them.

Measured on Claude Code 2.1.325 before choosing this: pausing mid-run with a
PreToolUse "defer" works for a single call but silently drops calls when
Claude makes several at once, so it is not used.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import shlex
import signal
import sys
import uuid
from datetime import datetime
from pathlib import Path

from approve_hook import APPROVED_ENV, call_key

TASK_TIMEOUT = int(os.environ.get("TASK_TIMEOUT", "1800"))
TASK_MODEL = os.environ.get("TASK_MODEL", "")
TASK_BASE_DIR = Path(os.path.expanduser(os.environ.get("TASK_BASE_DIR") or "~"))
# Bot credentials stay out of the task session: its Bash tool could read them.
# The Claude Code login variables (ANTHROPIC_*) must stay.
PRIVATE_ENV = ("WECOM_BOT_ID", "WECOM_BOT_SECRET")
MAX_NOTE_CHARS = 6000
MAX_TARGET_CHARS = 2000

STATUS = {"queued": "排队中", "running": "执行中", "waiting": "等你确认", "done": "已结束", "failed": "失败"}

TASK_SYSTEM_PROMPT = (
    "你在无人值守模式下运行：这个任务是主人通过企业微信派给你的，终端前没有人，"
    "没人能回答你的提问或权限弹窗。\n"
    "- 按任务描述把能做的做完。需要主人拿主意的事（方案取舍、信息不足、有风险的操作），"
    "不要猜，在最后的回复里写清楚要他决定什么，然后结束。\n"
    "- 被 auto mode 拦下的操作，不要换别的命令或写法绕过去。机器人会把它转给主人批准，"
    "批准后你会收到「原样重新执行」的指示。先做不依赖它的部分。\n"
    "- 你最后的回复会原样发到主人的企业微信：先说结论，再说做了什么、还剩什么；"
    "简洁，可以用 Markdown，不要贴大段日志。"
)

log = logging.getLogger("wecom-autoreply")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def resolve_dir(raw: str) -> Path | None:
    """Absolute, ~/..., or relative to TASK_BASE_DIR; None unless it is a directory."""
    path = Path(os.path.expanduser(raw))
    if not path.is_absolute():
        path = TASK_BASE_DIR / path
    path = path.resolve()
    return path if path.is_dir() else None


def describe(call: dict) -> str:
    """The tool and what it touches (command / file / URL), quoted line by line."""
    inp = call.get("tool_input") or {}
    target = str(inp.get("command") or inp.get("file_path") or inp.get("url") or json.dumps(inp, ensure_ascii=False))
    if len(target) > MAX_TARGET_CHARS:
        target = target[:MAX_TARGET_CHARS] + f"…（共 {len(target)} 字，后面已截断）"
    return call["tool_name"] + "\n" + "\n".join("> " + line for line in (target.splitlines() or [""]))


def numbered(calls: list[dict]) -> str:
    return "\n".join(f"{i}. {describe(c)}" for i, c in enumerate(calls, 1))


def blocked_calls(denials: list[dict]) -> list[dict]:
    """permission_denials without repeats (Claude may retry the same call)."""
    seen, calls = set(), []
    for d in denials:
        call = {"tool_name": d.get("tool_name", ""), "tool_input": d.get("tool_input") or {}}
        key = call_key(call["tool_name"], call["tool_input"])
        if key not in seen:
            seen.add(key)
            calls.append(call)
    return calls


def short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


class TaskRunner:
    """Task state in a JSON file, a queue of runs, and the single worker draining it.

    State changes are synchronous (no await between load-modify-save), so the
    bot's message handlers and the worker cannot interleave writes.
    """

    def __init__(self, state_file: Path, notify, hook_script: Path) -> None:
        self.state_file = state_file
        self.notify = notify  # async (title, markdown) -> None
        self.hook_script = hook_script
        self.queue: asyncio.Queue = asyncio.Queue()
        try:
            self.state = json.loads(state_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.state = {"next_id": 1, "tasks": {}}
        # A run that was queued or in flight when the bot stopped is not replayed:
        # it may have had side effects already. The owner continues it with /re.
        for task in self.state["tasks"].values():
            if task["status"] in ("queued", "running"):
                task.update(status="failed", note="机器人重启时这个任务还没跑完，已中断。", updated=now())
        self.save()

    def save(self) -> None:
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(self.state_file)

    def get(self, task_id: int) -> dict | None:
        return self.state["tasks"].get(str(task_id))

    def busy(self) -> int:
        return sum(1 for t in self.state["tasks"].values() if t["status"] in ("queued", "running"))

    def enqueue(self, task: dict, prompt: str, approved: list[str]) -> None:
        task.update(status="queued", updated=now())
        self.save()
        self.queue.put_nowait((task["id"], prompt, approved))

    # --- owner commands; each returns the reply for the owner -----------------

    def submit(self, cwd: Path, prompt: str) -> dict:
        task_id = self.state["next_id"]
        self.state["next_id"] = task_id + 1
        # The session id is chosen here, so a first run that times out before
        # reporting one can still be resumed.
        task = {"id": task_id, "cwd": str(cwd), "prompt": prompt, "session_id": str(uuid.uuid4()), "runs": 0,
                "status": "queued", "pending": [], "note": "", "created": now(), "updated": now()}
        self.state["tasks"][str(task_id)] = task
        self.enqueue(task, prompt, [])
        return task

    def waiting(self, task_id: int | None) -> dict | str:
        """The waiting task the owner means, or why that is unclear."""
        if task_id is None:
            waiting = [t for t in self.state["tasks"].values() if t["status"] == "waiting"]
            if len(waiting) == 1:
                return waiting[0]
            if not waiting:
                return "没有在等你确认的任务。"
            return "有几个任务都在等你确认（" + "、".join(f"#{t['id']}" for t in waiting) + "），请带上编号。"
        task = self.get(task_id)
        if not task:
            return f"没有任务 #{task_id}。"
        if task["status"] != "waiting":
            return f"任务 #{task_id} 现在不需要确认（{STATUS[task['status']]}）。"
        return task

    def approve(self, task_id: int | None) -> str:
        task = self.waiting(task_id)
        if isinstance(task, str):
            return task
        calls, task["pending"] = task["pending"], []
        prompt = ("主人在企业微信里批准了刚才被拦下的这些操作。请原样重新执行"
                  "（命令和参数要和原来完全一样，否则批准不生效），然后继续完成任务：\n" + numbered(calls))
        self.enqueue(task, prompt, [call_key(c["tool_name"], c["tool_input"]) for c in calls])
        return f"已批准任务 #{task['id']} 的 {len(calls)} 个操作，继续执行。"

    def reject(self, task_id: int | None, reason: str) -> str:
        task = self.waiting(task_id)
        if isinstance(task, str):
            return task
        calls, task["pending"] = task["pending"], []
        prompt = ("主人拒绝了刚才被拦下的这些操作：\n" + numbered(calls)
                  + f"\n\n主人的说明：{reason or '（无）'}\n"
                  "不要执行它们，也不要换别的命令或写法绕过。在不做这些操作的前提下继续；做不下去就收尾，说明还差什么。")
        self.enqueue(task, prompt, [])
        return f"已告诉任务 #{task['id']} 不做这 {len(calls)} 个操作，让它接着处理。"

    def reply(self, task_id: int, text: str) -> str:
        task = self.get(task_id)
        if not task:
            return f"没有任务 #{task_id}。"
        if task["status"] == "waiting":
            return f"任务 #{task_id} 在等你确认被拦下的操作，先回 /yes {task_id} 或 /no {task_id} 说明。"
        if task["status"] in ("queued", "running"):
            return f"任务 #{task_id} 还在{STATUS[task['status']]}，等它结束再追加。"
        self.enqueue(task, text, [])
        return f"已转给任务 #{task_id}，继续执行。"

    def listing(self, limit: int = 10) -> str:
        tasks = sorted(self.state["tasks"].values(), key=lambda t: t["id"], reverse=True)[:limit]
        if not tasks:
            return "还没有任务。"
        return "最近的任务：\n" + "\n".join(
            f"- #{t['id']} {STATUS[t['status']]}（{t['updated']}）`{t['cwd']}`：{short(t['prompt'], 60)}" for t in tasks
        )

    # --- the worker ------------------------------------------------------------

    def command(self, task: dict, approved: list[str]) -> tuple[list[str], dict]:
        cmd = ["claude", "-p", "--output-format", "json", "--permission-mode", "auto",
               "--append-system-prompt", TASK_SYSTEM_PROMPT]
        if TASK_MODEL:
            cmd += ["--model", TASK_MODEL]
        cmd += ["--resume" if task["runs"] else "--session-id", task["session_id"]]
        env = {k: v for k, v in os.environ.items() if k not in PRIVATE_ENV and k != APPROVED_ENV}
        if approved:
            hook = f"{shlex.quote(sys.executable)} {shlex.quote(str(self.hook_script))}"
            cmd += ["--settings", json.dumps({"hooks": {"PreToolUse": [
                {"matcher": "*", "hooks": [{"type": "command", "command": hook}]}]}})]
            env[APPROVED_ENV] = json.dumps(approved, ensure_ascii=False)
        return cmd, env

    async def worker(self) -> None:
        while True:
            task_id, prompt, approved = await self.queue.get()
            task = self.get(task_id)
            try:
                await self.run(task, prompt, approved)
            except Exception as exc:  # noqa: BLE001 - one broken run must not stop the worker
                log.exception("task #%s crashed", task_id)
                await self.finish(task, "failed", f"机器人内部错误：{exc}")
            finally:
                self.queue.task_done()

    async def run(self, task: dict, prompt: str, approved: list[str]) -> None:
        task.update(status="running", updated=now())
        self.save()
        log.info("task #%s run (approved %d) in %s: %s", task["id"], len(approved), task["cwd"], short(prompt, 200))
        cmd, env = self.command(task, approved)
        # The prompt goes in on stdin, never argv. A session of its own lets a
        # timeout kill Claude together with the commands it started.
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=task["cwd"], env=env, start_new_session=True,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        task["runs"] += 1
        self.save()
        try:
            out, err = await asyncio.wait_for(proc.communicate(prompt.encode("utf-8")), TASK_TIMEOUT)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            await proc.wait()
            await self.finish(task, "failed", f"超过 {TASK_TIMEOUT} 秒还没跑完，已停止。")
            return

        try:
            data = json.loads(out)
        except ValueError:
            data = {}
        result = (data.get("result") or "").strip()
        if proc.returncode != 0 or not data or data.get("is_error"):
            detail = result or err.decode("utf-8", "replace").strip()[-800:] or f"退出码 {proc.returncode}"
            await self.finish(task, "failed", f"Claude 出错：{detail}")
            return
        task["pending"] = blocked_calls(data.get("permission_denials") or [])
        await self.finish(task, "waiting" if task["pending"] else "done", result)

    async def finish(self, task: dict, status: str, note: str) -> None:
        task.update(status=status, note=note[:MAX_NOTE_CHARS], updated=now())
        self.save()
        log.info("task #%s %s: %s", task["id"], status, short(note, 300))
        tid, where = task["id"], f"`{task['cwd']}`"
        if status == "waiting":
            calls = task["pending"]
            explain = "\n".join("> " + line for line in (task["note"].splitlines() or ["（没有说明）"]))
            content = (f"**任务 #{tid} 有 {len(calls)} 个操作被 auto mode 拦下，等你确认** {where}\n\n"
                       f"{numbered(calls)}\n\nClaude 的说明：\n{explain}\n\n"
                       f"回复 /yes {tid} 批准并继续；/no {tid} 说明 拒绝。")
        elif status == "done":
            content = f"**任务 #{tid} 结束** {where}\n\n{task['note'] or '（Claude 没有写总结）'}\n\n要接着做：/re {tid} 内容"
        else:
            content = f"**任务 #{tid} 失败** {where}\n\n{task['note']}\n\n要重试或接着做：/re {tid} 内容"
        await self.notify(f"任务 #{tid} {STATUS[status]}", content)
