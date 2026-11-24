# STATS C161 小组备用 Agent

从本目录运行 PowerShell。项目入口是 `agent.course`。同一实例按平台分配的游戏选择策略，每个对局座位有独立的进程和记忆。基于 UCLA 官方 starter 的 `d94be8c` 版本。

## 准备

安装 Python 3.11 或更高版本。从仓库根目录执行：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

已有 .env 时直接编辑原文件。保留官方服务器地址，在本机设置 ALTRUAGENT_OFFICIAL_AGENT_KEY 和 OPENAI_API_KEY。也可以从环境变量读取。试跑使用官方默认 gpt-4o-mini，OPENAI_MODEL 可覆盖。模型服务必须支持结构化输出。

## 运行和复核

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/course_evidence.py
.venv/Scripts/python scripts/course_evidence.py --live-model
.venv/Scripts/python -m agent --check-tournament --agent agent.course
.venv/Scripts/python -m agent --match --agent agent.course
```

第二条生成固定局面的离线 CSV。第三条会调用模型服务，各测一个决策。最后两条需要小组平台密钥。在 Dashboard 的 Testing 创建 Pokémon VGC doubles draft 和七人 Werewolf 两场比赛，选择 Mine (self-hosted)，其余座位由可用对手补齐。所有座位连接后开始。观察终局并用平台结果核对自己的座位。每把密钥只启动一个运行实例。中断后用原命令重新连接。回到项目根目录导出：

```powershell
.venv/Scripts/python -m agent.analysis match_logs evidence/platform
```

两个导出文件分别是逐次决策或终局事件、按数据来源和游戏汇总的结果。截图或抄录平台终局、比赛 ID 和座位，用于核验终局。后台测试只有一方获胜时也要等服务器给出结果。根据比赛页面区分 testing 和 tournament。若终局字段缺失，记录 unknown，并保留页面结果供核对。

## Realy 复现

用课程账号打开 [Realy](https://table-reasoning.vercel.app/)，上传 evidence 下相应来源的 events.csv，保存会话。已连上课程 Realy MCP 时先用 realy_describe_scope 选中该会话，再让 realy_retrieve 执行同一个问题。离线示例见 report 草稿。测试赛完成后，对 platform/events.csv 重跑，保存返回的表、操作步骤和差异说明。实时模型与离线模拟使用各自的文件。

给 Realy 的汇总问题可以直接粘贴：

> Group events.csv by source and game. Output one row per group. For decision events count rows as decisions, average latency_ms as mean_latency_ms (keep at least three decimal places), and sum fallback as fallbacks. For result events count each distinct (match, seat) once as completed_seats. Count won, lost, drew and all remaining outcomes as wins, losses, draws and other_results. Use zero for missing counts, and leave the mean empty if there are no decisions. Return a CSV with the columns source, game, decisions, mean_latency_ms, fallbacks, completed_seats, wins, losses, draws, other_results.

将 Realy 实际返回的 CSV 保存为同目录的 realy-summary.csv。对已保存的离线示例运行下列命令；实赛后将目录换为 evidence/platform。

```powershell
.venv/Scripts/python scripts/verify_export.py evidence/offline --external-summary evidence/offline/realy-summary.csv
```

## 小组决定启用时

按课程规则确认提供给平台的公开 GitHub 仓库，给两款游戏分别登记。关闭测试运行，再执行下列命令。报名、仓库发布和课程提交均由组内确认后进行。

```powershell
.venv/Scripts/python -m agent --tournament --agent agent.course
```

修改策略的位置在 agent/course.py 顶部。给每次改动记录日期、依据、修改前后版本和回归测试结果；把实测对局结果补进报告。展示和报告文字在 deliverables 中。
