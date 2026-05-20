"""End-to-end PPT generation test — creates a task and polls until completion."""

import time
import json
import requests

BASE = "http://localhost:8100"

# 1. Create a 3-page task
print("=" * 60)
print("Step 1: Creating PPT task (3 pages)")
print("=" * 60)

task_data = {
    "user_id": "e2e-test",
    "conversation_id": "e2e-conv",
    "source_markdown": "# AI驱动的企业数字化转型\n\n## 核心技术\n- 大语言模型 (LLM)\n- 知识图谱\n- 多模态感知\n\n## 应用场景\n- 智能客服\n- 文档分析",
    "outline": {
        "title": "AI驱动的企业数字化转型",
        "pages": [
            {"type": "cover", "title": "AI驱动的企业数字化转型", "points": ["2024年战略报告"]},
            {"type": "content", "title": "核心技术架构", "points": ["大语言模型 (LLM)", "知识图谱", "多模态感知"]},
            {"type": "ending", "title": "谢谢", "points": ["Q&A"]}
        ]
    },
    "pages": [
        {"type": "cover", "title": "AI驱动的企业数字化转型"},
        {"type": "content", "title": "核心技术架构"},
        {"type": "ending", "title": "谢谢"}
    ]
}

resp = requests.post(f"{BASE}/api/tasks", json=task_data)
result = resp.json()
task_id = result["task_id"]
print(f"Task ID: {task_id}")
print(f"Status:  {result['status']}")
print(f"Pages:   {result['total_pages']}")

# 2. Poll task status
print("\n" + "=" * 60)
print("Step 2: Polling task progress...")
print("=" * 60)

max_wait = 300  # 5 minutes max
elapsed = 0

while elapsed < max_wait:
    time.sleep(5)
    elapsed += 5
    
    status_resp = requests.get(f"{BASE}/api/tasks/{task_id}")
    progress = status_resp.json()
    
    status = progress["status"]
    completed = progress["completed_pages"]
    total = progress["total_pages"]
    msg = progress.get("progress_message", "")
    
    print(f"  [{elapsed:3d}s] {status} — {completed}/{total} — {msg}")
    
    # Show per-page status
    for p in progress["pages"]:
        icon = "✅" if p["status"] == "done" else "⏳" if p["status"] == "generating" else "❌" if p["status"] == "failed" else "⬜"
        err = f" ({p['error']})" if p.get("error") else ""
        print(f"         {icon} P{p['page_num']}: {p['title']} [{p['status']}]{err}")
    
    if status in ("completed", "failed"):
        break

# 3. Final result
print("\n" + "=" * 60)
print("Step 3: Final Result")
print("=" * 60)

final = requests.get(f"{BASE}/api/tasks/{task_id}").json()
print(json.dumps(final, ensure_ascii=False, indent=2))

if final["status"] == "completed":
    print(f"\n🎉 SUCCESS! Download: {BASE}{final['pptx_url']}")
elif final["status"] == "failed":
    print(f"\n❌ FAILED: {final.get('error', 'unknown')}")
else:
    print(f"\n⏳ TIMEOUT after {max_wait}s — status: {final['status']}")
