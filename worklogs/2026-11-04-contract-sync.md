# 2026-11-04 契约同步：设置层与 17 个工具

## 1. 需求

`dsh-snapshot` 已把设置表面（DSH 表单行 `snapshot-settings` + `get_settings` + `GET/PUT /settings`）
和图表/导入等工具做完并跑通测试，但 `ARCHITECTURE.json` 仍停留在旧口径：`layers.shells` 写
`tools: 10` / `endpoints: 11`，`mcp.tools` 少 `get_settings`，`api.endpoints` 少 `/settings`。
本轮把契约回写到实现，不改任何代码路径。

## 2. ARCHITECTURE.json 变化

| 位置 | 旧 | 新 |
|---|---|---|
| `layers.shells[0].tools` | 10 | 17 |
| `layers.shells[1].endpoints` | 11 | 19 |
| `mcp.tools` | 16 条 | + `get_settings`（read，`SettingsStore.resolve().public()`） |
| `api.endpoints` | 17 条 | + `/settings` GET（`settings.get`）、PUT（`settings.put`） |

均为「纯新增/计数回写」：不改不变量，不改已有工具与端点的语义。

## 3. 修改文件

- `ARCHITECTURE.json` — 上表四处
- `ARCHITECTURE.md` — 工具数 16→17、读行补 `get_settings`、HTTP 表补 `/settings`、
  验证体系 10→17、部署形态改为本地目录安装、新增「设置」段落
- `worklogs/2026-11-04-contract-sync.md` — 本文件

## 4. 业务逻辑变化

无。本轮只动契约与文档；代码改动在 `dsh-snapshot` 仓库同主题提交
`366d7dc`（设置表单桥）与 `59db112`（TSA 拒绝原因），已推送 `origin/main`。

## 5. validate_arch 结果

```text
python scripts/validate_arch.py --arch ARCHITECTURE.json --app api:app \
  --root E:\dsh-snapshot --ignore / --ignore /chart

framework=fastapi json_routes=19 app_routes=21
OK
```

`app_routes=21` 含 `/` 与 `/chart` 两个网页入口（`--ignore` 排除），契约 19 条全部命中。

## 6. 测试命令与通过率

```text
cd E:\dsh-snapshot && python -m pytest -q
exit=0，0 failed，7 skipped（test_postgres.py 需 SNAPSHOT_TEST_DSN）
ARCHITECTURE.json json.load() 通过：tools=17, endpoints=19, mcp.tools=17, api.endpoints=19
```

## 7. 风险 / 外部 API

- 无新增外部 API；`/settings` 已存在于 `api.py`，本轮只是登记。
- `PUT /settings` 会写本地 `settings.json`（已有行为，密钥不回显，文件 chmod 600 为 best effort）。
- 契约由 validate_arch 只校验 HTTP 路由；MCP 工具数没有机器校验，靠实现与契约同步维护。

## 8. 未完成项

- DSH 安装产物中的 generation 未重装：`snapshot-settings` 行已在线上生效，重装非必需。

## 9. 追加（同日，第二次「批准修改」）

`security.settings` 已落盘（`env` / `file` / `precedence` / `keys` / `secrets` / `surface`），
`ARCHITECTURE.md` 增加「### 设置」小节；原第 8 节第 1 条因此关闭。
`validate_arch` 复核：`framework=fastapi json_routes=19 app_routes=21 / OK`，JSON 合法
（`security` = auth / timestamps / settings）。
