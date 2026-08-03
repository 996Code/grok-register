#!/bin/bash
set -e

# ──────────────────────────────────────────────
# grok-register 一键初始化脚本
# ──────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "╔══════════════════════════════════════════╗"
echo "║   Grok Register 一键部署初始化           ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. 检查 Docker ──
if ! command -v docker &>/dev/null; then
    echo "❌ 未检测到 Docker，请先安装 Docker。"
    echo "   安装指南：https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "❌ 未检测到 Docker Compose v2，请先安装。"
    echo "   Ubuntu: sudo apt install docker-compose-v2"
    exit 1
fi
echo "✅ Docker 环境检查通过"
echo ""

# ── 2. 配置代理订阅（写入 .env，不修改配置文件）──
echo "── 代理配置 ──"
echo "注册机和 grok2api 需要代理才能访问 grok.com。"
echo "订阅链接保存在 .env 文件中（已被 gitignore，不会提交）。"
echo ""

ENV_FILE="$SCRIPT_DIR/.env"
read -rp "请输入你的 Clash 订阅链接（直接回车跳过，使用宿主机已有代理）: " SUB_URL

if [ -n "$SUB_URL" ]; then
    echo "SUB_URL=$SUB_URL" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "✅ 订阅链接已写入 .env"
else
    echo "ℹ️  跳过代理配置，请确保宿主机已有代理运行在 127.0.0.1:7897"
fi
echo ""

# ── 3. grok2api 密码 + 密钥 ──
echo "── grok2api 管理员配置 ──"
GROK2API_CONFIG="$SCRIPT_DIR/grok2api/config.yaml"

# 密码：优先从环境变量读取，默认 Njmd@618
ADMIN_PASS="${GROK2API_ADMIN_PASS:-Njmd@618}"

if grep -q "<SECRET_" "$GROK2API_CONFIG" 2>/dev/null || grep -q "<ADMIN_PASSWORD>" "$GROK2API_CONFIG" 2>/dev/null; then
    JWT_SECRET=$(openssl rand -hex 32)
    CRED_KEY=$(openssl rand 32 | base64)

    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|<SECRET_JWT>|$JWT_SECRET|g" "$GROK2API_CONFIG"
        sed -i '' "s|<SECRET_CRED_KEY>|$CRED_KEY|g" "$GROK2API_CONFIG"
        sed -i '' "s|<ADMIN_PASSWORD>|$ADMIN_PASS|g" "$GROK2API_CONFIG"
    else
        sed -i "s|<SECRET_JWT>|$JWT_SECRET|g" "$GROK2API_CONFIG"
        sed -i "s|<SECRET_CRED_KEY>|$CRED_KEY|g" "$GROK2API_CONFIG"
        sed -i "s|<ADMIN_PASSWORD>|$ADMIN_PASS|g" "$GROK2API_CONFIG"
    fi
    echo "✅ 密钥已生成并写入 grok2api/config.yaml"
else
    echo "ℹ️  grok2api/config.yaml 已配置，跳过"
fi
echo "   管理员密码：$ADMIN_PASS"
echo "   可在 .env 文件中通过 GROK2API_ADMIN_PASS 修改"
echo ""

# ── 4. 创建 config.json ──
echo "── 创建注册机配置 ──"
CONFIG_JSON="$SCRIPT_DIR/config.json"

if [ ! -f "$CONFIG_JSON" ]; then
    if [ -f "$SCRIPT_DIR/config.example.json" ]; then
        cp "$SCRIPT_DIR/config.example.json" "$CONFIG_JSON"

        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|\"grok2api_remote_admin_password\": \"\"|\"grok2api_remote_admin_password\": \"$ADMIN_PASS\"|" "$CONFIG_JSON"
        else
            sed -i "s|\"grok2api_remote_admin_password\": \"\"|\"grok2api_remote_admin_password\": \"$ADMIN_PASS\"|" "$CONFIG_JSON"
        fi
        echo "✅ config.json 已从模板创建"
    else
        echo "⚠️  config.example.json 不存在，请手动创建 config.json"
    fi
else
    echo "ℹ️  config.json 已存在，跳过创建"
fi
echo ""

# ── 5. 创建输出目录 ──
mkdir -p "$SCRIPT_DIR/output"
echo "✅ 输出目录已创建: output/"
echo ""

# ── 6. 完成 ──
echo "╔══════════════════════════════════════════╗"
echo "║   ✅ 初始化完成！                        ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "下一步："
echo ""
echo "  1. 启动代理和 API 网关："
echo "     docker compose up -d mihomo grok2api"
echo ""
echo "  2. 访问 grok2api 管理后台配置出口代理："
echo "     http://localhost:8000"
echo "     （在 Settings → Egress Nodes 添加 http://grok-mihomo:7897）"
echo ""
echo "  3. 编辑 config.json 填写邮箱配置后，运行注册："
echo "     docker compose run --rm grok-register"
echo ""
