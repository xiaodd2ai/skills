# 企业微信机器人自动回复

[技能入口](../../skills/productivity/wecom-autoreply/SKILL.md) · [运维手册](../../skills/productivity/wecom-autoreply/references/operations.md)

## 做什么

在你的 Mac 上装一个常驻的企业微信智能机器人。同事给机器人发消息，由无工具、无 MCP、空工作目录的 `claude -p` 写回复；需要你本人处理的事（审批、决定、要资料、催进度）记成带编号的待办，并推送到你的企业微信。

你自己和机器人单聊时进入主人模式：问「有什么要我处理的？」列出未完成待办，说「#3 做完了」即可关闭。你也可以发 `/task <目录> <要做的事>`，让 Mac 上的 Claude Code 带工具、按 auto mode 在该目录执行任务。被 auto mode 拦下的操作会推给你，回 `/yes` 只放行这几个操作，回 `/no` 让它绕开。

launchd 负责常驻：崩溃、注销、重启后都会自动拉起长连接。

## 什么时候使用

- 想让企业微信机器人替你先接住同事的消息，把要你办的事整理成待办。
- 第一次安装 wecom-cli、配置机器人凭证，或让机器人常驻。
- 机器人掉线、不回复、推送收不到，需要排查。
- 人不在电脑前，想在企业微信里给 Mac 上的 Claude Code 派任务。

调用示例：

> 使用 $wecom-autoreply，帮我在这台 Mac 上装好企业微信机器人，用 Claude Code 自动回复，并用 launchd 常驻。

需要 macOS、已登录的 Claude Code、`uv`、Node 18+，以及企业微信管理后台里一个开启了「API 模式 → 长连接」的智能机器人。

## 常见问题

**同事的消息会发到哪里？**

每条发给机器人的消息都会作为提示词发给 Anthropic。安装前要确认这对给机器人发消息的人是可以接受的；`ALLOWED_USERS` 可以限制只回复哪些人。

**机器人能替我回复发给我本人的消息吗？**

不能。它只收得到发给机器人的消息。发给你本人账号的消息读不到，也无法代你回复。

**同事能让机器人执行命令吗？**

不能。回复用的 Claude 没有任何工具，同事只能拿到文字。只有 `OWNER_USERID` 对应的你本人、在单聊里，才能用 `/task` 派任务；同样的命令从别人或群里发来，只当普通文字处理。

**派出去的任务安全吗？**

任务用你自己的 Claude Code 设置和 auto mode 运行。auto mode 拦下的操作不会执行，要等你在企业微信里批准；批准只对那次续跑有效，名单存在那次运行的环境变量里，会话无法改写。auto mode 只对部分操作调用分类器：它视为常规的命令，以及你在任务描述里点名要做的操作，不经检查就会执行。派任务前按这个边界判断。

**Mac 睡眠时怎么办？**

机器人跑在这台 Mac 上，睡眠或关机期间不回复，唤醒后自动恢复。

**之前装过其他版本的这个机器人怎么办？**

重新运行 `install.sh` 即可。如果另一个 LaunchAgent 在跑同一个 `~/wecom-autoreply/bot.py`，脚本会停掉它，并把它的 plist 移到应用目录，避免同一个机器人开两条长连接、互相踢下线。`.env`、`persona.md`、待办和日志都会保留。

**凭证放在哪里？**

`WECOM_BOT_SECRET` 等写在 `~/wecom-autoreply/.env`（权限 600），不贴进对话、不写进 plist。Claude Code 用环境变量登录时，`install.sh --copy-claude-env` 会把这些变量追加到 `.env`。

## 完成标准

- `install.sh` 的预检通过：Claude 在 launchd 的环境里能正常回答。
- `uv run ~/wecom-autoreply/bot.py --test "你好"` 能得到回复。
- 日志里出现 `connected to WeCom`；同事发消息后有 `inbound` 和 `reply to`。需要你处理的消息出现 `owner action` 和 `notified owner via WeCom`。
- 你问机器人「有什么要我处理的？」能列出带编号的待办。
- 启用派任务时，`--test-task <目录> "执行 pwd，告诉我结果"` 能返回结果。
