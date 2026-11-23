# wecom-autoreply — operations

## What the bot does

| Incoming | Handling |
|---|---|
| Text, single chat | Claude replies; one Claude session per colleague, resumed across messages |
| Text in a group (bot @-mentioned) | One session per group; the sender's userid is prefixed for Claude |
| Voice | WeCom's own transcript (`voice.content`) is handled as text |
| Text + images/files (mixed) | Text is handled; Claude is told N attachments exist but cannot be seen |
| Image, file, any other type | Sender is told the bot cannot read it; owner gets a to-do + push |
| A message that needs the owner | Claude flags it → numbered to-do in `todos.jsonl` + WeCom push to the owner (macOS notification if the push fails) |
| `/new` or `/reset` | Starts a fresh Claude session for that chat |
| Owner's `/task`, `/yes`, `/no`, `/re`, `/tasks`, `/help` (single chat only) | Owner tasks — see [Owner tasks](#owner-tasks). From anyone else, or in a group, these are ordinary text |

**Owner mode** — the owner's own single-chat messages get a private-assistant prompt with the
open to-dos attached. 「有什么要我处理的？」 lists them by number; 「#3 做完了」 /
「张三那几件处理好了」 / 「全部完成」 marks them done (Claude asks instead of guessing when it
is unclear which). Open to-dos stay listed until marked done.

Every inbound message writes an `inbound <type> from <userid>` log line, so nothing is dropped
silently.

## Files (`~/wecom-autoreply/`)

| File | Content |
|---|---|
| `bot.py`, `tasks.py`, `approve_hook.py` | The bot, the task runner and the approval hook (updated by `install.sh`; previous versions kept as `*.bak-*`) |
| `.env` | Bot credentials and options — secret, mode 600, never commit or print it |
| `persona.md` | Optional identity and duties, prepended to every system prompt; re-read per message (no restart). `persona.example.md` next to it is the template |
| `bot.log` | Messages, replies, to-dos, errors — contains message text, mode 600 |
| `sessions.json` | chat → Claude session id |
| `todos.jsonl` | One to-do per line: `id`, `time`, `from`, `chat`, `summary`, `text`, `done_at` |
| `tasks.json` | Owner tasks: directory, prompt, Claude session id, status, blocked calls, last result — mode 600. `tasks-test.json` is the same for `--test-task` |
| `workdir/` | Claude's empty working directory — must stay outside every repository |

## Owner tasks

| Command (owner's single chat) | Effect |
|---|---|
| `/task <dir> <what to do>` | New task: its own Claude Code session in `<dir>`. `#3` as the text hands Claude to-do #3 (colleague's words marked as data), optionally followed by the owner's notes |
| `/yes [编号]` | Approve the blocked calls of a waiting task and continue. The number can be left out when only one task is waiting |
| `/no [编号] [说明]` | Do not make the blocked calls; Claude continues without them or wraps up |
| `/re <编号> <内容>` | Continue a finished or failed task in the same session |
| `/tasks` | The last 10 tasks and their status |

How a run works:

1. A single worker takes runs from the queue one at a time and starts
   `claude -p --output-format json --permission-mode auto` in the task directory, with the
   owner's normal settings, a system prompt for unattended work, and the message on stdin. The
   first run passes `--session-id` (chosen when the task is created); later runs `--resume` it.
   `WECOM_BOT_ID` / `WECOM_BOT_SECRET` are removed from Claude's environment.
2. When the run ends, `permission_denials` in the JSON result lists the calls auto mode blocked.
   None: the result is pushed (task `done`). Some: the calls (command / file / URL, first
   2000 characters) and Claude's explanation are pushed and the task waits.
3. `/yes` resumes the session with "re-run these exactly", adding a `PreToolUse` hook
   (`approve_hook.py`) through `--settings` and the approved calls in `WECOM_APPROVED_CALLS`.
   The hook allows a call only when its tool and input match an approved one (ignoring
   `description` / `timeout`), and only in that run: the list lives in that run's environment,
   never in a file the session could write. A deny from another hook still wins.
4. A run longer than `TASK_TIMEOUT` (default 1800 s) is killed with everything it started. A run
   queued or in flight when the bot restarts is marked failed, not replayed; `/re` continues it.

Known limits:

- Auto mode only consults its classifier for some calls: commands it treats as routine (e.g.
  `touch` inside the task directory) and actions the owner named in the task text pass without a
  check. The approval loop covers what the classifier blocks, not every risky call.
- When Claude makes several calls at once and one is blocked, auto mode tends to block the whole
  batch, so harmless calls like `date` can show up in the approval list.
- Through a relay login the denial reason is always "judged dangerous (no explanation)"; the push
  shows Claude's own explanation instead.
- If Claude re-runs an approved call with a different command or input, it no longer matches and
  is blocked again — the bot asks again.
- Pausing mid-run with a `PreToolUse` `defer` was measured (2.1.325) and rejected: with several
  calls at once it reports only one and drops the others on resume.

## launchd

```bash
launchctl print gui/$(id -u)/com.xiaodd2ai.wecom-autoreply | grep -E "state|pid"   # status
launchctl kickstart -k gui/$(id -u)/com.xiaodd2ai.wecom-autoreply                  # restart
bash "<skill dir>/scripts/install.sh" --uninstall                                 # stop + remove
```

After editing `.env`, restart with `kickstart -k`. A crash is restarted after
`ThrottleInterval` (30 s); the SDK itself reconnects a dropped WebSocket forever.

## Troubleshooting

| Symptom | Check |
|---|---|
| No reply at all | `tail -20 bot.log`: is there a recent `connected to WeCom`? Is there an `inbound` line for the message? |
| `inbound` line but no `reply to` | `claude exited` / `timed out` in the log → run `uv run bot.py --test "hi"` in a terminal; usually Claude is logged out or the proxy is missing |
| Works in a terminal, fails under launchd | The plist carries PATH and proxy variables from the shell that ran `install.sh`; an env-var Claude login must be in `.env` (`install.sh --copy-claude-env`). Re-run `install.sh` — its preflight reproduces launchd's environment |
| Owner never gets pushes (`WeCom notify failed`) | The owner must have sent the bot a message first (853008); `OWNER_USERID` must be the owner's userid |
| Bot keeps disconnecting / reconnecting | Two processes share one bot (another machine, a terminal copy): one long connection per bot, the newest wins |
| Colleague's message missing from the log | It went to the user's own account, not to the bot; only messages to the bot arrive |
| A task fails with `command not found` or an MCP server missing | Tasks run in launchd's environment: PATH comes from the shell that ran `install.sh` (re-run it from a shell that has the tool); other exported variables are not carried |
| A task waits forever | It is waiting for `/yes` or `/no` — `/tasks` shows its status |

## Isolation — why the reply `claude -p` flags are what they are

These apply to replies (colleagues and owner mode). Owner tasks deliberately run with tools and
the owner's settings, as above.

Verified against Claude Code 2.1.323:

- `--tools ""`, `--strict-mcp-config`, `--disable-slash-commands`: no tools, MCP servers or skills
  — a sender can only get text back.
- `--setting-sources local`: without it, plugin `SessionStart` hooks from the user's settings
  still inject their context into the bot's prompt.
- Working directory outside every repo: Claude Code loads `CLAUDE.md` from parent directories.
- The message goes in on stdin, never argv (a message starting with `-` would parse as a flag).
- `--bare` is not used: it ignores OAuth logins and requires `ANTHROPIC_API_KEY`.
- A resumed session keeps whatever context it was created with — after changing these flags,
  delete `sessions.json` so every chat starts fresh.

## Known limits

- WeCom caps one message at 20480 UTF-8 bytes; longer replies are truncated with a marker.
- Images and files are not read (no download/OCR).
- `wecom-cli chat messages list` and `message send` (plain chats) return 853006 for some
  corporations, so a message the bot missed cannot be recovered afterwards.
