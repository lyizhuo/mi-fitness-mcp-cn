# Docker 部署（含 ARM64）

镜像在 CI 中通过 QEMU + Buildx 构建，同时产出 `linux/amd64` 与 `linux/arm64` 两种架构，
默认推送到 GHCR：`ghcr.io/<owner>/mi-fitness-mcp-cn`。树莓派 4/5、ARM 服务器、ARM NAS 直接拉取 AArch64 镜像即可。

## 快速运行

```bash
docker run -d --name mi-fitness \
  -p 8322:8322 -p 8321:8321 \
  -v mi-fitness-data:/data \
  -e MI_FITNESS_API_KEY="$(openssl rand -hex 32)" \
  -e MI_FITNESS_ADMIN_KEY="$(openssl rand -hex 32)" \
  ghcr.io/lyizhuo/mi-fitness-mcp-cn:latest
```

打开 `http://127.0.0.1:8322/` → 「扫码登录」→ 手机小米账号/米家 App 确认，即可在容器内换取 Key 并同步数据。

容器默认命令是 `all`：同一进程组内启动 FastAPI（8321）与 Flask 仪表盘（8322），前端通过
`http://127.0.0.1:8321` 访问同一容器内的后端。任一端退出容器即退出；`docker stop` 会优雅关闭两者。

## 单服务模式

入口脚本把参数直接交给 `mi-fitness-mcp`，`api`/`web`/`webui` 在未显式传 `--host` 时自动绑定 `0.0.0.0`：

```bash
docker run --rm -it -p 8321:8321 -v mi-fitness-data:/data image api
docker run --rm -it -p 8322:8322 -v mi-fitness-data:/data image web --backend-url http://127.0.0.1:8321
docker run --rm -i -v mi-fitness-data:/data image serve          # MCP stdio，供客户端 docker exec/attach
docker run --rm -v mi-fitness-data:/data image sync --type sleep  # 一次性同步
docker run --rm -v mi-fitness-data:/data image doctor            # 诊断
```

调试时也可执行任意命令（不会被解释为子命令时）：

```bash
docker run --rm image bash
docker run --rm image python -c 'import mi_fitness_mcp; print("ok")'
```

## 数据与凭据

| 容器路径 | 内容 | 来源 |
|---|---|---|
| `/data/share/mi-fitness-mcp/mi_fitness.db` | SQLite 健康数据、API Key 表 | `XDG_DATA_HOME=/data/share` |
| `/data/config/mi-fitness-mcp/config.json` | 区域、路径、同步参数 | `XDG_CONFIG_HOME=/data/config` |
| `/data/state/mi-fitness-mcp/` | 运行日志 | `XDG_STATE_HOME=/data/state` |
| `/data/share/python_keyring/keyring_pass.cfg` | 小米凭据（keyrings.alt 文件后端，base64 混淆，等同明文） | `PYTHON_KEYRING_BACKEND` |

容器内没有 Secret Service，镜像内置 `keyrings.alt` 并把后端固定为 `keyrings.alt.file.PlaintextKeyring`，
这样 `setup --user-id ... --pass-token ...` 与 `sync` 在容器里可用。**凭据只应存在于挂载卷内**，
请限制卷与宿主机的访问权限；不想落盘明文时改用 Web 仪表盘的扫码登录（Key 的 passToken 仍会回退到数据库列）。

挂载宿主目录时注意镜像以 UID 10001 运行：

```bash
mkdir -p ./mi-fitness-data && sudo chown -R 10001:10001 ./mi-fitness-data
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `MI_FITNESS_API_KEY` | 空 | 设置后所有数据接口要求 `X-API-Key`；容器暴露到局域网时务必设置 |
| `MI_FITNESS_ADMIN_KEY` | 空 | 管理端点（发放/吊销 Key、扫码登录）的 `X-Admin-Key`；未设置时仅本机来源可调用 |
| `MI_FITNESS_ALLOWED_HOSTS` | `*`（入口脚本设置） | Host 头白名单，逗号分隔。容器内无法预知客户端域名，故默认放行；需要防 DNS 重绑定请显式收窄 |
| `MI_FITNESS_CORS_ORIGINS` | 本机来源 | 浏览器跨域白名单 |
| `MI_FITNESS_API_URL` | `http://127.0.0.1:8321` | `web` 的代理后端地址 |
| `MI_FITNESS_API_PORT` | `8321` | `all` 模式下 API 端口（容器内） |
| `MI_FITNESS_WEB_PORT` | `8322` | `all` 模式下仪表盘端口（容器内） |

也可以直接给 `api`/`web` 传 `--port`/`--host`/`--backend-url`。

## 本地构建 ARM64 镜像

在 x86 机器上交叉构建：

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64   # 首次
docker buildx build --platform linux/arm64 -t mi-fitness-mcp-cn:arm64 --load .
docker run --rm --platform linux/arm64 mi-fitness-mcp-cn:arm64 --help
```

在 ARM64 设备上直接 `docker build -t mi-fitness-mcp-cn .` 即可，无需 QEMU。

## CI

`.github/workflows/docker.yml`：

1. `build`：Buildx 构建 `linux/amd64,linux/arm64`，push/PR 均构建；非 PR 事件推送到 GHCR，标签策略
   `latest`（默认分支）、分支名、`v*` 语义化版本、`sha-<短哈希>`；GHCR 层缓存（`type=gha`）。
2. `smoke-arm64`：拉取 arm64 镜像，断言 `uname -m` 为 `aarch64`，验证 CLI 与依赖导入，
   再以默认 `all` 模式启动容器，检查 8321 的 API 根路径与 8322 的仪表盘代理健康。

镜像包默认为**私有**，要匿名拉取需在 GitHub 仓库 → Packages → 该镜像 → Package settings 中改为 Public。
