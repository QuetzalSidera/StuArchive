# 镜像与国内访问

GitHub Raw 在国内网络下可能出现超时。StuArchive 推荐把仓库同步到多个镜像仓库，并优先通过 Pages 形式访问静态 JSON。

## 当前镜像

当前已配置 GitCode 镜像仓库：

```text
git@gitcode.com:Eternal_hearted/StuArchive.git
```

GitCode Raw API base：

```text
https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data
```

常用入口：

```text
https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data/index.json
https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data/students/lookup.json
https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/docs/openapi.json
```

2026-06-03 本地抽测结果：

- 上述三个入口均返回 `200 OK`。
- 响应 `Content-Type` 为 `application/octet-stream;charset=UTF-8`，不是 `application/json`。
- 带 `Origin` 请求时会返回 `Access-Control-Allow-Origin`，可用于浏览器端 `fetch`；如调用方强依赖 JSON MIME，优先使用 Pages 镜像或服务端代理。

本地手动推送：

```bash
git push gitcode main
```

注意：本地的 `gitcode` remote 只对当前机器生效。GitHub Actions 自动推送镜像时，仍需要配置 `MIRROR_PUSH_URLS` secret，或在 Actions 中单独配置可用的 SSH deploy key。

## 推荐顺序

1. 极狐GitLab / JihuLab Pages

   推荐作为国内主镜像。Pages 可以直接从代码仓发布静态网站，适合把 `data/` 暴露为静态 JSON API。

   访问形式：

   ```text
   https://<namespace>.jihulab.io/<project>/data/index.json
   https://<namespace>.jihulab.io/<project>/data/students/lookup.json
   https://<namespace>.jihulab.io/<project>/docs/openapi.json
   ```

   GitLab 兼容 raw API 也可作为备选：

   ```text
   https://jihulab.com/api/v4/projects/<url-encoded-namespace%2Fproject>/repository/files/data%2Findex.json/raw?ref=main
   ```

2. GitCode Raw API

   GitCode 提供仓库 raw 文件 API，可作为第二镜像或程序端 fallback。

   访问形式：

   ```text
   https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data/index.json
   https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data/students/lookup.json
   ```

3. Gitee

   Gitee 可以作为代码镜像仓库，但不建议作为本项目新的静态 API 主入口。Gitee Pages 相关功能当前不适合作为稳定新方案；如仅使用仓库 raw 链接，需要先实测公开访问、CORS、MIME 与限流。

## 配置 GitHub 自动推送镜像

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions -> New repository secret` 中添加：

```text
MIRROR_PUSH_URLS
```

内容为一个或多个可 push 的 Git 远端 URL，每行一个：

```text
https://oauth2:<jihulab-token>@jihulab.com/<namespace>/<project>.git
https://<gitcode-username>:<gitcode-token>@gitcode.com/<owner>/<repo>.git
```

推送逻辑在 `.github/workflows/mirror.yml` 中，触发条件：

- `main` 分支有新提交时自动同步到镜像仓库。
- 也可以手动运行 `Mirror Repositories` workflow。

## 配置 Pages

本仓库已包含 `.gitlab-ci.yml`。当仓库镜像到极狐GitLab / GitLab 兼容平台后，CI 会把以下目录发布到 Pages：

```text
public/data
public/docs
```

因此 Pages API base 为：

```text
https://<namespace>.jihulab.io/<project>/data
```

OpenAPI 文档也可以通过 Pages 访问：

```text
https://<namespace>.jihulab.io/<project>/docs/openapi.json
```

注意：`docs/openapi.json` 中的默认 server 仍是 GitHub Raw。导入 Apifox 后，如果要走镜像，需要把服务地址改为对应 Pages base。

## 客户端 fallback 示例

```js
const bases = [
  "https://<namespace>.jihulab.io/<project>/data",
  "https://api.gitcode.com/api/v5/repos/Eternal_hearted/StuArchive/raw/data",
  "https://raw.githubusercontent.com/QuetzalSidera/StuArchive/main/data"
];

async function fetchJson(path, timeoutMs = 5000) {
  for (const base of bases) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${base}/${path.replace(/^\/+/, "")}`, {
        signal: controller.signal
      });
      if (res.ok) return await res.json();
    } catch {
      // Try next mirror.
    } finally {
      clearTimeout(timer);
    }
  }
  throw new Error(`All API mirrors failed: ${path}`);
}

const lookup = await fetchJson("students/lookup.json");
```

## 选择原则

- 面向浏览器和普通用户：优先 Pages。
- 面向脚本和服务端：Pages 与 raw API 都可用，建议实现多 base fallback。
- 不要把镜像仓库作为新的数据源；所有镜像都应由 GitHub `main` 自动推送，避免多个源头产生分叉。
- 镜像 URL 上线前，用 `data/index.json`、`data/students/lookup.json`、`docs/openapi.json` 三个文件做连通性、CORS 和 MIME 抽样。

## 参考

- 极狐GitLab Pages：`https://gitlab.cn/docs/jh/user/project/pages/_index/`
- GitLab raw file API：`https://docs.gitlab.com/api/repository_files/`
- GitCode raw file API：`https://docs.gitcode.com/en/docs/apis/get-api-v-5-repos-owner-repo-raw-path/`
