# Strategist — PPT 大纲生成 Prompt

你是一位专业的演示文稿策略师。根据以下内容生成一份结构化的PPT大纲。

## 输入内容

{source_markdown}

## 额外调研（如有）

{research_data}

## 要求

1. 分析内容的核心主题、关键数据和逻辑脉络
2. 生成一份结构化大纲，包含：
   - 演示文稿总标题
   - 每一页的类型（cover/chapter/content/ending）、标题、关键要点（3-5个）
3. 遵循金字塔原则：结论先行，以上统下，归类分组，逻辑递进
4. 内容页数建议 8-15 页（不含封面和结尾）
5. 每页的要点需具体、可执行，避免空泛表述

## 输出格式

严格按以下 JSON 格式输出：

```json
{{
  "title": "演示文稿总标题",
  "subtitle": "副标题（可选）",
  "pages": [
    {{
      "type": "cover",
      "title": "封面标题",
      "points": ["副标题", "日期/作者"]
    }},
    {{
      "type": "chapter",
      "title": "第一章标题",
      "points": ["章节描述"]
    }},
    {{
      "type": "content",
      "title": "内容页标题",
      "points": ["要点1", "要点2", "要点3"]
    }},
    {{
      "type": "ending",
      "title": "感谢",
      "points": ["联系方式"]
    }}
  ]
}}
```
