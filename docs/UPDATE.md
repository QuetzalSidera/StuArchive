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
   git add sources.json data README.md docs LICENSE LICENSE-DATA.md NOTICE.md scripts
   git commit -m "chore: sync kivo data"
   git push origin main
   ```

## 定时同步与 Runner

GitHub-hosted runner 可能被 Kivo API 限速、拒绝或出现跨境网络超时。如果本地或国内机器可以稳定访问 Kivo，推荐使用 GitHub self-hosted runner 执行同步。

手动运行 `Sync Kivo Data` workflow 时，可以选择：

```text
runner = self-hosted
```

要让每日定时同步默认使用 self-hosted runner，在 GitHub 仓库中配置变量：

```text
Settings -> Secrets and variables -> Actions -> Variables -> New repository variable

Name: SYNC_RUNNER
Value: self-hosted
```

推荐用普通用户长期运行 self-hosted runner，不要直接用 `root` 运行 runner 或 `pip`。以下以 `gha-runner` 用户和 `/opt/actions-runner/stuarchive` 目录为例：

```bash
sudo useradd --create-home --shell /bin/bash gha-runner
sudo mkdir -p /opt/actions-runner/stuarchive
sudo chown -R gha-runner:gha-runner /opt/actions-runner/stuarchive
sudo -iu gha-runner
cd /opt/actions-runner/stuarchive
```

然后按照 GitHub 仓库页面提供的 self-hosted runner 安装命令下载并解压 runner，再用普通用户执行 `config.sh`：

```bash
./config.sh --url https://github.com/QuetzalSidera/StuArchive --token <RUNNER_TOKEN> --name stuarchive-sync --labels self-hosted,linux,stuarchive --work _work
exit
```

测试成功后，在 runner 目录中安装为系统服务。服务仍会以 `gha-runner` 普通用户运行：

```bash
cd /opt/actions-runner/stuarchive
sudo ./svc.sh install gha-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

如果之前已经用 `root` 安装过 runner 服务，先在旧 runner 目录停止并卸载旧服务，再按上面的普通用户方式重新配置：

```bash
sudo ./svc.sh stop
sudo ./svc.sh uninstall
```

如果不配置 `SYNC_RUNNER`，定时任务默认使用 `ubuntu-latest`。当 GitHub-hosted runner 无法访问 Kivo 时，workflow 会记录 warning 并跳过提交，避免每天因为上游网络策略标红。手动排查时可启用 `fail_on_sync_error` 让同步失败直接标红。

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

4. 更新 OpenAPI / Apifox 文档：

   ```bash
   python3 scripts/generate_openapi.py
   ```

5. 确认结构无误后再运行完整同步。

## 仅重建查询索引和 URL 规范化

如果没有重新抓取 Kivo，只需要基于当前 `data/` 重新生成 `lookup.json` 并把 `//static.kivo.wiki/...` 转换为绝对 URL：

```bash
python3 scripts/postprocess.py
python3 scripts/validate.py
```

## GitHub Raw 生效

推送到 `main` 后，Raw URL 通常会很快更新：

```text
https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data/index.json
```

Raw CDN 可能存在短时间缓存。对外使用时建议客户端带本地缓存和重试逻辑。

## 请求量控制

`sources.json` 中的 `request_delay_seconds` 用于控制请求间隔。完整详情同步会产生大量请求，建议保留合理延迟，不要并发抓取。

`timeout_seconds`、`request_retries`、`request_retry_delay_seconds` 用于控制单次请求超时和失败重试。GitHub Actions 上的公网访问偶尔会出现 read timeout，默认配置会重试后再判定失败。

`current-*` 等实时单页端点可能因为 Kivo 上游后端超时返回 504 或长期无响应。同步脚本会对这类端点使用更短的资源级 timeout；若本地已有旧文件，会复用旧数据继续同步其他资源，并在 `data/index.json` 中通过 `stale`、`sync_error`、`sync_errors` 标记该资源。

`timeline` 的详情默认关闭。如确实需要：

```bash
python3 scripts/sync.py --resource timeline --include-details --include-disabled-details
```
