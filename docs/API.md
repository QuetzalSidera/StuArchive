# StuArchive Raw API

StuArchive 是静态 JSON 文件集合，不运行服务器。客户端通过 GitHub Raw URL 直接读取 JSON 文件，再在本地进行筛选、缓存或索引。

## OpenAPI / Apifox

本项目提供 OpenAPI 3.1 文档，可导入 Apifox：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/docs/openapi.json
```

本地文件路径：

```text
docs/openapi.json
```

导入说明见 [Apifox 导入指南](APIFOX.md)。当 `sources.json` 新增或调整资源后，运行以下命令重新生成 OpenAPI 文档：

```bash
python3 scripts/generate_openapi.py
```

## 基础地址

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data
```

总入口：

```text
GET /index.json
```

完整 URL：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/index.json
```

`data/index.json` 会列出本次生成时间、上游来源、许可声明、资源清单、每个集合的入口文件和 Raw URL。

## 响应类型

### 单页资源

单页资源直接保存 Kivo API 的原始 JSON 响应，例如：

```text
GET /meta/api-root.json
GET /meta/statistics.json
GET /current/event.json
GET /current/raid.json
GET /current/pick-up.json
GET /current/lucky-item.json
GET /current/students-birthday-week.json
```

形态与上游一致：

```json
{
  "code": 2000,
  "codename": "Koyuki",
  "data": {},
  "message": "OK",
  "success": true,
  "time": 1780426814,
  "version": "1.0.0-beta.43"
}
```

### 集合索引

集合索引是 StuArchive 生成的聚合文件：

```text
GET /students/index.json
GET /items/index.json
GET /timeline/index.json
```

形态：

```json
{
  "schema_version": "1.0.0",
  "name": "students",
  "generated_at": "2026-06-02T19:00:00Z",
  "list_key": "students",
  "id_key": "id",
  "max_page": 48,
  "synced_pages": 48,
  "total_items": 578,
  "details_synced": 0,
  "items": [],
  "pages": [],
  "details": []
}
```

`items` 是所有分页中对应列表字段的合并结果，适合做列表查询和客户端搜索。

### 查询索引

GitHub Raw 是静态文件服务，不能执行真正的服务端查询。StuArchive 为每个集合额外生成 `lookup.json`，用于更方便地按 ID、名称、标题或本地化别名查询：

```text
GET /students/lookup.json
GET /items/lookup.json
GET /schools/lookup.json
GET /articles/lookup.json
```

`lookup.json` 形态：

```json
{
  "schema_version": "1.0.0",
  "name": "students",
  "normalization": "NFKC, trim, collapse whitespace, casefold, then remove whitespace.",
  "total_items": 474,
  "alias_count": 5382,
  "normalized_alias_count": 3693,
  "by_id": {
    "76": {
      "id": 76,
      "source_path": "students/index.json",
      "source_raw_url": "https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/index.json",
      "detail_path": "students/76.json",
      "detail_raw_url": "https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/76.json",
      "item": {}
    }
  },
  "by_alias": {
    "小鸟游星野": ["76"],
    "小鳥遊ホシノ": ["76"]
  },
  "by_normalized_alias": {
    "小鸟游星野": ["76"]
  }
}
```

学生集合会自动生成默认中文、简中、日文姓名组合，并结合简中/繁中/日文皮肤名生成别名，包括：

```text
小鸟游星野
小鸟游 星野
星野
小鳥遊ホシノ
陆八魔阿露（礼服）
陸八魔アル（ドレス）
```

其他集合会使用 `name`、`name_cn`、`name_jp`、`name_zh_tw`、`title`、`title_cn`、`title_jp`、`title_zh_tw`、`label`、`slug`、`original_file_name` 等字段生成别名。

客户端查询示例：

```js
const base = "https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data";
const lookup = await fetch(`${base}/students/lookup.json`).then((res) => res.json());

const key = "陆八魔阿露（礼服）".normalize("NFKC").trim().replace(/\s+/g, "").toLocaleLowerCase();
const [id] = lookup.by_normalized_alias[key] ?? [];
const student = id ? lookup.by_id[id].item : null;
```

### 原始分页

每个集合保留 Kivo API 的原始分页响应：

```text
GET /students/pages/1.json
GET /students/pages/2.json
GET /items/pages/1.json
GET /timeline/pages/1.json
```

分页文件不做结构改写，便于对照上游响应。

### 条目详情

详情文件只有在同步时使用 `--include-details` 才会生成：

```text
GET /students/76.json
GET /items/1742.json
GET /schools/1.json
GET /articles/77.json
```

详情文件保存 Kivo API 的原始详情响应。

## 资源表

| 名称                       | Raw 路径                                  | 上游路径                           | 列表字段          | 详情                           |
|--------------------------|-----------------------------------------|--------------------------------|---------------|------------------------------|
| `api-root`               | `/meta/api-root.json`                   | `/`                            | -             | -                            |
| `statistics`             | `/meta/statistics.json`                 | `/statistics/index`            | -             | -                            |
| `current-event`          | `/current/event.json`                   | `/data/event/now`              | -             | -                            |
| `current-raid`           | `/current/raid.json`                    | `/data/raid/now`               | -             | -                            |
| `current-pick-up`        | `/current/pick-up.json`                 | `/data/pick_up/`               | -             | -                            |
| `lucky-item`             | `/current/lucky-item.json`              | `/data/lucky_item/`            | -             | -                            |
| `students-birthday-week` | `/current/students-birthday-week.json`  | `/data/students/birthday/week` | -             | -                            |
| `students`               | `/students/index.json`                  | `/data/students/`              | `students`    | `/students/{id}.json`        |
| `items`                  | `/items/index.json`                     | `/data/items/`                 | `item`        | `/items/{id}.json`           |
| `equipments`             | `/equipments/index.json`                | `/data/equipments/`            | `equipment`   | `/equipments/{id}.json`      |
| `schools`                | `/schools/index.json`                   | `/data/schools/`               | `school`      | `/schools/{id}.json`         |
| `models`                 | `/models/index.json`                    | `/data/models/`                | `model`       | `/models/{id}.json`          |
| `spines`                 | `/spines/index.json`                    | `/data/spines/`                | `spine`       | `/spines/{id}.json`          |
| `relations`              | `/relations/index.json`                 | `/data/relations/`             | `relation`    | `/relations/{id}.json`       |
| `declare-icons`          | `/interactive/declare-icons/index.json` | `/interactive/declares/icons`  | `icon`        | -                            |
| `bulletins`              | `/bulletins/index.json`                 | `/bulletins/`                  | `bulletin`    | `/bulletins/{id}.json`       |
| `news`                   | `/news/index.json`                      | `/news/`                       | `news`        | `/news/{id}.json`            |
| `galleries`              | `/galleries/index.json`                 | `/galleries/`                  | `gallery`     | `/galleries/{id}.json`       |
| `musics`                 | `/musics/index.json`                    | `/musics/`                     | `music`       | `/musics/{id}.json`          |
| `timeline`               | `/timeline/index.json`                  | `/timeline/`                   | `timeline`    | `/timeline/{id}.json`，默认不抓详情 |
| `walkthroughs`           | `/walkthroughs/index.json`              | `/walkthroughs/`               | `walkthrough` | `/walkthroughs/{id}.json`    |
| `articles`               | `/articles/index.json`                  | `/articles/`                   | `article`     | `/articles/{id}.json`        |
| `comics`                 | `/comics/index.json`                    | `/comics/`                     | `comics`      | `/comics/{id}.json`          |

## 查询示例

读取学生索引：

```bash
curl -L https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/index.json
```

按学生姓名读取查询索引：

```bash
curl -L https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/lookup.json
```

读取星野详情：

```bash
curl -L https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/76.json
```

GitHub Raw 不支持服务端筛选。需要按名称、ID、标题等条件查询时，优先读取对应 `lookup.json`；复杂条件仍可读取 `index.json` 后在客户端过滤 `items`。

## 静态资源 URL

Kivo API 中的协议相对静态资源 URL 会在同步时转换为绝对 URL，便于客户端直接使用：

```text
//static.kivo.wiki/images/students/.../avatar.png
```

会保存为：

```text
https://static.kivo.wiki/images/students/.../avatar.png
```
