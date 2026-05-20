/**
 * PPT Outline Editor — Artifacts panel component.
 *
 * Displays the AI-generated outline for user confirmation/editing:
 * - Page list with titles and key points
 * - Template selector (inline from template library)
 * - Design parameter preview (colors, fonts)
 * - "Confirm & Generate" button to create a Task
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Check, ChevronDown, ChevronUp, GripVertical, Loader2, Palette, Type } from 'lucide-react';
import { listTemplates, getTemplatePageSvgUrl } from '~/utils/pptApi';
import type { TemplateSummary } from '~/utils/pptApi';

interface OutlinePage {
  type: string;
  title: string;
  points: string[];
}

interface PPTOutlineEditorProps {
  outline: {
    title: string;
    pages: OutlinePage[];
    design?: {
      primary_color?: string;
      font_stack?: string[];
      style?: string;
    };
  };
  onConfirm: (data: {
    outline: { title: string; pages: OutlinePage[] };
    template_id: string;
  }) => void;
}

export default function PPTOutlineEditor({ outline, onConfirm }: PPTOutlineEditorProps) {
  const [pages, setPages] = useState<OutlinePage[]>(outline.pages || []);
  const [title, setTitle] = useState(outline.title || '');
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [expandedPage, setExpandedPage] = useState<number | null>(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    listTemplates().then(setTemplates).catch(console.error);
  }, []);

  const handleConfirm = useCallback(async () => {
    setIsSubmitting(true);
    setSubmitError('');
    try {
      await onConfirm({
        outline: { title, pages },
        template_id: selectedTemplate,
      });
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : '创建任务失败');
    } finally {
      setIsSubmitting(false);
    }
  }, [title, pages, selectedTemplate, onConfirm]);

  const updatePageTitle = (idx: number, newTitle: string) => {
    const updated = [...pages];
    updated[idx] = { ...updated[idx], title: newTitle };
    setPages(updated);
  };

  const updatePagePoint = (pageIdx: number, pointIdx: number, value: string) => {
    const updated = [...pages];
    const points = [...updated[pageIdx].points];
    points[pointIdx] = value;
    updated[pageIdx] = { ...updated[pageIdx], points };
    setPages(updated);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border-medium px-4 py-3">
        <input
          className="w-full bg-transparent text-lg font-bold text-text-primary outline-none placeholder:text-text-tertiary"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="演示文稿标题"
        />
        <p className="mt-1 text-xs text-text-secondary">
          共 {pages.length} 页 · 编辑大纲后点击确认生成
        </p>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Page list */}
        <div className="p-4 space-y-2">
          {pages.map((page, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-border-light bg-surface-secondary"
            >
              {/* Page header */}
              <button
                className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
                onClick={() => setExpandedPage(expandedPage === idx ? null : idx)}
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white">
                  {idx + 1}
                </span>
                <span className="flex-1 text-sm font-medium text-text-primary">
                  {page.title || `第 ${idx + 1} 页`}
                </span>
                <span className="rounded-full bg-surface-tertiary px-2 py-0.5 text-xs text-text-secondary">
                  {page.type}
                </span>
                {expandedPage === idx ? (
                  <ChevronUp className="h-4 w-4 text-text-tertiary" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-text-tertiary" />
                )}
              </button>

              {/* Expanded content */}
              {expandedPage === idx && (
                <div className="border-t border-border-light px-3 py-3 space-y-2">
                  <input
                    className="w-full rounded-lg bg-surface-primary px-2 py-1.5 text-sm text-text-primary outline-none border border-border-light focus:border-blue-500"
                    value={page.title}
                    onChange={(e) => updatePageTitle(idx, e.target.value)}
                    placeholder="页面标题"
                  />
                  {page.points.map((point, pIdx) => (
                    <input
                      key={pIdx}
                      className="w-full rounded-lg bg-surface-primary px-2 py-1 text-xs text-text-secondary outline-none border border-border-light focus:border-blue-500"
                      value={point}
                      onChange={(e) => updatePagePoint(idx, pIdx, e.target.value)}
                      placeholder={`要点 ${pIdx + 1}`}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Template selector */}
        <div className="border-t border-border-medium px-4 py-3">
          <h3 className="mb-2 text-xs font-semibold text-text-secondary uppercase tracking-wider">
            选择模板（可选）
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {/* No template option */}
            <button
              onClick={() => setSelectedTemplate('')}
              className={`rounded-xl border-2 p-2 text-xs text-center transition-colors ${
                selectedTemplate === ''
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-border-light hover:border-border-medium'
              }`}
            >
              <Palette className="mx-auto mb-1 h-5 w-5 text-text-secondary" />
              自由设计
            </button>

            {templates.map((t) => (
              <button
                key={t.template_id}
                onClick={() => setSelectedTemplate(t.template_id)}
                className={`rounded-xl border-2 p-2 text-xs text-center transition-colors ${
                  selectedTemplate === t.template_id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-border-light hover:border-border-medium'
                }`}
              >
                <div
                  className="mx-auto mb-1 h-5 w-8 rounded"
                  style={{ backgroundColor: t.primary_color }}
                />
                <span className="block truncate">{t.display_name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Confirm button */}
      <div className="border-t border-border-medium px-4 py-3">
        <button
          onClick={handleConfirm}
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              正在创建任务…
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              确认大纲 · 开始生成
            </>
          )}
        </button>
        {submitError && (
          <p className="mt-2 text-xs text-red-500 text-center">{submitError}</p>
        )}
      </div>
    </div>
  );
}
