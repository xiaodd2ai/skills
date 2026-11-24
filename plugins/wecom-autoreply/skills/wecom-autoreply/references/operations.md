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
| `/new` or `/reset` from a colleague or in a group | Starts a fresh Claude session for that chat |
| Anything from the owner in a single chat | Goes to the owner's Claude Code terminal — see [The owner's Claude Code terminal](#the-owners-claude-code-terminal). In a group the owner is handled like a colleague |

Every inbound message writes an `inbound <type> from <userid>` log line, so nothing is dropped
silently.

## Files (`~/wecom-autoreply/`)

| File | Content |
|---|---|
| `bot.py`, `tasks.py`, `push_hook.py` | The bot, the owner's terminal session and the hook that pushes its replies to WeCom (updated by `install.sh`; previous versions kept as `*.bak-*`) |
| `.env` | Bot credentials and options — secret, mode 600, never commit or print it |
| `persona.md` | Optional identity and duties, prepended to the system prompt of replies to colleagues; re-read per message (no restart). `persona.example.md` next to it is the template |
| `bot.log` | Messages, replies, to-dos, errors — contains message text, mode 600 |
| `sessions.json` | chat → Claude session id |
| `todos.jsonl` | One to-do per line: `id`, `time`, `from`, `chat`, `summary`, `text`, `done_at`. The owner's terminal session reads it and fills in `done_at` |
| `task-prompt.txt` | The message that opened the current terminal session — mode 600 |
| `workdir/` | Claude's empty working directory — must stay outside every repository |

## The owner's Claude Code terminal

| Owner's single chat | Effect |
|---|---|
| A message, no session open | The bot keeps it and asks for the directory. Nothing starts yet |
| `/yes` / a directory / `/no` (while the bot is asking) | Open the session in `TASK_BASE_DIR` / in that directory (absolute, `~/…`, or relative to `TASK_BASE_DIR`) / drop the message. Anything else is answered with the question again |
| A message, session open | Typed into the session and submitted; the bot answers 「已发到终端」 |
| `/new` | Ends the session (kills the tmux session). The next message asks for a directory again |
| `/help` | The commands, and how to reopen the window |

How it works:

1. The session is `claude --permission-mode auto` in a detached tmux session (`tmux -L wecom`,
   session `claude`: a socket of its own, apart from the owner's tmux), started in the confirmed
   directory with the owner's normal settings, a system prompt for remote use, and the held
   message as its first prompt. `AskUserQuestion` is disallowed: nobody is there to click.
   `WECOM_BOT_ID` / `WECOM_BOT_SECRET` are removed from its environment.
2. A window is opened on it: `open -na Ghostty.app --args -e tmux … attach` when Ghostty is
   installed, otherwise Terminal.app through `osascript` (macOS asks once to allow it).
3. Later messages are pasted into the pane (`load-buffer` from stdin, bracketed `paste-buffer`,
   then Enter). While Claude is working, Claude Code queues them.
4. `--settings` adds a `Stop` hook, `push_hook.py`: after each turn it sends
   `last_assistant_message` to `OWNER_USERID` with `wecom-cli message aibot send` (cut at
   20480 bytes). A failed send exits 1 and shows in the terminal as a hook error.
5. The session is "open" while its pane's process is alive. When Claude exits (`/exit` in the
   terminal, a crash), the next message asks for a directory again.

Known limits:

- The owner's words never go through tmux's command line — tmux ends a command at an argument
  that ends in `;` — so the first message goes through `task-prompt.txt` and later ones through
  a paste buffer.
- A call auto mode blocks is not executed and not forwarded to WeCom; the reply says what was
  blocked. Dialogs (the trust question of a new directory, a permission prompt after leaving
  auto mode) wait at the terminal, and a message sent meanwhile is typed into that dialog.
- Replies typed at the terminal by the owner are pushed to WeCom as well: it is the same session.
- A pending first message is kept in memory only; after a bot restart, send it again. Whether
  an open session outlives a bot restart under launchd was not tested.
- Verified on Claude Code 2.1.330, tmux 3.5a, Ghostty 1.4.0: a first prompt starting with `-`,
  a follow-up ending in `;`, a message sent while Claude was working (queued, answered in the
  same turn), the `Stop` payload, and a Ghostty window attaching. The Terminal.app fallback was
  not run.

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
| `command not found` or an MCP server missing in the owner's terminal | It runs in launchd's environment: PATH comes from the shell that ran `install.sh` (re-run it from a shell that has the tool); other exported variables are not carried |
| The owner's message got 「已发到终端」 but no reply comes | Look at the terminal (`tmux -L wecom attach -t claude`): Claude may still be working, be stopped at a dialog (e.g. the trust question of a directory it has not seen), or show a `Stop hook` error from `push_hook.py` (wecom-cli not authorized, or the owner never messaged the bot: 853008) |
| 「Claude Code 没能在 … 启动」 | The text after it is what the terminal showed before Claude exited — usually not logged in under launchd (`install.sh --copy-claude-env`) |

## Isolation — why the reply `claude -p` flags are what they are

These apply to replies to colleagues. The owner's terminal deliberately runs with tools and the
owner's settings, as above.

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
