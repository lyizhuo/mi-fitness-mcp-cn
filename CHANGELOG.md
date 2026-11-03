# Changelog

## 未发布

- Docker 镜像：`python:3.12-slim` 基础，默认 `all` 模式在同一容器启动 FastAPI 与 Web 仪表盘；数据、配置、日志与凭据统一落在 `/data` 卷（XDG 目录重定向）
- CI 新增 `.github/workflows/docker.yml`：QEMU + Buildx 构建 `linux/amd64`/`linux/arm64` 并推送 GHCR，arm64 任务在 QEMU 下冒烟验证架构、CLI、依赖导入与 `all` 模式端到端
- 镜像内置 `keyrings.alt` 文件后端，容器内无 Secret Service 时 `setup`/`sync` 可用（凭据以明文等同形式存于挂载卷）
- 修复 Web 仪表盘渲染：API 统一返回 `{status,count,data}`，前端此前按裸数组与旧字段名（`distance`/`active_calories`/`spo2_value`/`stress_value`）渲染，且睡眠未聚合 `stages`，导致有数据仍显示空；现统一解包并按 `distance_m`/`active_kcal`/`spo2_pct`/`stress_score` 展示，Key 表改用 `key_masked`

## 0.2.2（零第三方请求）

- 移除 Web 仪表盘与测试页的 Google Fonts 外链：打开页面不再向 Google 发送任何请求（此前浏览器会上传 IP/UA），改用系统字体栈，国内加载也更快、离线可渲染
- 发往小米的请求覆盖默认 `python-httpx/*` User-Agent 为浏览器 UA，去除脚本指纹（与 Cookie 登录来源一致）
- `docs/PRIVACY.md` 补充浏览器端零外链与最小化出站请求头说明

## 0.2.1（隐私加固）

- 数据安全审计文档 `docs/PRIVACY.md`：全部对外请求清单（仅小米域名）、本机数据存放表、威胁模型与自验方法
- CORS 收紧：默认仅允许本机来源（原来为 `*`，恶意网页可跨站读取本地健康数据）；可用 `MI_FITNESS_CORS_ORIGINS` 覆盖
- Host 头白名单中间件（FastAPI + Flask 双侧）：阻断 DNS 重绑定攻击；非回环绑定时 CLI 自动放行绑定地址，可用 `MI_FITNESS_ALLOWED_HOSTS` 覆盖
- API Key 的 passToken 迁出 SQLite 明文，改存系统 keyring（启动时自动迁移历史数据）；吊销时同步清理
- `api` 命令默认关闭 uvicorn 访问日志（查询参数不再落入终端）
- 新增 `GET /api/export`：本地数据导出为 JSON/CSV（含 Excel BOM），纯离线操作

## 0.2.0

- 内置 Web 仪表盘（`mi-fitness-mcp web`，Flask）：可视化测试全部 API 端点、Key 管理、扫码登录，内置反向代理（自动附加 X-API-Key/X-Admin-Key，上游耗时透传）
- REST API 服务（`mi-fitness-mcp api`，FastAPI）：全部数据端点 + 同步（前台/后台）+ 覆盖统计，交互式文档 `/docs`
- API Key 体系：`POST /api/auth/keys` 用小米凭据换取 `mif_sk_*` Key（类大模型平台风格），支持多账号上下文、last_used 统计、按前缀吊销；静态 Key 经 `MI_FITNESS_API_KEY`、管理端点经 `MI_FITNESS_ADMIN_KEY`
- 扫码登录：逆向小米通用扫码流程（`sid=xiaomiio`），`/api/auth/qr/start|poll` 生成二维码并轮询换取凭据后自动发放 Key，无需浏览器 F12
- Rust 测试页 `testpage/`（可选，内置 Web 仪表盘的 Rust 替代实现）
- 修复：`mcp` 依赖加上界 `<2`（MCP SDK 2.x 移除 `Server.list_tools` 导致启动崩溃）
- 文档：隐私与数据安全审计 `docs/PRIVACY.md`

## 0.1.0

- initial standalone `mi-fitness-mcp` repository
- Xiaomi auth via `userId + passToken`
- Mi Fitness cloud sync for steps, heart rate, calories, body measurements
- MCP tools for sync, summaries, heart rate, body measurements, coverage
