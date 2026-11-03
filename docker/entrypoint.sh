#!/usr/bin/env bash
# 容器入口：
#   all（默认） 同一容器内启动 FastAPI + Flask 仪表盘
#   api|web|webui|serve|sync|setup|doctor  交给 mi-fitness-mcp（容器内自动绑定 0.0.0.0）
#   --help|-h|--version                     交给 mi-fitness-mcp
#   其他命令（bash、python、uname ...）     直接执行，便于调试
set -euo pipefail

API_PORT="${MI_FITNESS_API_PORT:-8321}"
WEB_PORT="${MI_FITNESS_WEB_PORT:-8322}"

# 绑定 0.0.0.0 后真实客户端域名无法预知，默认放行 Host 头；
# 需要防 DNS 重绑定请显式设置 MI_FITNESS_ALLOWED_HOSTS（逗号分隔）。
: "${MI_FITNESS_ALLOWED_HOSTS:=*}"
export MI_FITNESS_ALLOWED_HOSTS

if [ -z "${MI_FITNESS_API_KEY:-}" ]; then
    echo "⚠️  未设置 MI_FITNESS_API_KEY：API 依赖默认凭据/发放的 Key，且管理端点仅限本机来源或 X-Admin-Key。" >&2
fi

has_host_flag() {
    for arg in "$@"; do
        case "$arg" in
            --host|--host=*) return 0 ;;
        esac
    done
    return 1
}

wait_for_api() {
    python - "$API_PORT" <<'PY'
import sys
import time
import urllib.request

port = sys.argv[1]
deadline = time.time() + 15
while time.time() < deadline:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5).read()
        sys.exit(0)
    except Exception:
        time.sleep(0.3)
sys.exit(1)
PY
}

run_all() {
    mi-fitness-mcp api --host 0.0.0.0 --port "$API_PORT" &
    api_pid=$!
    wait_for_api || echo "⚠️  API 启动超时，仍尝试启动仪表盘" >&2

    mi-fitness-mcp web --host 0.0.0.0 --port "$WEB_PORT" \
        --backend-url "http://127.0.0.1:$API_PORT" &
    web_pid=$!

    stopping=0
    on_signal() {
        stopping=1
        kill -TERM "$api_pid" "$web_pid" 2>/dev/null || true
    }
    trap on_signal TERM INT
    status=0
    # 任一进程退出即整体退出，避免容器半死
    wait -n "$api_pid" "$web_pid" || status=$?
    kill -TERM "$api_pid" "$web_pid" 2>/dev/null || true
    wait 2>/dev/null || true
    # docker stop / Ctrl+C 视为正常退出，异常退出保留真实状态码
    [ "$stopping" -eq 1 ] && exit 0
    exit "$status"
}

case "${1:-all}" in
    all)
        if [ "$#" -gt 1 ]; then
            echo "❌ all 模式不接受额外参数：$*" >&2
            exit 64
        fi
        run_all
        ;;
    api|web|webui)
        if has_host_flag "$@"; then
            exec mi-fitness-mcp "$@"
        else
            exec mi-fitness-mcp "$@" --host 0.0.0.0
        fi
        ;;
    serve|sync|setup|doctor|-h|--help|--version)
        exec mi-fitness-mcp "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
