# Executor — 单页 SVG 生成 Prompt

## 任务

生成第 {page_number}/{total_pages} 页的完整 SVG。

## 页面规范

- **页面类型**: {page_type}
- **页面标题**: {page_title}
- **内容要点**:
{page_content}

## 设计规范（必须严格遵守）

### 画布
- viewBox: "0 0 1280 720" (16:9)
- 背景色: {bg_color}

### 配色
{design_colors}

### 字体
{design_fonts}

### 模板参考（如有）
{template_reference}

## SVG 技术约束（Mandatory）

1. **纯内联样式** — 禁止 `<style>` 块、禁止 class 属性
2. **禁止元素**: `<foreignObject>`, CSS 动画, JavaScript, `<animate>`
3. **文本**: 只使用 `<text>` 元素，必须有明确 x/y 坐标
4. **字体**: 只使用设计规范中指定的字体，或 web-safe 字体
5. **颜色**: 所有颜色必须是明确的 HEX 值
6. **分组**: 相关元素用 `<g id="...">` 分组
7. **文本不得溢出** — 预估文本宽度，确保不超过容器边界
8. **每行文本独立 `<text>` 元素** — 不使用 `<tspan>` 换行

## 布局参考

- 安全边距: 上下 40px, 左右 60px
- 标题区域: y=40 到 y=100
- 内容区域: y=120 到 y=660
- 页码区域: y=700

## 输出

直接输出 SVG 代码，不要任何解释或 markdown 围栏。
