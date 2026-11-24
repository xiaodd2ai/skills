#!/bin/bash
# Install or update the WeCom auto-reply bot and keep it running under launchd.
#
#   install.sh                    install / update, then (re)start the agent
#   install.sh --copy-claude-env  same, first copying this shell's ANTHROPIC_* login
#                                 variables into .env (for env-var based logins)
#   install.sh --uninstall        stop the agent and remove its plist (data is kept)
#
# The bot lives in $WECOM_AUTOREPLY_HOME (default ~/wecom-autoreply). Re-running
# is safe: .env, persona.md, sessions.json, todos.jsonl and bot.log are
# never overwritten; changed code files are backed up before they are replaced.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
APP="${WECOM_AUTOREPLY_HOME:-$HOME/wecom-autoreply}"
LABEL="com.xiaodd2ai.wecom-autoreply"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
# Claude Code can be logged in through these instead of OAuth; launchd does not
# inherit them from the shell.
CLAUDE_ENV_VARS="ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY"

[ "$(uname)" = "Darwin" ] || { echo "macOS only: the bot is kept alive by launchd." >&2; exit 1; }

if [ "${1:-}" = "--uninstall" ]; then
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Stopped and removed $LABEL. Data left in $APP."
    exit 0
fi

missing=""
for bin in uv claude wecom-cli tmux; do
    command -v "$bin" >/dev/null 2>&1 || missing="$missing $bin"
done
[ -z "$missing" ] || { echo "Missing on PATH:$missing (see the skill's prerequisites)." >&2; exit 1; }

mkdir -p "$APP/workdir"
stamp="$(date +%Y%m%d%H%M%S)"
for f in bot.py tasks.py push_hook.py; do
    if [ -f "$APP/$f" ] && ! cmp -s "$SRC/$f" "$APP/$f"; then
        cp -p "$APP/$f" "$APP/$f.bak-$stamp"
        echo "Backed up the previous $f."
    fi
    cp "$SRC/$f" "$APP/$f"
done
# 0.3.0's approval hook: nothing uses it since the owner's messages go to a terminal.
if [ -f "$APP/approve_hook.py" ]; then
    mv "$APP/approve_hook.py" "$APP/approve_hook.py.bak-$stamp"
    echo "Retired approve_hook.py (kept as a backup)."
fi
cp "$SRC/persona.example.md" "$APP/persona.example.md"
[ -f "$APP/persona.md" ] || echo "Optional: give the bot an identity and duties — copy $APP/persona.example.md to $APP/persona.md and edit it."

if [ ! -f "$APP/.env" ]; then
    (umask 077 && cp "$SRC/env.example" "$APP/.env")
    echo "Created $APP/.env. Fill in WECOM_BOT_ID, WECOM_BOT_SECRET and OWNER_USERID, then run this script again."
    exit 0
fi
chmod 600 "$APP/.env"
for key in WECOM_BOT_ID WECOM_BOT_SECRET; do
    if ! grep -qE "^$key=.+" "$APP/.env"; then
        echo "$key is empty in $APP/.env. Fill it in, then run this script again." >&2
        exit 1
    fi
done
grep -qE "^OWNER_USERID=.+" "$APP/.env" || echo "Note: OWNER_USERID is empty, so owner mode and owner notifications are off."
if [ "${1:-}" = "--copy-claude-env" ]; then
    for var in $CLAUDE_ENV_VARS; do
        if [ -n "${!var:-}" ] && ! grep -q "^$var=" "$APP/.env"; then
            printf '%s=%s\n' "$var" "${!var}" >> "$APP/.env"
            echo "Copied $var into $APP/.env."
        fi
    done
fi

# launchd opens the log in append mode and keeps existing permissions; the log
# holds message text, so create it private before the first start.
[ -f "$APP/bot.log" ] || (umask 077 && : > "$APP/bot.log")
chmod 600 "$APP/bot.log"

# Two connections for one bot kick each other off: stop any copy started by hand
# from this directory. launchd's own copy (its `uv run` pid AND the python child
# doing the work) is left alone here and replaced by the bootout below.
agent_pid="$(launchctl print "$DOMAIN/$LABEL" 2>/dev/null | awk '$1 == "pid" && $2 == "=" {print $3; exit}' || true)"
for pid in $(pgrep -f "bot\.py" || true); do
    ppid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
    if [ -n "$agent_pid" ] && { [ "$pid" = "$agent_pid" ] || [ "$ppid" = "$agent_pid" ]; }; then
        continue
    fi
    # A pid can be gone by now (killing `uv run` takes its python child with it); lsof
    # then fails, and under set -e + pipefail that would end the script silently.
    cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' || true)"
    if [ "$cwd" = "$APP" ]; then
        kill "$pid" 2>/dev/null && echo "Stopped a manually started bot (pid $pid)."
    fi
done

xml() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<<"$1"; }

# launchd starts with a bare PATH: carry the directories of every tool the bot
# shells out to (uv, claude, wecom-cli, tmux and the node it runs on), then this
# shell's PATH, which the owner's Claude Code terminal needs for git, gh, pnpm
# and the like.
launch_path=""
add_path() { case ":$launch_path:" in *":$1:"*) ;; *) launch_path="${launch_path:+$launch_path:}$1" ;; esac; }
for bin in uv claude wecom-cli tmux node; do
    add_path "$(dirname "$(command -v "$bin" 2>/dev/null || echo /usr/bin/x)")"
done
IFS=: read -ra shell_path <<<"$PATH"
for dir in "${shell_path[@]}" /usr/bin /bin /usr/sbin /sbin; do
    [ -n "$dir" ] && add_path "$dir"
done
env_xml="    <key>PATH</key><string>$(xml "$launch_path")</string>"$'\n'
launch_env=("HOME=$HOME" "USER=$USER" "LOGNAME=$USER" "PATH=$launch_path")
# A proxy the shell needs to reach Anthropic is needed by launchd's copy too.
for var in HTTPS_PROXY https_proxy HTTP_PROXY http_proxy ALL_PROXY all_proxy NO_PROXY no_proxy; do
    if [ -n "${!var:-}" ]; then
        env_xml+="    <key>$var</key><string>$(xml "${!var}")</string>"$'\n'
        launch_env+=("$var=${!var}")
    fi
done

# Preflight: run Claude exactly as the agent will (launchd's environment plus .env,
# same flags) before installing anything, so a login that only exists in this shell
# fails here instead of failing every reply.
result="$(env -i "${launch_env[@]}" bash -c 'set -a; . "$1"; set +a; cd "$2" && claude -p --output-format json --tools "" --strict-mcp-config --disable-slash-commands --setting-sources local --no-session-persistence <<<"Reply with the single word: ok"' _ "$APP/.env" "$APP/workdir" 2>&1 || true)"
if ! grep -qE '"is_error": ?false' <<<"$result"; then
    echo "Claude Code does not work in the environment launchd will give the bot:" >&2
    echo "  $(grep -oE '"result": ?"[^"]*"' <<<"$result" | head -1)" >&2
    copyable=""
    for var in $CLAUDE_ENV_VARS; do
        [ -n "${!var:-}" ] && ! grep -q "^$var=" "$APP/.env" && copyable="$copyable $var"
    done
    if [ -n "$copyable" ]; then
        echo "This shell logs Claude Code in through$copyable, which launchd will not have." >&2
        echo "Run again with --copy-claude-env to write them into $APP/.env (mode 600)." >&2
    fi
    exit 1
fi
echo "Preflight: Claude answers in the agent's environment."

mkdir -p "$(dirname "$PLIST")"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(xml "$(command -v uv)")</string>
    <string>run</string>
    <string>--env-file</string>
    <string>$(xml "$APP/.env")</string>
    <string>$(xml "$APP/bot.py")</string>
  </array>
  <key>WorkingDirectory</key><string>$(xml "$APP")</string>
  <key>EnvironmentVariables</key>
  <dict>
$env_xml  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$(xml "$APP/bot.log")</string>
  <key>StandardErrorPath</key><string>$(xml "$APP/bot.log")</string>
</dict>
</plist>
EOF
plutil -lint "$PLIST" >/dev/null

# Another LaunchAgent running this same bot.py (for example one installed under an
# older label) would hold a second connection to the bot and the two would keep
# kicking each other off. Stop it and move its plist aside.
for other in "$HOME"/Library/LaunchAgents/*.plist; do
    [ -f "$other" ] && [ "$other" != "$PLIST" ] || continue
    grep -qF "$APP/bot.py" "$other" || continue
    other_label="$(plutil -extract Label raw "$other" 2>/dev/null || basename "$other" .plist)"
    launchctl bootout "$DOMAIN/$other_label" 2>/dev/null || true
    mv "$other" "$APP/$(basename "$other").disabled-$stamp"
    echo "Stopped another agent running this bot ($other_label); its plist is now in $APP."
done

before="$(grep -c "connected to WeCom" "$APP/bot.log" || true)"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
# bootout returns before the service is fully gone; bootstrapping too early fails
# with "5: Input/output error" and leaves the bot stopped.
for _ in $(seq 1 20); do
    launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || break
    sleep 0.5
done
for attempt in 1 2 3 4 5; do
    launchctl bootstrap "$DOMAIN" "$PLIST" 2>/dev/null && break
    [ "$attempt" = 5 ] && { echo "launchctl bootstrap failed 5 times; run: launchctl bootstrap $DOMAIN $PLIST" >&2; exit 1; }
    sleep 2
done

for _ in $(seq 1 60); do
    now="$(grep -c "connected to WeCom" "$APP/bot.log" || true)"
    [ "$now" -gt "$before" ] && { echo "Running under launchd ($LABEL): connected to WeCom."; exit 0; }
    sleep 1
done
echo "Started, but no 'connected to WeCom' within 60s. Check: tail -20 $APP/bot.log" >&2
exit 1
