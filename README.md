# StuArchive

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)
[![Data Source: Kivo Wiki](https://img.shields.io/badge/data%20source-Kivo%20Wiki-blue.svg)](https://kivo.wiki/)
[![Sync: Daily](https://img.shields.io/badge/sync-daily-green.svg)](.github/workflows/sync.yml)

StuArchive 是 **Kivo Wiki 公开《蔚蓝档案》JSON 数据的非官方静态镜像**。项目每天自动同步上游数据，并通过 GitHub Raw / GitCode Raw 暴露 JSON 文件，配合预生成 `lookup.json` 索引实现类似 API 的查询接口。

本项目不下载图片、音频、模型等二进制素材，只保存 Kivo API 返回的 JSON 和素材 URL。这样仓库体积更可控，也能避免把官方素材重新分发到本仓库。

## 项目特性

- Kivo Wiki 镜像：同步 Kivo Wiki 公开 JSON 端点，保留上游来源和许可声明。
- Raw API 访问：直接通过 Raw URL 读取 `data/*.json`，不需要部署服务器。
- 查询索引：为集合生成 `lookup.json`，支持按 ID、学生姓名、条目名称、标题和本地化别名定位数据。
- 学生页面级资料：生成 `students/profiles/{id}.json`，聚合学生详情、学校、关系、技能、装备、素材、礼物、家具、语音和鉴赏等常用字段。
- 每日自动同步：GitHub Actions 每天定时同步 Kivo 数据，并将更新推送到配置的镜像仓库。
- 许可显式：仓库原创脚本、文档和索引结构使用 CC BY-NC-SA 4.0；镜像内容保留 Kivo、第三方、Nexon 和 Yostar 的原始声明。

## 许可与来源

本仓库原创的脚本、文档、索引结构使用 [CC BY-NC-SA 4.0](LICENSE)。镜像数据中的上游内容保留其原始来源、署名和许可要求；《蔚蓝档案》官方素材相关权利属于其权利方，本项目只镜像 JSON 中出现的素材 URL。

详见 [LICENSE](LICENSE)、[LICENSE-DATA.md](LICENSE-DATA.md) 和 [NOTICE.md](NOTICE.md)。

## GitHub 介绍

仓库 About / Description 建议使用：

```text
Kivo Wiki Blue Archive static JSON mirror with Raw API lookup indexes and daily automated sync.
```

建议 Topics：

```text
blue-archive, kivo-wiki, raw-api, json-api, static-api, cc-by-nc-sa-4-0
```

## 快速开始

```bash
python3 scripts/sync.py
python3 scripts/validate.py
```

默认同步会抓取 `sources.json` 中配置的所有单页端点和分页索引，生成 `data/` 目录。

需要同步每个条目的详情 JSON 时运行：

```bash
python3 scripts/sync.py --include-details
python3 scripts/validate.py
```

如需把默认关闭的超大集合详情也同步，例如 `timeline`：

```bash
python3 scripts/sync.py --include-details --include-disabled-details
```

## Raw API 入口

GitHub Raw 基础地址：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data
```

入口清单：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/index.json
```

示例：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/index.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/lookup.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/pages/1.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/76.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/profiles/76.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/current/events/cn.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/current/pick-ups/jp.json
```

`lookup.json` 是预生成查询索引，可按 ID、学生姓名、条目名称、标题等别名在客户端快速定位条目，并提供对应 `detail_path` / `detail_raw_url` 与学生 `profile_path` / `profile_raw_url`。每日自动同步会默认生成详情文件和学生页面级资料；本地手动同步需要传入 `--include-details`。

`students/{id}.json` 保存 Kivo 原始详情响应；`students/profiles/{id}.json` 是 StuArchive 生成的页面级聚合资料，会解析学校、关系、装备、养成素材、礼物、家具等常见引用，适合客户端直接展示学生详情页。

同步写出的 `//static.kivo.wiki/...` 静态资源地址会被转换为 `https://static.kivo.wiki/...`。页面 Markdown 中的 `files/...` / `/files/...` 资源也会转换为 `https://kivo.wiki/files/...`，可直接用于图片、封面等资源加载。

完整说明见 [API 文档](docs/API.md) 和 [更新流程](docs/UPDATE.md)。

现代 API 工具导入：

- Apifox/OpenAPI 文档：[docs/openapi.json](docs/openapi.json)
- Apifox 导入说明：[docs/APIFOX.md](docs/APIFOX.md)

国内访问镜像：

- 镜像仓库与 Pages 配置：[docs/MIRRORS.md](docs/MIRRORS.md)
- GitCode Raw API：https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data/index.json

## 目录结构

```text
data/
  index.json                 # Raw API 总入口
  current/                   # 当前活动、总力战、Pickup 等
  meta/                      # API 根信息、统计信息
  students/
    index.json               # 学生集合索引
    lookup.json              # 按 ID/姓名/别名查询
    pages/1.json             # Kivo 原始分页响应
    76.json                  # 学生详情，需 --include-details
    profiles/76.json         # 学生页面级聚合资料
```
