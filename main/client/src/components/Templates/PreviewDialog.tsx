import React, { useState, useEffect, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Type, Palette } from 'lucide-react';
import type { TemplateDetail } from '~/utils/pptApi';
import { getTemplatePageSvgUrl } from '~/utils/pptApi';
import { cn } from '~/utils';

interface PreviewDialogProps {
  template: TemplateDetail | null;
  onClose: () => void;
}

export default function PreviewDialog({ template, onClose }: PreviewDialogProps) {
  const [currentPage, setCurrentPage] = useState(0);

  // Reset page when template changes
  useEffect(() => { setCurrentPage(0); }, [template?.template_id]);

  // Keyboard navigation
  const handleKey = useCallback((e: KeyboardEvent) => {
    if (!template) return;
    const max = (template.pages?.length ?? 1) - 1;
    if (e.key === 'ArrowLeft') setCurrentPage((p) => Math.max(0, p - 1));
    else if (e.key === 'ArrowRight') setCurrentPage((p) => Math.min(max, p + 1));
    else if (e.key === 'Escape') onClose();
  }, [template, onClose]);

  useEffect(() => {
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleKey]);

  if (!template) return null;

  const pages = template.pages || [];
  const currentSvgUrl = pages[currentPage]
    ? getTemplatePageSvgUrl(template.template_id, pages[currentPage].filename)
    : '';
  const hasPrev = currentPage > 0;
  const hasNext = currentPage < pages.length - 1;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="flex h-[85vh] w-[92vw] max-w-6xl flex-col overflow-hidden rounded-xl border border-border-light bg-surface-primary shadow-2xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border-light px-5 py-3">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-base font-semibold text-text-primary">
              {template.display_name}
            </h2>
            <div className="mt-0.5 flex flex-wrap items-center gap-3 text-xs text-text-secondary">
              <span className="flex items-center gap-1">
                <span
                  className="inline-block size-2.5 rounded-full"
                  style={{ backgroundColor: template.primary_color }}
                />
                {template.category}
              </span>
              <span>{pages.length} 页</span>
              {template.font_stack && template.font_stack.length > 0 && (
                <span className="flex items-center gap-1">
                  <Type className="size-3" />
                  {template.font_stack.slice(0, 2).join(', ')}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
            aria-label="关闭"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Main preview area */}
        <div className="relative flex-1 overflow-hidden bg-surface-tertiary">
          {currentSvgUrl && (
            <iframe
              src={currentSvgUrl}
              className="h-full w-full"
              title={`Slide ${currentPage + 1}`}
              sandbox="allow-same-origin"
            />
          )}

          {/* Prev / Next arrows */}
          {hasPrev && (
            <button
              onClick={() => setCurrentPage((p) => p - 1)}
              className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/80 backdrop-blur-sm transition-colors hover:bg-black/60 hover:text-white"
              aria-label="上一页"
            >
              <ChevronLeft className="size-5" />
            </button>
          )}
          {hasNext && (
            <button
              onClick={() => setCurrentPage((p) => p + 1)}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/80 backdrop-blur-sm transition-colors hover:bg-black/60 hover:text-white"
              aria-label="下一页"
            >
              <ChevronRight className="size-5" />
            </button>
          )}
        </div>

        {/* Page navigation thumbnails */}
        {pages.length > 1 && (
          <div className="flex shrink-0 items-center gap-1.5 overflow-x-auto border-t border-border-light bg-surface-primary-alt px-4 py-2.5">
            {pages.map((page, idx) => (
              <button
                key={page.filename}
                onClick={() => setCurrentPage(idx)}
                className={cn(
                  'flex shrink-0 items-center gap-1 rounded-md px-2.5 py-1.5 text-xs transition-colors',
                  idx === currentPage
                    ? 'bg-surface-primary font-medium text-text-primary shadow-sm'
                    : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary',
                )}
              >
                <span className="tabular-nums">{idx + 1}</span>
                <span className="hidden sm:inline">·</span>
                <span className="hidden sm:inline">{page.page_type}</span>
              </button>
            ))}
            <span className="ml-auto shrink-0 text-xs text-text-tertiary">
              {currentPage + 1} / {pages.length}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
