# StuArchive Raw API

StuArchive 是静态 JSON 文件集合，不运行服务器。客户端通过 GitHub Raw URL 直接读取 JSON 文件，再在本地进行筛选、缓存或索引。

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

| 名称 | Raw 路径 | 上游路径 | 列表字段 | 详情 |
| --- | --- | --- | --- | --- |
| `api-root` | `/meta/api-root.json` | `/` | - | - |
| `statistics` | `/meta/statistics.json` | `/statistics/index` | - | - |
| `current-event` | `/current/event.json` | `/data/event/now` | - | - |
| `current-raid` | `/current/raid.json` | `/data/raid/now` | - | - |
| `current-pick-up` | `/current/pick-up.json` | `/data/pick_up/` | - | - |
| `lucky-item` | `/current/lucky-item.json` | `/data/lucky_item/` | - | - |
| `students-birthday-week` | `/current/students-birthday-week.json` | `/data/students/birthday/week` | - | - |
| `students` | `/students/index.json` | `/data/students/` | `students` | `/students/{id}.json` |
| `items` | `/items/index.json` | `/data/items/` | `item` | `/items/{id}.json` |
| `equipments` | `/equipments/index.json` | `/data/equipments/` | `equipment` | `/equipments/{id}.json` |
| `schools` | `/schools/index.json` | `/data/schools/` | `school` | `/schools/{id}.json` |
| `models` | `/models/index.json` | `/data/models/` | `model` | `/models/{id}.json` |
| `spines` | `/spines/index.json` | `/data/spines/` | `spine` | `/spines/{id}.json` |
| `relations` | `/relations/index.json` | `/data/relations/` | `relation` | `/relations/{id}.json` |
| `declare-icons` | `/interactive/declare-icons/index.json` | `/interactive/declares/icons` | `icon` | - |
| `bulletins` | `/bulletins/index.json` | `/bulletins/` | `bulletin` | `/bulletins/{id}.json` |
| `news` | `/news/index.json` | `/news/` | `news` | `/news/{id}.json` |
| `galleries` | `/galleries/index.json` | `/galleries/` | `gallery` | `/galleries/{id}.json` |
| `musics` | `/musics/index.json` | `/musics/` | `music` | `/musics/{id}.json` |
| `timeline` | `/timeline/index.json` | `/timeline/` | `timeline` | `/timeline/{id}.json`，默认不抓详情 |
| `walkthroughs` | `/walkthroughs/index.json` | `/walkthroughs/` | `walkthrough` | `/walkthroughs/{id}.json` |
| `articles` | `/articles/index.json` | `/articles/` | `article` | `/articles/{id}.json` |
| `comics` | `/comics/index.json` | `/comics/` | `comics` | `/comics/{id}.json` |

## 查询示例

读取学生索引：

```bash
curl -L https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/index.json
```

读取星野详情：

```bash
curl -L https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/students/76.json
```

GitHub Raw 不支持服务端筛选。需要按名称、ID、学校等条件查询时，先读取对应 `index.json`，再在客户端过滤 `items`。
