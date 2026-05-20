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

---

## MCP 修复记录 (2026-05-17)

### 问题
MCP SDK 从 v1.0 升级到 v1.11.0 后，`SseServerTransport.connect_sse()` 和 `handle_post_message()` 仍是原生 ASGI handler `(scope, receive, send)`，但 Starlette 的 `Route(endpoint=func)` 会自动用 `request_response` 包装，只传入 `Request` 对象。

### 修复方案
在 [server.py](file:///d:/AI/Projects/genText/AI-Office-Mate/ppt-engine/app/mcp/server.py) 中使用 callable class wrapper：

```python
class _RawAsgi:
    def __init__(self, handler):
        self._handler = handler
    async def __call__(self, scope, receive, send):
        await self._handler(scope, receive, send)

Route("/mcp/sse", endpoint=_RawAsgi(handle_sse))
```

`inspect.isfunction()` 对 class instance 返回 `False`，Starlette 直接将其作为 ASGI app 调用。

```diff:server.py
"""MCP Server for PPT Engine — SSE transport.

Exposes PPT generation tools to LibreChat Agent via the
Model Context Protocol. Tools registered:

- convert_document: Document → Markdown (MarkItDown)
- list_templates: Browse template library
- get_template_preview: Preview a template's SVG pages
- create_ppt_task: Create a PPT generation task
- get_task_status: Poll task progress
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route

from app.deps import get_markitdown, get_template_service, get_task_worker, get_db

logger = logging.getLogger(__name__)

# Create the MCP server
mcp_server = Server("ppt-engine")


# ------------------------------------------------------------------
# Tool definitions
# ------------------------------------------------------------------

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="convert_document",
            description="将上传的文档(PDF/DOCX/XLSX/PPTX/HTML等)转换为结构化Markdown。"
                        "用于PPT内容预处理。",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（服务端可访问的路径）",
                    },
                    "url": {
                        "type": "string",
                        "description": "要转换的URL（网页/YouTube等）",
                    },
                    "text": {
                        "type": "string",
                        "description": "原始文本内容",
                    },
                },
            },
        ),
        Tool(
            name="list_templates",
            description="列出PPT模板库中所有可用的模板。"
                        "返回每个模板的ID、名称、分类、主色调、页数等摘要信息。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_template_preview",
            description="获取指定模板的详细信息和SVG页面预览。",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "模板ID",
                    },
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="create_ppt_task",
            description="创建一个PPT生成任务。需要提供：已处理的Markdown内容、"
                        "确认后的大纲、选择的模板ID、设计规范。任务创建后将自动"
                        "在后台按固定管道执行SVG生成和PPTX导出。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "conversation_id": {"type": "string"},
                    "source_markdown": {
                        "type": "string",
                        "description": "markitdown转换后的内容",
                    },
                    "template_id": {
                        "type": "string",
                        "description": "选用的模板ID（可选）",
                    },
                    "outline": {
                        "type": "object",
                        "description": "确认后的大纲结构",
                    },
                    "design_spec": {
                        "type": "string",
                        "description": "设计规范文档",
                    },
                    "spec_lock": {
                        "type": "string",
                        "description": "锁定的规范",
                    },
                    "total_pages": {
                        "type": "integer",
                        "description": "总页数",
                    },
                    "pages": {
                        "type": "array",
                        "description": "每页的基本信息",
                    },
                },
                "required": ["user_id", "source_markdown", "outline"],
            },
        ),
        Tool(
            name="get_task_status",
            description="查询PPT生成任务的当前进度。返回状态、已完成页数、"
                        "每页状态，以及完成后的下载链接。",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "任务ID",
                    },
                },
                "required": ["task_id"],
            },
        ),
    ]


# ------------------------------------------------------------------
# Tool handlers
# ------------------------------------------------------------------

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "convert_document":
            return await _handle_convert(arguments)
        elif name == "list_templates":
            return await _handle_list_templates()
        elif name == "get_template_preview":
            return await _handle_template_preview(arguments)
        elif name == "create_ppt_task":
            return await _handle_create_task(arguments)
        elif name == "get_task_status":
            return await _handle_task_status(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as exc:
        logger.exception("MCP tool error: %s", name)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def _handle_convert(args: dict) -> list[TextContent]:
    md_svc = get_markitdown()
    if "file_path" in args and args["file_path"]:
        result = md_svc.convert_file(args["file_path"])
    elif "url" in args and args["url"]:
        result = md_svc.convert_url(args["url"])
    elif "text" in args and args["text"]:
        result = args["text"]
    else:
        return [TextContent(type="text", text="请提供 file_path、url 或 text")]
    return [TextContent(type="text", text=result)]


async def _handle_list_templates() -> list[TextContent]:
    svc = get_template_service()
    templates = await svc.list_templates()
    return [TextContent(type="text", text=json.dumps(templates, ensure_ascii=False, indent=2))]


async def _handle_template_preview(args: dict) -> list[TextContent]:
    svc = get_template_service()
    template = await svc.get_template(args["template_id"])
    if template is None:
        return [TextContent(type="text", text=f"模板不存在: {args['template_id']}")]
    info = {
        "template_id": template.template_id,
        "display_name": template.display_name,
        "category": template.category,
        "primary_color": template.primary_color,
        "font_stack": template.font_stack,
        "pages": [{"filename": p.filename, "page_type": p.page_type} for p in template.pages],
        "design_spec_preview": template.design_spec_md[:2000] if template.design_spec_md else "",
    }
    return [TextContent(type="text", text=json.dumps(info, ensure_ascii=False, indent=2))]


async def _handle_create_task(args: dict) -> list[TextContent]:
    import asyncio
    import uuid
    from app.models.task import PPTTask, TaskStatus, PageResult

    db = get_db()
    worker = get_task_worker()
    task_id = str(uuid.uuid4())[:12]

    pages = []
    for i, p in enumerate(args.get("pages", [])):
        pages.append(PageResult(
            page_num=i + 1,
            page_type=p.get("type", "content"),
            title=p.get("title", ""),
        ))
    if not pages and args.get("total_pages", 0) > 0:
        for i in range(args["total_pages"]):
            pages.append(PageResult(page_num=i + 1))

    task = PPTTask(
        task_id=task_id,
        user_id=args["user_id"],
        conversation_id=args.get("conversation_id", ""),
        status=TaskStatus.OUTLINE_CONFIRMED,
        source_markdown=args["source_markdown"],
        template_id=args.get("template_id", ""),
        outline=args.get("outline", {}),
        design_spec=args.get("design_spec", ""),
        spec_lock=args.get("spec_lock", ""),
        total_pages=len(pages),
        pages=pages,
    )

    await db.ppt_tasks.insert_one(task.model_dump())
    asyncio.create_task(worker.execute(task_id))

    return [TextContent(
        type="text",
        text=json.dumps({
            "task_id": task_id,
            "status": "outline_confirmed",
            "total_pages": len(pages),
            "message": f"PPT生成任务已创建，共{len(pages)}页，后台执行中。"
                       f"使用 get_task_status 查询进度。",
        }, ensure_ascii=False),
    )]


async def _handle_task_status(args: dict) -> list[TextContent]:
    from app.models.task import PPTTask
    db = get_db()
    doc = await db.ppt_tasks.find_one({"task_id": args["task_id"]}, {"_id": 0})
    if doc is None:
        return [TextContent(type="text", text=f"任务不存在: {args['task_id']}")]
    task = PPTTask(**doc)
    return [TextContent(type="text", text=json.dumps(task.to_progress(), ensure_ascii=False, indent=2))]
```

---

## Phase A 验证结果 (2026-05-17)

✅ **3 页 E2E 测试完全通过**

| 指标 | 结果 |
|------|------|
| 总耗时 | ~80s (3页) |
| 页面成功率 | 3/3 (100%) |
| PPTX 文件大小 | 39.4 KB |
| SVG 质量 | 封面渐变 + 内容页三栏布局 + 标签芯片 |

### 代码变更

- `ArtifactTabs.tsx`: `onConfirm` 从 console.log 改为调用真实 `createTask` API
- `PPTOutlineEditor.tsx`: 添加 loading/error 状态反馈

render_diffs(file:///d:/AI/Projects/genText/AI-Office-Mate/main/client/src/components/Artifacts/ArtifactTabs.tsx)
render_diffs(file:///d:/AI/Projects/genText/AI-Office-Mate/main/client/src/components/Artifacts/PPTOutlineEditor.tsx)
