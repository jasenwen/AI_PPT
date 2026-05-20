# LibreChat + PPT Engine 本地部署指南

> [!NOTE]
> **开源声明与版权告示（Open Source License Notice）**
> 本项目系统（位于 `main` 目录下）深度定制并集成自开源项目 **[LibreChat](https://github.com/danny-avila/LibreChat)**（使用 **MIT 协议** 授权，Copyright (c) 2026 LibreChat）。
> 根据 MIT 开源协议之规定，特此声明：
> 1. 我们在开发本系统的衍生部分时，完全保留并继承了 LibreChat 原作者的版权声明及许可条款。
> 2. 本项目中专属开发的 PPT-Engine 引擎及其核心转换/生成逻辑（位于 `ppt-engine` 目录下）属于独立扩展组件。

## 前置条件

| 组件 | 要求 |
|------|------|
| Node.js | v18+ (推荐 v20 LTS) |
| npm | v9+ |
| Docker Desktop | 需要运行 (用于 MongoDB) |
| Python | 3.11+ + uv |

---

## Step 1: 启动 Docker Desktop

手动启动 Docker Desktop 应用程序。等待 Docker 引擎就绪（任务栏图标变绿）。

---

## Step 2: 启动 MongoDB

```powershell
docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:7
```

验证：
```powershell
docker ps  # 应看到 mongodb 容器运行中
```

---

## Step 3: 配置 LibreChat

### 3a. 确认 `.env`

```powershell
cd d:\AI\Projects\genText\AI-Office-Mate\main
```

在 `.env` 中确认以下关键配置：

```env
# MongoDB (本地 Docker)
MONGO_URI=mongodb://127.0.0.1:27017/LibreChat

# 允许不验证邮箱登录
ALLOW_UNVERIFIED_EMAIL_LOGIN=true
ALLOW_REGISTRATION=true
```

### 3b. 确认 `librechat.yaml` (MCP 配置)

当前 [librechat.yaml](file:///d:/AI/Projects/genText/AI-Office-Mate/main/librechat.yaml) 已正确配置：

```yaml
version: 1.2.2

mcpSettings:
  allowedAddresses:
    - '127.0.0.1:8100'
    - 'localhost:8100'

mcpServers:
  ppt-engine:
    url: http://localhost:8100/mcp/sse
    timeout: 300000  # 5分钟超时
```

### 3c. 安装依赖

```powershell
cd d:\AI\Projects\genText\AI-Office-Mate\main
npm install
```

> [!NOTE]
> 首次安装可能需要 5-10 分钟，项目依赖较多。
> 安装完成后的 vulnerability 警告可以忽略，不影响运行。

---

## Step 4: 启动 PPT Engine

```powershell
cd d:\AI\Projects\genText\AI-Office-Mate\ppt-engine

# 确保虚拟环境和依赖已安装
uv pip install -r requirements.txt

# 启动 PPT Engine（开发模式，带热重载）
uv run python -m app.main
```

验证：
```powershell
curl http://localhost:8100/health
# 应返回 {"status": "ok", "service": "ppt-engine"}
```

---

## Step 5: 启动 LibreChat 后端

> [!WARNING]
> LibreChat **没有** `npm run dev` 脚本！后端和前端需要**分别启动**。

**打开新终端**，运行：

```powershell
cd d:\AI\Projects\genText\AI-Office-Mate\main

# 安装依赖（如果还没装过）
npm install

# 启动后端开发服务器
npm run backend:dev
```

验证日志中出现：
```
info: Server listening at http://localhost:3080
info: [MCP] Initialized with 1 configured server and 5 tools.
```

> [!NOTE]
> `backend:dev` 使用 nodemon，修改后端代码会自动重启。
> MCP 连接 PPT Engine 时如果看到 `oauth-protected-resource` 404 是正常的。

---

## Step 6: 启动 LibreChat 前端

**打开新终端**，运行：

```powershell
cd d:\AI\Projects\genText\AI-Office-Mate\main

# 先构建包依赖
npm run build:packages

# 启动前端开发服务器
npm run frontend:dev
```

前端启动后会显示：
```
VITE v7.x.x  ready in xxx ms
➜  Local:   http://localhost:3090/
```

> [!IMPORTANT]
> 前端开发服务器运行在 **:3090**，会自动代理 API 请求到后端 **:3080**。
> 访问 `http://localhost:3090/` 即可使用。

---

## Step 7: 创建 PPT 助手 Agent

1. 访问 http://localhost:3090/
2. 首次使用需注册一个账号
3. 在设置中输入 LLM API Key（OpenAI / Anthropic / Google 等）
4. 点击左侧的 **"Agents"** 按钮
5. 点击 **"+ Create Agent"**
6. 配置：
   - **Name**: `PPT 助手`
   - **Model Provider**: 选择支持 tool_use 的模型（如 GPT-4o、Claude Sonnet）
   - **System Prompt**: 粘贴 `ppt-engine/app/prompts/agent_system.md` 的内容
   - **Tools**: 启用 `ppt-engine` MCP 工具组（5个工具）
7. 保存

---

## 启动顺序总结

需要 **4 个终端**，按以下顺序启动：

```
1. Docker Desktop       →  等待就绪
2. MongoDB              →  docker run -d --name mongodb -p 27017:27017 ... mongo:7
3. PPT Engine (终端 1)  →  cd ppt-engine && uv run python -m app.main
4. LibreChat 后端 (终端 2) →  cd main && npm run backend:dev
5. LibreChat 前端 (终端 3) →  cd main && npm run build:packages && npm run frontend:dev
6. 浏览器               →  http://localhost:3090
```

| 服务 | 端口 | 脚本命令 |
|------|------|----------|
| MongoDB | :27017 | `docker run ...` |
| PPT Engine | :8100 | `uv run python -m app.main` |
| LibreChat 后端 | :3080 | `npm run backend:dev` |
| LibreChat 前端 | :3090 | `npm run frontend:dev` |

---

## 常见问题

### Q: `npm run dev` 报错 `Missing script: "dev"`
A: LibreChat 没有 `dev` 脚本。正确命令是分别启动：
- 后端: `npm run backend:dev`
- 前端: `npm run frontend:dev`（首次需先 `npm run build:packages`）

### Q: MCP 连接报 500 / TypeError: handle_sse() missing arguments
A: MCP SDK v1.11+ 的 `connect_sse` 是原生 ASGI handler，需要用 `_RawAsgi` 包装器挂载。
   参见 [server.py](file:///d:/AI/Projects/genText/AI-Office-Mate/ppt-engine/app/mcp/server.py) 中的 `create_mcp_routes()`。

### Q: MCP 连接报 307 Temporary Redirect 循环
A: 不要用 `Mount(app=...)`，应使用 `Route(endpoint=_RawAsgi(...))` 避免尾斜杠重定向。

### Q: PPT Engine 启动报 MongoDB 连接失败
A: 确保 Docker 中的 MongoDB 正在运行：`docker ps`

### Q: Agent 看不到 PPT 工具
A: 检查：
1. PPT Engine 已启动且 `curl http://localhost:8100/health` 返回 ok
2. `librechat.yaml` 中 `mcpServers.ppt-engine.url` = `http://localhost:8100/mcp/sse`
3. 重启 LibreChat 后端以重新加载配置

### Q: LLM 调用失败 (qwen3.6-flash)
A: 在 PPT Engine `.env` 中确认 `LITELLM_API_KEY` 有效，且模型名正确
