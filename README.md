# StuArchive

StuArchive 将 Kivo Wiki 的公开《蔚蓝档案》JSON 数据镜像成仓库内的静态文件，通过 GitHub Raw URL 提供类似 API 的读取方式。

本项目不下载图片、音频、模型等二进制素材，只保存 Kivo API 返回的 JSON 和素材 URL。这样仓库体积更可控，也能避免把官方素材重新分发到本仓库。

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
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/pages/1.json
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/76.json
```

详情文件需要在同步时使用 `--include-details` 才会生成。

完整说明见 [API 文档](docs/API.md) 和 [更新流程](docs/UPDATE.md)。

## 目录结构

```text
data/
  index.json                 # Raw API 总入口
  current/                   # 当前活动、总力战、Pickup 等
  meta/                      # API 根信息、统计信息
  students/
    index.json               # 学生集合索引
    pages/1.json             # Kivo 原始分页响应
    76.json                  # 学生详情，需 --include-details
```

## 许可与来源

本仓库原创的脚本、文档、索引结构使用 CC BY-SA 4.0。镜像数据中的上游内容保留其原始来源、署名和许可要求；《蔚蓝档案》官方素材相关权利属于其权利方，本项目只镜像 JSON 中出现的素材 URL。

详见 [LICENSE](LICENSE)、[LICENSE-DATA.md](LICENSE-DATA.md) 和 [NOTICE.md](NOTICE.md)。
