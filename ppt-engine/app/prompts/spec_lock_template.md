# spec_lock 模板 — 锁定规范

项目确认后生成的锁定规范文件，确保 Executor 阶段的确定性。

---
project_title: "{title}"
total_pages: {total_pages}
canvas: ppt169
viewBox: "0 0 1280 720"
template_id: "{template_id}"
---

## 设计规范

### 配色方案
- 主色: {primary_color}
- 强调色: {accent_color}
- 背景色: {bg_color}
- 文本色: {text_color}

### 字体方案
- 标题: {title_font}
- 正文: {body_font}

### 风格
- 主题模式: {theme_mode}
- 设计风格: {style_desc}

## 页面清单

{pages_spec}

## 约束

- 每页 SVG 必须严格遵守上述配色和字体
- 所有文本使用中文
- 数据可视化优先使用原生 SVG 图形（rect/circle/path）
- 禁止使用外部图片链接
