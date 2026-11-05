# plans/

每个计划一份：`<plan-id>.md`（计划书）+ `<plan-id>.traceability.json`（追溯矩阵）。

计划书模板见 `../docs/templates/计划书.md`，矩阵格式见 `../docs/templates/追溯矩阵.md`。

门禁：

```bash
python scripts/check_traceability.py plans/<plan-id>.traceability.json --tests-root <code-repo>
```

全部条目 aligned 才算完成；`status: planned` 的条目允许测试暂缺，但必须在计划书「未完成项」里写明。
