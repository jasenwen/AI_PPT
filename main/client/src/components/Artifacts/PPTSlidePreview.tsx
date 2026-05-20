/**
 * PPT Slide Preview — Artifacts panel component.
 *
 * Full-page SVG slide viewer with:
 * - Page navigation (prev/next + thumbnails)
 * - Zoom controls
 * - PPTX download button
 */

import React, { useState, useEffect } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  FileDown,
  Maximize2,
} from 'lucide-react';
import { getDownloadUrl, getTaskStatus, downloadPptx, fetchPageSvg } from '~/utils/pptApi';
import type { TaskProgress } from '~/utils/pptApi';

interface PPTSlidePreviewProps {
  taskId: string;
}

export default function PPTSlidePreview({ taskId }: PPTSlidePreviewProps) {
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [svgContent, setSvgContent] = useState('');

  // Load task info
  useEffect(() => {
    getTaskStatus(taskId).then(setProgress).catch(console.error);
  }, [taskId]);

  // Load current page SVG
  useEffect(() => {
    if (!progress || currentPage < 1) return;

    const page = progress.pages[currentPage - 1];
    if (!page || page.status !== 'done') {
      setSvgContent('');
      return;
    }

    fetchPageSvg(taskId, currentPage)
      .then(setSvgContent)
      .catch(() => setSvgContent(''));
  }, [taskId, currentPage, progress]);

  if (!progress) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  const totalPages = progress.total_pages;
  const completedPages = progress.pages.filter((p) => p.status === 'done');

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface-primary">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border-medium px-3 py-2">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            className="rounded-lg p-1.5 hover:bg-surface-hover disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="h-4 w-4 text-text-primary" />
          </button>
          <span className="min-w-[60px] text-center text-xs text-text-secondary">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className="rounded-lg p-1.5 hover:bg-surface-hover disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="h-4 w-4 text-text-primary" />
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setZoom(Math.max(50, zoom - 25))}
            className="rounded-lg p-1.5 hover:bg-surface-hover transition-colors"
          >
            <ZoomOut className="h-4 w-4 text-text-primary" />
          </button>
          <span className="min-w-[40px] text-center text-xs text-text-secondary">{zoom}%</span>
          <button
            onClick={() => setZoom(Math.min(200, zoom + 25))}
            className="rounded-lg p-1.5 hover:bg-surface-hover transition-colors"
          >
            <ZoomIn className="h-4 w-4 text-text-primary" />
          </button>
          <button
            onClick={() => setZoom(100)}
            className="rounded-lg p-1.5 hover:bg-surface-hover transition-colors"
          >
            <Maximize2 className="h-4 w-4 text-text-primary" />
          </button>
        </div>

        {progress.pptx_url && (
          <button
            onClick={() => downloadPptx(taskId).catch(console.error)}
            className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 transition-colors"
          >
            <FileDown className="h-3.5 w-3.5" />
            下载
          </button>
        )}
      </div>

      {/* SVG viewer */}
      <div className="flex-1 overflow-auto bg-gray-100 dark:bg-gray-900 p-4">
        <div
          className="mx-auto"
          style={{
            transform: `scale(${zoom / 100})`,
            transformOrigin: 'top center',
          }}
        >
          {svgContent ? (
            <div
              className="rounded-lg bg-white shadow-xl"
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          ) : (
            <div className="flex h-[405px] w-[720px] items-center justify-center rounded-lg bg-white shadow-xl">
              <p className="text-sm text-gray-400">暂无预览</p>
            </div>
          )}
        </div>
      </div>

      {/* Thumbnail strip */}
      {completedPages.length > 1 && (
        <div className="flex gap-2 overflow-x-auto border-t border-border-medium px-3 py-2">
          {progress.pages.map((page) => (
            <button
              key={page.page_num}
              onClick={() => page.status === 'done' && setCurrentPage(page.page_num)}
              className={`flex-shrink-0 rounded-lg border-2 px-2 py-1 text-xs transition-colors ${
                page.page_num === currentPage
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600'
                  : page.status === 'done'
                    ? 'border-border-light text-text-secondary hover:border-border-medium'
                    : 'border-border-light text-text-tertiary opacity-50'
              }`}
            >
              P{page.page_num}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
