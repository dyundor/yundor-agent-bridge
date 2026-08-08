python3 main.py "升级 Yundor Agent Bridge 到 v0.2。

目标：
把当前简单的 OpenCode API 调用器升级为项目管理代理。

要求：

1. 保留现有功能：
- Python 调用 OpenCode API
- 创建 session
- 发送 message

2. 新增模块：

project_reader.py
功能：
- 自动读取目标项目中的：
  AGENTS.md
  PROJECT_STATE.md
  PROJECT_DECISIONS.md

git_manager.py
功能：
- 获取执行前 git commit
- 获取执行后 git commit
- 获取 git diff summary

report_parser.py
功能：
- 从 DeepSeek 输出中提取：
  Sprint
  Commit
  Files Changed
  Tests
  Next Step

3. 修改 main.py：

执行流程：

启动
↓
读取项目上下文
↓
获取 git 状态
↓
发送任务给 OpenCode
↓
获取返回
↓
获取 git 状态
↓
生成执行报告


4. 增加 session 持久化：

如果 config.yaml 有 session_id：
继续使用。

如果没有：
创建新 session，并自动写入 config.yaml。


5. 不修改 market-intelligence 项目。

只修改 yundor-agent-bridge。

完成后输出：

Sprint Bridge v0.2 Summary

包含：
- 修改文件
- 测试结果
- 使用方式"
