#!/bin/bash
set -e

echo "========================================="
echo "  Grok Register - Docker Container"
echo "========================================="

# 启动 Xvfb 虚拟显示器
echo "[*] 启动 Xvfb 虚拟显示器 :99 ..."
Xvfb :99 -screen 0 1280x900x24 -nolisten tcp &
XVFB_PID=$!

# 等待 Xvfb 启动
sleep 1

# 验证 Xvfb 是否运行
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "[!] Xvfb 启动失败，尝试降级分辨率..."
    Xvfb :99 -screen 0 1024x768x16 -nolisten tcp &
    XVFB_PID=$!
    sleep 1
fi

if kill -0 $XVFB_PID 2>/dev/null; then
    echo "[*] Xvfb 已启动 (PID: $XVFB_PID)"
else
    echo "[!] Xvfb 启动失败，将尝试直接运行（可能影响 Turnstile）"
fi

export DISPLAY=:99

# 检测 Chromium
echo "[*] 检测 Chromium 路径..."
for cmd in chromium chromium-browser google-chrome google-chrome-stable; do
    if which $cmd 2>/dev/null; then
        echo "[*] 找到浏览器: $(which $cmd)"
        break
    fi
done

# 检测代理连通性
if [ -n "$PROXY_HOST" ] && [ -n "$PROXY_PORT" ]; then
    echo "[*] 检测代理 $PROXY_HOST:$PROXY_PORT ..."
    if curl -s --connect-timeout 5 -x http://$PROXY_HOST:$PROXY_PORT https://www.google.com > /dev/null 2>&1; then
        echo "[*] HTTP 代理可用"
    elif curl -s --connect-timeout 5 -x socks5://$PROXY_HOST:$PROXY_PORT https://www.google.com > /dev/null 2>&1; then
        echo "[*] SOCKS5 代理可用，更新 config.json"
        if [ -f /app/config.json ]; then
            sed -i "s|http://.*:7897|socks5://$PROXY_HOST:$PROXY_PORT|g" /app/config.json
        fi
    else
        echo "[!] 代理连通性测试失败，将尝试直连"
    fi
fi

# 显示配置
echo "[*] 当前配置:"
if [ -f /app/config.json ]; then
    echo "  邮箱服务商: $(python3 -c "import json; c=json.load(open('/app/config.json')); print(c.get('email_provider','unknown'))")"
    echo "  注册数量: $(python3 -c "import json; c=json.load(open('/app/config.json')); print(c.get('register_count',1))")"
    echo "  代理: $(python3 -c "import json; c=json.load(open('/app/config.json')); p=c.get('proxy',''); print(p if p else '直连')")"
fi

echo "========================================="
echo "[*] 启动注册机..."
echo "========================================="

# 运行注册机
cd /app
python3 grok_register_ttk.py cli --auto-start

# 捕获退出码
EXIT_CODE=$?

# 清理
echo "[*] 清理中..."
kill $XVFB_PID 2>/dev/null || true

echo "[*] 退出码: $EXIT_CODE"
exit $EXIT_CODE
