# 更新流程

## 本地手动更新

1. 同步公开索引：

   ```bash
   python3 scripts/sync.py
   ```

2. 如需要每个条目的详情 JSON：

   ```bash
   python3 scripts/sync.py --include-details
   ```

3. 校验生成结果：

   ```bash
   python3 scripts/validate.py
   ```

4. 提交并推送：

   ```bash
   git add sources.json data README.md docs LICENSE LICENSE-DATA.md NOTICE.md scripts main.py
   git commit -m "chore: sync kivo data"
   git push origin main
   ```

## 添加或调整端点

1. 先探测端点是否返回 JSON：

   ```bash
   python3 scripts/probe_endpoints.py /data/students/
   python3 scripts/probe_endpoints.py /data/students/76
   ```

2. 修改 `sources.json`。

3. 运行一次小范围烟测：

   ```bash
   python3 scripts/sync.py --resource students --max-pages 1 --include-details --details-limit 2
   python3 scripts/validate.py
   ```

4. 确认结构无误后再运行完整同步。

## GitHub Raw 生效

推送到 `main` 后，Raw URL 通常会很快更新：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/index.json
```

Raw CDN 可能存在短时间缓存。对外使用时建议客户端带本地缓存和重试逻辑。

## 请求量控制

`sources.json` 中的 `request_delay_seconds` 用于控制请求间隔。完整详情同步会产生大量请求，建议保留合理延迟，不要并发抓取。

`timeline` 的详情默认关闭。如确实需要：

```bash
python3 scripts/sync.py --resource timeline --include-details --include-disabled-details
```
