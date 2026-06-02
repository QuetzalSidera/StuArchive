# Apifox / OpenAPI 导入指南

StuArchive 提供 OpenAPI 3.1 文档，可导入 Apifox 或其他支持 OpenAPI 的 API 工具。

## 导入文件

OpenAPI 文件：

```text
docs/openapi.json
```

GitHub Raw 导入 URL：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/docs/openapi.json
```

导入后，Apifox 中的服务地址会使用：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data
```

## 接口分组

OpenAPI 文档按以下标签分组：

- `Manifest`：总入口 `/index.json`
- `Single resources`：当前活动、统计、API 根信息等单文件资源
- `Collection indexes`：集合聚合索引，如 `/students/index.json`
- `Lookup indexes`：预生成查询索引，如 `/students/lookup.json`
- `Original pages`：原始分页响应，如 `/students/pages/{page}.json`
- `Details`：按 ID 的详情文件，如 `/students/{id}.json`

## 使用注意

- GitHub Raw 是静态文件服务，不支持服务端搜索、排序、过滤或 POST。
- 要按 ID、学生姓名、条目名称、标题等条件查询，优先请求集合 `lookup.json`，再通过 `by_id`、`by_alias` 或 `by_normalized_alias` 定位条目。
- 复杂条件查询仍可请求集合 `index.json`，再在客户端过滤 `items`。
- 详情文件需要运行 `python3 scripts/sync.py --include-details` 后才会生成。
- `timeline` 详情默认关闭；需要时运行 `python3 scripts/sync.py --resource timeline --include-details --include-disabled-details`。
- OpenAPI 文档由 `scripts/generate_openapi.py` 从 `sources.json` 生成。
- Kivo 的 `//static.kivo.wiki/...` 静态资源地址会被同步脚本保存为 `https://static.kivo.wiki/...`。
