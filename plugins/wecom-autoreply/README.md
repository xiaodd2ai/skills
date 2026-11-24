# 企业微信机器人自动回复

独立插件，单独安装。[技能入口](skills/wecom-autoreply/SKILL.md) · [运维手册](skills/wecom-autoreply/references/operations.md)

## 安装

在 Claude Code 中运行：

```text
/plugin install wecom-autoreply --marketplace xiaodd2ai/skills
```

一行安装需要 Claude Code 2.1.275 或更高版本。更早的版本分两步：

```text
/plugin marketplace add xiaodd2ai/skills
/plugin install wecom-autoreply@xiaodd2ai
```

装好后对 Claude Code 说「帮我在这台 Mac 上装好企业微信机器人」，它会按技能的步骤检查环境、安装 wecom-cli、引导你填写机器人凭证并启动常驻服务。

## 做什么

在你的 Mac 上装一个常驻的企业微信智能机器人。同事给机器人发消息，由无工具、无 MCP、空工作目录的 `claude -p` 写回复；需要你本人处理的事（审批、决定、要资料、催进度）记成带编号的待办，并推送到你的企业微信。

你自己在单聊里对机器人说的话，会直接进 Mac 上的 Claude Code 终端（tmux 会话加一个终端窗口，带工具，auto mode，用你平时的 Claude Code 设置）：

- 还没有会话时，机器人先留着这条消息，问你在哪个目录开。回 `/yes` 用 `.env` 里的 `TASK_BASE_DIR`（默认主目录），回一个路径换目录（绝对路径、`~/…`，或相对 `TASK_BASE_DIR` 的路径），回 `/no` 取消。
- 会话开着时，之后的每条消息都进同一个会话，一件事一个会话。发 `/new` 结束，下一条消息重新问目录。
- 每轮结束后，`Stop` hook（`push_hook.py`）把 Claude 的回复推回你的企业微信。
- 待办也交给这个会话：问「有什么要我处理的？」它会读待办列表，说「#3 做完了」它会标记完成。

终端窗口关了也没关系，会话还在后台跑，用 `tmux -L wecom attach -t claude` 重新打开。

launchd 负责常驻：崩溃、注销、重启后都会自动拉起长连接。

## 什么时候使用

- 想让企业微信机器人替你先接住同事的消息，把要你办的事整理成待办。
- 第一次安装 wecom-cli、配置机器人凭证，或让机器人常驻。
- 机器人掉线、不回复、推送收不到，需要排查。
- 人不在电脑前，想在企业微信里让 Mac 上的 Claude Code 开终端干活。

调用示例：

> 帮我在这台 Mac 上装好企业微信机器人，用 Claude Code 自动回复，并用 launchd 常驻。

需要 macOS、已登录的 Claude Code、`uv`、Node 18+、`tmux`，以及企业微信管理后台里一个开启了「API 模式 → 长连接」的智能机器人。

## 常见问题

**同事的消息会发到哪里？**

每条发给机器人的消息都会作为提示词发给 Anthropic。安装前要确认这对给机器人发消息的人是可以接受的；`ALLOWED_USERS` 可以限制只回复哪些人。

**机器人能替我回复发给我本人的消息吗？**

不能。它只收得到发给机器人的消息。发给你本人账号的消息读不到，也无法代你回复。

**同事能让机器人执行命令吗？**

不能。回复用的 Claude 没有任何工具，同事只能拿到文字。只有 `OWNER_USERID` 对应的你本人、在单聊里发的消息才会进终端；同样的消息从别人或群里发来，只当普通文字回复。

**终端里的 Claude Code 安全吗？**

它用你自己的 Claude Code 设置和 auto mode 运行。auto mode 拦下的操作不会执行，也不会推到企业微信等你批准：Claude 会在回复里说明拦下了什么，要回到电脑前在终端里处理。auto mode 只对部分操作调用分类器：它视为常规的命令，以及你在消息里点名要做的操作，不经检查就会执行。发消息前按这个边界判断。机器人的 `WECOM_BOT_ID` / `WECOM_BOT_SECRET` 不会传进这个会话。

**发了消息却一直没回复怎么办？**

看一眼终端（`tmux -L wecom attach -t claude`）：Claude 可能还在干活，可能停在对话框上（比如第一次进某个目录时的信任确认），也可能 `push_hook.py` 报了错（wecom-cli 没授权，或你还没给机器人发过消息）。

**Mac 睡眠时怎么办？**

机器人跑在这台 Mac 上，睡眠或关机期间不回复，唤醒后自动恢复。

**之前装过其他版本的这个机器人怎么办？**

重新运行 `install.sh` 即可。如果另一个 LaunchAgent 在跑同一个 `~/wecom-autoreply/bot.py`，脚本会停掉它，并把它的 plist 移到应用目录，避免同一个机器人开两条长连接、互相踢下线。`.env`、`persona.md`、待办和日志都会保留。

从 0.4.0 升级时，`/task`、`/yes` 批准、`/re`、`/tasks` 这套后台任务机制已经去掉，`install.sh` 会把旧的 `approve_hook.py` 改名留作备份，`tasks.json` 不再使用。

**凭证放在哪里？**

`WECOM_BOT_SECRET` 等写在 `~/wecom-autoreply/.env`（权限 600），不贴进对话、不写进 plist。Claude Code 用环境变量登录时，`install.sh --copy-claude-env` 会把这些变量追加到 `.env`。

## 完成标准

- `install.sh` 的预检通过：Claude 在 launchd 的环境里能正常回答。
- `uv run ~/wecom-autoreply/bot.py --test "你好"` 能得到回复。
- 日志里出现 `connected to WeCom`；同事发消息后有 `inbound` 和 `reply to`。需要你处理的消息出现 `owner action` 和 `notified owner via WeCom`。
- 你给机器人发一条消息，回 `/yes` 后 Mac 上弹出 Claude Code 终端，它的回复出现在企业微信里。
- 不经过企业微信时，`uv run --env-file ~/wecom-autoreply/.env ~/wecom-autoreply/bot.py --test-owner` 能打开同样的终端会话。
