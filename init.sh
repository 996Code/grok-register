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

# ── 2. 配置代理（mihomo 订阅链接）──
echo "── 代理配置 ──"
echo "注册机需要代理才能访问 grok.com。"
echo "如果你有自己的代理（clash/v2ray/mihomo），请提供订阅链接。"
echo ""

MIHOMO_CONFIG="$SCRIPT_DIR/mihomo/config.yaml"
CURRENT_URL=$(grep 'url: "' "$MIHOMO_CONFIG" 2>/dev/null | head -1 | sed 's/.*url: "//;s/"//')

read -rp "请输入你的 Clash 订阅链接（直接回车跳过，使用宿主机已有代理）: " SUB_URL

if [ -n "$SUB_URL" ]; then
    sed -i.bak "s|url: \".*\"|url: \"$SUB_URL\"|" "$MIHOMO_CONFIG" 2>/dev/null || \
    sed -i '' "s|url: \".*\"|url: \"$SUB_URL\"|" "$MIHOMO_CONFIG"
    rm -f "$MIHOMO_CONFIG.bak"
    echo "✅ 订阅链接已写入 mihomo/config.yaml"
else
    echo "ℹ️  跳过代理配置，请确保宿主机已有代理运行在 127.0.0.1:7897"
fi
echo ""

# ── 3. 生成 grok2api 密钥 ──
echo "── 生成 grok2api 密钥 ──"
GROK2API_CONFIG="$SCRIPT_DIR/grok2api/config.yaml"

if grep -q "<SECRET_" "$GROK2API_CONFIG" 2>/dev/null; then
    JWT_SECRET=$(openssl rand -hex 32)
    CRED_KEY=$(openssl rand 32 | base64)
    ADMIN_PASS=$(openssl rand -base64 12 | tr -d '/+=')

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
    echo "   管理后台密码：$ADMIN_PASS"
else
    echo "ℹ️  grok2api/config.yaml 已包含密钥，跳过生成"
fi
echo ""

# ── 4. 创建 config.json ──
echo "── 创建注册机配置 ──"
CONFIG_JSON="$SCRIPT_DIR/config.json"

if [ ! -f "$CONFIG_JSON" ]; then
    if [ -f "$SCRIPT_DIR/config.example.json" ]; then
        cp "$SCRIPT_DIR/config.example.json" "$CONFIG_JSON"

        # 写入 grok2api 管理员密码（与上面生成的一致）
        if [ -n "$ADMIN_PASS" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|\"grok2api_remote_admin_password\": \"\"|\"grok2api_remote_admin_password\": \"$ADMIN_PASS\"|" "$CONFIG_JSON"
            else
                sed -i "s|\"grok2api_remote_admin_password\": \"\"|\"grok2api_remote_admin_password\": \"$ADMIN_PASS\"|" "$CONFIG_JSON"
            fi
        fi
        echo "✅ config.json 已从模板创建"
        echo "   请编辑 config.json 填写邮箱服务配置"
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
