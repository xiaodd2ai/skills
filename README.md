# skills

把日常工作中反复使用的方法沉淀为小而可组合的 Agent Skills。

这是 [xiaodd2ai](https://github.com/xiaodd2ai) 的个人技能仓库。目录组织参考 [mattpocock/skills](https://github.com/mattpocock/skills)，技能内容随实际使用逐步积累。

## 目录结构

```text
skills/
├── README.md
├── AGENTS.md
├── LICENSE
├── .claude/
│   └── CLAUDE.md
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── .github/workflows/
│   └── validate.yml
├── docs/
│   ├── skill-template.md
│   ├── engineering/
│   └── productivity/
├── scripts/
│   ├── list-skills.sh
│   └── check-repository.py
└── skills/
    ├── engineering/
    ├── productivity/
    ├── in-progress/
    ├── misc/
    └── deprecated/
```

## 技能分类

| 目录 | 用途 | 加入插件 |
| --- | --- | --- |
| [engineering](skills/engineering/README.md) | 开发、调试、测试、代码审查等工程流程 | 是 |
| [productivity](skills/productivity/README.md) | 写作、整理、复盘等日常工作流程 | 是 |
| [in-progress](skills/in-progress/README.md) | 正在试验、尚未稳定的技能 | 否 |
| [misc](skills/misc/README.md) | 暂时保留、低频使用的技能 | 否 |
| [deprecated](skills/deprecated/README.md) | 已弃用的技能及替代方案说明 | 否 |

## 已发布技能

### 手动调用

暂无仅限手动调用的技能。

### 自动调用

- [screen-boss-candidates](skills/productivity/screen-boss-candidates/SKILL.md)：保持当前筛选条件，逐位核验 BOSS直聘在线简历，并停留供用户判断。[使用说明](docs/productivity/screen-boss-candidates.md)

自动调用类技能也可以通过 `$技能名` 明确调用。当前已发布技能已加入插件配置。

## 新增一个技能

1. 根据成熟程度，在相应分类下建立目录，例如 `skills/in-progress/example-skill/`。
2. 按 [技能模板](docs/skill-template.md) 编写 `SKILL.md`，说明任务、触发场景、执行步骤和完成标准。
3. 长资料按需放入 `references/`，可执行工具放入 `scripts/`，模板或其他资源放入 `assets/`。
4. 在分类目录的 `README.md` 中补充链接和一句话说明。
5. 技能稳定后移入 `engineering/` 或 `productivity/`，同步本页索引、`docs/<分类>/<技能名>.md` 和 `.claude-plugin/plugin.json` 的 `skills` 列表。

本地校验：

```bash
bash scripts/list-skills.sh
python3 scripts/check-repository.py
```

GitHub Actions 会在提交和 Pull Request 时执行相同的基础校验。

## 许可证

[MIT](LICENSE)。
