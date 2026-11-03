# gitLab-dsh

> 一套可复用的「架构即代码」协作骨架：把 API 契约、开发流程与人工审批红线，从口头约定固化成仓库里的文件、脚本和 Git 钩子。

---

## 仓库定位

本仓库是 Sci-Pal 项目沉淀下来的**规范与脚手架骨架**，用作后续新项目的开发底座。

它分成两层，复用程度不同：

| 层 | 内容 | 新项目如何处理 |
|---|---|---|
| **规则层** | `.dsh_rules`、`AGENTS.md`、`docs/开发流程规范.md`、`.githooks/`、`scripts/` | **直接继承**，规则本身不随项目变化 |
| **架构层** | `ARCHITECTURE.json`、`ARCHITECTURE.md` | **清空重写**，必须针对新项目重新讨论、细化后成文 |

也就是说：流程不用再发明，但架构不能照抄。`ARCHITECTURE.md` 里现有的检索链路、模块清单、评测指标都是 Sci-Pal 的，新项目要连同一份新的 `ARCHITECTURE.json` 一起重新设计。

## 目录结构

| 路径 | 作用 | 层 |
|---|---|---|
| `.dsh_rules` | 最高优先级协作规则（规则 0–7），任何 AI 动手前必须先加载 | 规则 |
| `AGENTS.md` | 给 AI 代码助手的项目说明书：技术栈、目录、环境变量、代码规范 | 规则 |
| `docs/开发流程规范.md` | 「架构即代码」的完整操作手册：审批流、`planned` 状态、标准操作 | 规则 |
| `docs/开发说明.md` | 新项目（实验记录系统）的开发说明：领域模型、快照语义、分层架构、待决项 | 项目 |
| `docs/架构图.md` | 分层、领域模型、快照流程、存储布局四张图 + 25 个端点清单 | 项目 |
| `.githooks/` | `pre-commit`、`commit-msg`、`pre-push` 三道物理拦截 | 规则 |
| `scripts/validate_arch.py` | 校验 Flask 路由与 `ARCHITECTURE.json` 契约是否一致 | 规则 |
| `scripts/scaffold_from_arch.py` | 依据 JSON 节点生成 Flask 蓝图 / MCP 工具骨架 | 规则 |
| `ARCHITECTURE.md` | 架构总览（当前为 Sci-Pal 版本，需为新项目重写） | 架构 |
| `gitLab.py` | 机器学习实验记录（随机森林 + SHAP），作为实验脚本的存放样例 | 样例 |

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

## 新项目接入流程

1. **讨论架构**：确定项目目标、边界、技术栈、路由清单、数据模型与模块划分。
2. **写 `ARCHITECTURE.json`**：按讨论结果填充 `api.endpoints`，未实现的节点标 `status: "planned"`。
3. **重写 `ARCHITECTURE.md`**：用新项目的模块清单和链路替换 Sci-Pal 的内容。
4. **更新 `AGENTS.md`**：技术栈、目录结构、环境变量改成新项目的。
5. **跑校验**：`python scripts/validate_arch.py` 通过后，才允许写路由与业务逻辑。

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

## 待补齐

接入新项目时需要一并处理：

- **新建 `ARCHITECTURE.json`**：规则层的 `validate_arch.py` 依赖它，当前骨架中不存在，属预期——它是架构讨论的产物，不该预先提供。
- **`.dsh_rules` 引用的两个脚本尚缺**：`scripts/run_tests_guarded.py`、`scripts/record_eval_metric.py`，规则 4 的强制退出码依赖它们。
- **`ARCHITECTURE.md` 仍是 Sci-Pal 内容**：需随新架构讨论一并重写。

## 许可

[Apache-2.0](LICENSE)
