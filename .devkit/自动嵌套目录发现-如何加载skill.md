根据 Claude Code 文档，这里是关于 skills 加载的关键信息：

自动嵌套目录发现
Claude Code 自动支持从嵌套子目录发现 skills。当你在子目录中工作时，它会自动查找该目录下的 .claude/skills/、.claude/rules/ 和 .claude/agents/。

例如，如果你的结构是：


AmberProject/
├── .claude/skills/          # 项目级 skills
├── 1-planning/.claude/
│   ├── skills/
│   ├── rules/
│   └── agents/
├── 2-design/.claude/
│   ├── skills/
│   └── rules/
└── 3-backend/.claude/
    └── skills/
当你在 3-backend/ 目录工作时，Claude Code 会自动加载 3-backend/.claude/ 中的 skills。

加载优先级
级别	路径	作用范围
Enterprise	托管设置	组织所有用户
Personal	~/.claude/skills/	你的所有项目
Project	.claude/skills/	当前项目
Nested	子目录/.claude/skills/	在该子目录工作时
没有显式路径覆盖
文档没有提供显式指定加载特定目录 skills 的配置选项。加载机制是隐式的——基于你当前的工作目录自动发现。

替代方案
使用 frontmatter 的 paths 字段 - 在 skill 中限定适用路径
使用 --add-dir 参数 - 加载额外目录的 CLAUDE.md 和 rules（不含 skills）

CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ./specific-dir

如果你希望在根目录也能用特定子目录的 skills，建议将这些 skills 提升到项目级 .claude/skills/ 或使用 paths 字段控制适用范围。