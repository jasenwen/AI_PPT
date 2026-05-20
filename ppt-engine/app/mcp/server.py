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


# ------------------------------------------------------------------
# SSE transport mount
# ------------------------------------------------------------------

sse_transport = SseServerTransport("/mcp/messages")


async def handle_sse(scope, receive, send):
    """SSE connection endpoint — LibreChat connects here.

    This is a raw ASGI app (not a Starlette endpoint) so that
    ``scope``, ``receive``, and ``send`` are passed directly by the
    ASGI server rather than via a Starlette ``Request`` wrapper.

    MCP SDK v1.11+ ``connect_sse`` and ``handle_post_message`` both
    expect the raw ASGI triple — they must NOT be wrapped by
    Starlette's ``request_response`` adapter (which ``Route(endpoint=)``
    does).  We therefore mount them via ``Mount(app=)`` instead.
    """
    async with sse_transport.connect_sse(scope, receive, send) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


def create_mcp_routes() -> list:
    """Return Starlette routes to mount on the FastAPI app.

    Starlette's ``Route(endpoint=func)`` checks ``inspect.isfunction``
    and, when True, wraps the handler with ``request_response`` (which
    passes a single ``Request`` arg instead of raw ASGI triple).

    The MCP SDK v1.11+ handlers need the raw ``(scope, receive, send)``
    triple.  By wrapping them in a callable *class*, ``inspect.isfunction``
    returns ``False`` and Starlette passes the triple through unchanged —
    while still using ``Route`` (exact path match, no trailing-slash
    redirect that ``Mount`` would add).
    """
    from starlette.routing import Route

    class _RawAsgi:
        """Thin wrapper so Starlette treats the handler as an ASGI app."""
        def __init__(self, handler):
            self._handler = handler

        async def __call__(self, scope, receive, send):
            await self._handler(scope, receive, send)

    return [
        Route("/mcp/sse", endpoint=_RawAsgi(handle_sse)),
        Route("/mcp/messages", endpoint=_RawAsgi(sse_transport.handle_post_message), methods=["POST"]),
    ]

