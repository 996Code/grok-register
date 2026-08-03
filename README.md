<div align="center">

[![Grok Register — GUI and CLI registration automation toolkit](assets/banner.png)](https://github.com/AaronL725/grok-register)

Grok Register 是一个面向自动化流程研究、测试环境验证和个人学习的 Python 工具。项目提供 GUI / CLI、四种临时邮箱接入、Chromium 页面自动化、账号安全落盘、pending 恢复、grok2api token 入池，可选 CPA xAI OIDC 凭证导出，以及 Web 控制台和 Docker 一键部署。

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Interface-GUI%20%2B%20CLI-success.svg" alt="GUI + CLI">
  <img src="https://img.shields.io/badge/Docker-一键部署-2496ED.svg" alt="Docker">
  <a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

</div>

---

> [!IMPORTANT]
> 本项目仅用于自动化流程研究、测试环境验证和个人学习。使用者应自行遵守目标网站服务条款、当地法律法规和第三方服务限制。请勿将本项目用于滥用、绕过平台限制或未经授权的商业用途。

## 目录

- [Docker 一键部署（推荐）](#docker-一键部署推荐)
- [Web 控制台](#web-控制台)
- [当前功能](#当前功能)
- [配置](#配置)
- [常见问题](#常见问题)
- [License](#license)

## Docker 一键部署（推荐）

四个服务通过 docker-compose 统一编排，所有数据持久化到本地目录。

### 架构

```
┌─────────────────────────────────────────────────────┐
│  docker-compose (bridge 网络 grok-net)               │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │ mihomo   │   │ grok2api │   │ web 控制台        │ │
│  │ :7897    │   │ :8000    │   │ :8088            │ │
│  │ (代理)   │◄──│ (API网关) │◄──│ (注册+管理)      │ │
│  └────┬─────┘   └────┬─────┘   └──────────────────┘ │
│       │              │                                │
└───────┼──────────────┼────────────────────────────────┘
        │              │
        ▼              ▼
   ┌──────────┐  ┌───────────┐
   │ grok.com │  │ x.ai API  │
   └──────────┘  └───────────┘
```

### 数据持久化

所有数据在本地目录，容器重建不丢失：

```
grok-register/
├── data/
│   ├── grok2api/    ← grok2api 数据库 (backend.db)
│   ├── web/         ← Web 控制台配置 (config.json)
│   └── mihomo/      ← 代理订阅缓存
├── output/          ← 注册产物 (accounts_*.txt)
├── .env             ← 环境变量（订阅链接、密码）
├── mihomo/config.yaml
└── grok2api/config.yaml
```

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/996Code/grok-register.git
cd grok-register

# 2. 创建 .env 文件
cat > .env << 'EOF'
SUB_URL=https://your-subscription-url/clashx/xxxxx
GROK2API_ADMIN_PASS=Njmd@618
EOF

# 3. 初始化（生成密钥、创建配置）
./init.sh

# 4. 启动所有服务
docker compose up -d
```

### 各服务说明

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| **web** | 8088 | Web 控制台（注册管理 + API 状态 + 配置） |
| **grok2api** | 8000 | API 网关（OpenAI 兼容），管理后台 http://localhost:8000 |
| **mihomo** | 内部 7897 | 代理服务（仅容器网络可访问） |

### 环境变量 (.env)

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `SUB_URL` | 是 | — | Clash 订阅链接 |
| `GROK2API_ADMIN_PASS` | 否 | `Njmd@618` | grok2api 管理员密码 |
| `GROK2API_ADMIN_USER` | 否 | `admin` | grok2api 管理员用户名 |

### 首次部署后的配置（重要）

启动后需要配置 grok2api 的出口代理，否则 API 无法访问 grok.com：

1. **方式一（推荐）**：打开 Web 控制台 http://localhost:8088 → 账号管理 → 系统会自动配置
2. **方式二**：手动配置
   - 打开 http://localhost:8000，用 admin / `Njmd@618` 登录
   - **Settings → Egress Nodes** → 为 4 个 scope 各添加节点，代理 URL 填 `http://grok-mihomo:7897`
   - **Settings → Provider Web → Clearance Mode** 设为 `manual`
   - **Settings → Egress Operations → Auto Assign** 开启

### 代理配置 (mihomo)

mihomo 配置文件在 `mihomo/config.yaml`，默认使用美国节点（grok.com 对部分国家 IP 有风控）。

```yaml
proxy-providers:
  my-sub:
    url: "你的订阅链接"      # 或在 .env 中设置 SUB_URL
    filter: "美国-US-[0-9]"  # 只用美国节点
    exclude-filter: "(?i)有效期|剩余|GB|V6"
```

如需切换其他地区，修改 `filter` 正则即可。

### 本地构建镜像

Web 控制台镜像需要先构建 base（含 Chrome + Xvfb）：

```bash
# 1. 构建基础镜像（约 1.5GB）
docker build -t grok-register-base:latest -f Dockerfile.base .
# 中国机器可加代理加速 Chrome 下载：
# docker build -f Dockerfile.base --build-arg BUILD_PROXY=http://127.0.0.1:7897 -t grok-register-base:latest .

# 2. 构建应用镜像
docker build -f Dockerfile -t grok-register:latest .

# 3. 构建 Web 控制台镜像
docker compose build web
```

## Web 控制台

访问地址：`http://服务器IP:8088`

### 功能

| 页面 | 功能 |
| --- | --- |
| **总览控制台** | 批量注册控制（总数/每批次/间隔）、实时日志、统计面板、进度条 |
| **账号管理** | 在线账号池（配额进度条）、批量刷新配额、API Key 管理、待恢复文件 |
| **Grok2API** | API 访问信息、Key 创建/删除、出口代理节点状态、连接测试、创意控制台入口 |
| **系统配置** | 邮箱服务/注册参数/入池配置/CPA 导出，所有参数可视化编辑 |

### 批量注册

控制台支持批量注册 + 批次间隔：

- **总数量**：总共注册多少个账号
- **每批次**：每批注册多少个（默认 100）
- **批次间隔(秒)**：批次之间的等待时间

注册完成后自动分配代理节点 + 刷新配额，无需手动操作。

## 当前功能

- 使用真实 Chromium / Chrome 页面完成注册、验证码、资料填写、Turnstile 与 SSO cookie 获取。
- 支持四种邮箱服务：DuckMail、YYDS、Cloudflare 临时邮箱、Cloud Mail 无人收件模式。
- 成功账号实时写入 `accounts_*.txt`，支持 pending 恢复。
- 支持将 SSO token 自动写入 grok2api 远端池。
- 支持注册成功后可选导出 CLIProxyAPI 使用的 CPA xAI OIDC 凭证。
- Web 控制台：注册控制 + 账号管理 + API 状态 + 配置编辑。
- Docker 一键部署：mihomo 代理 + grok2api API 网关 + Web 控制台。

## 配置

配置文件为 `data/web/config.json`（Web 控制台模式）或项目根目录 `config.json`（CLI 模式）。

完整配置说明参考 `config.example.json` 和源项目 [README](https://github.com/AaronL725/grok-register)。

### grok2api 配置

grok2api 的配置文件在 `grok2api/config.yaml`，密钥由 `init.sh` 自动生成。

**管理员密码**通过 `.env` 的 `GROK2API_ADMIN_PASS` 配置，默认 `Njmd@618`。

**重要**：如果重建 grok2api 容器（`docker compose down -v`），数据库会清空，需要重新导入 SSO token 和配置出口代理。使用 `docker compose restart` 则不会丢失数据。

## 常见问题

### API 调用返回 "上游服务暂不可用"

grok.com 免费账号偶尔不稳定（statsig 刷新中），重试即可。如果持续失败：
1. 检查代理节点是否 healthy（Web 控制台 → Grok2API 页面）
2. 刷新配额（Web 控制台 → 账号管理 → 全部刷新配额）
3. 确认 Clearance Mode 设为 `manual`

### 只有 2 个模型可用

免费账号（basic tier）只能用 `grok-chat-fast`（对话）和 `grok-imagine-image`（生图）。其他模型需要 SuperGrok 订阅。

### 注册后账号没出现在账号池

注册完成会自动分配代理 + 刷新配额。如果没出现：
1. 检查 Web 控制台日志是否有入池失败
2. 手动在账号管理页面点「全部刷新配额」
3. 检查 config.json 中 `grok2api_remote_base` 是否为 `http://grok2api:8000`

### 上下文窗口多大

免费账号：128K tokens（约 10 万字中文）。付费 SuperGrok：2M tokens。

### creative-console 报 "读取密钥失败"

这是 grok2api 的加密密钥变更导致旧数据无法解密。解决方法：
1. 删除旧的 API Key
2. 重新创建新的 API Key
3. 新 Key 会用当前密钥加密，可以正常读取

## License

[MIT](LICENSE).

## Acknowledgments

- [AaronL725/grok-register](https://github.com/AaronL725/grok-register) — 原项目
- [chenyme/grok2api](https://github.com/chenyme/grok2api) — Grok API 网关
- [router-for-me/CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) — CLI 代理 API
- [linux.do](https://linux.do) — 技术社区
