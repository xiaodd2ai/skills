# 技能模板

把下面的内容复制到 `skills/<分类>/<技能名>/SKILL.md`，再根据实际流程改写。模板留在文档目录中，不会作为技能加载。

`name` 与技能目录名一致，使用小写字母、数字和连字符。`description` 同时说明做什么和何时触发，避免只写一个抽象名称。

```markdown
---
name: example-skill
description: Describe the task this skill completes and the concrete requests or situations that should trigger it.
---

# Example Skill

## Purpose

Describe the outcome this skill helps the user achieve.

## Inputs

List the information or artifacts needed to start. Ask only for missing inputs that affect the result.

## Workflow

1. Inspect the available context and identify the intended outcome.
2. Perform the task using the smallest reliable workflow.
3. Check the result against the user's requirements.

## Completion criteria

Describe observable evidence that the task is complete.

## References

Link to relevant files in references/ only when the workflow needs them.
```

可选资源按需添加：

```text
example-skill/
├── SKILL.md
├── references/
├── scripts/
└── assets/
```

技能应从已经反复使用的流程中提炼，步骤写到可执行的程度，完成标准写到可检查的程度。
