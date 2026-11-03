# gitLab-dsh

> Sci-Pal 的「架构即代码」协作骨架：把 API 契约、开发流程与人工审批红线，从口头约定固化成仓库里的文件、脚本和 Git 钩子。

---

## 仓库定位

本仓库**不包含 Sci-Pal 的业务代码**，它承载的是项目的治理层：一份架构总览、一套 AI/人类协作规则、两个校验/脚手架脚本，以及三个物理拦截钩子。

目标是让「先改契约、再改代码」这件事无法被绕过——不是靠提醒，而是靠 `pre-commit` 和 `commit-msg` 让违规提交直接失败。

## 目录结构

| 路径 | 作用 |
|---|---|
| `.dsh_rules` | 最高优先级协作规则（规则 0–7），任何 AI 动手前必须先加载 |
| `AGENTS.md` | 给 AI 代码助手的项目说明书：技术栈、目录、环境变量、代码规范 |
| `ARCHITECTURE.md` | 架构总览，含各版本的模块清单、检索/生成/评测链路细节 |
| `docs/开发流程规范.md` | 「架构即代码」的完整操作手册：审批流、`planned` 状态、标准操作 |
| `scripts/validate_arch.py` | 校验 Flask 路由与 `ARCHITECTURE.json` 契约是否一致 |
| `scripts/scaffold_from_arch.py` | 依据 JSON 节点生成 Flask 蓝图 / MCP 工具骨架 |
| `.githooks/` | `pre-commit`、`commit-msg`、`pre-push` 三道物理拦截 |
| `gitLab.py` | 独立的机器学习实验脚本（随机森林 + SHAP），与本骨架无关 |

## 核心机制：架构即代码

### 真理源

`ARCHITECTURE.json` 被设计为系统唯一宪法，AI **只读不写**。需要修改时：

1. 在对话里输出拟修改的 JSON 代码块，说明原因与影响的路由；
2. 等待人类明确回复 **「批准修改」**；
3. 收到批准后才写入文件，并立即运行 `validate_arch.py`。

批准后的 commit message 必须包含 `[APPROVED_BY_HUMAN]`，否则 `commit-msg` 钩子拒绝提交。

### 状态流转

```text
planned        # 契约先行，Python 尚未实现，校验器只给 warning
  ↓ scaffold_from_arch.py 生成骨架
scaffold
  ↓ 实现并注册 blueprint
implemented    # 严格校验：路由、方法、参数必须与 JSON 完全一致
  ↓ validate_arch.py
通过
```

### 冲突处理原则

测试失败若源于代码与 JSON 契约不一致，**只允许改 Python 去适配 JSON**，禁止为了让测试变绿而反向修改 JSON 参数。

## 快速开始

### 1. 准备环境

```powershell
git clone https://github.com/williamchen520/gitLab-dsh.git
cd gitLab-dsh
python -m venv env_gitLab
.\env_gitLab\Scripts\Activate.ps1
```

> 首次在 PowerShell 激活若提示禁止运行脚本，先执行一次：
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. 启用钩子

```powershell
git config core.hooksPath .githooks
```

### 3. 校验架构契约

```powershell
python scripts/validate_arch.py
```

### 4. 从契约生成骨架

```powershell
python scripts/scaffold_from_arch.py --node <codegen.id>
```

生成结果写入 `generated/<id>/`，不会自动改动 `app.py` 或已有路由模块——注册与否由人决定。

## 协作红线（摘要）

| 规则 | 要求 |
|---|---|
| 规则 0 | `ARCHITECTURE.json` 只读，修改须人工批准 + `[APPROVED_BY_HUMAN]` |
| 规则 1 | 一个 PR 一个主题，不混入无关改动 |
| 规则 2 | 只有人类回复「批准合并」才能合并，CI 通过不算授权 |
| 规则 3 | 研究裁决（claim 状态、证据关系）与工程实现分开，写库前须确认 |
| 规则 4 | 同一方向连续两次负结果必须停下讨论，不得调参掩盖 |

完整规则见 [`.dsh_rules`](.dsh_rules)。

## 已知缺口

- **`ARCHITECTURE.json` 未纳入本仓库**：所有文档都称其为唯一真理源，但仓库中并不存在该文件，`validate_arch.py` 需要它才能运行。若它属于私有资产，请在克隆后自行放入根目录。
- `.dsh_rules` 中提到的 `scripts/run_tests_guarded.py`、`scripts/record_eval_metric.py` 尚未提供。
- `gitLab.py` 是一份独立的研究实验脚本（依赖 `pandas` / `scikit-learn` / `rdkit` / `shap`），与治理骨架没有依赖关系，保留在此仅作实验记录。

## 许可

[Apache-2.0](LICENSE)
