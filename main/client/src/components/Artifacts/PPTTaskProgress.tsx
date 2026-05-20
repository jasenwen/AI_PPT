/**
 * PPT Task Progress — Artifacts panel component.
 *
 * Shows real-time progress of a PPT generation task:
 * - Overall progress bar
 * - Per-page status indicators
 * - SVG thumbnail preview for completed pages
 * - Auto-polls task status every 2 seconds
 */

import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle, Clock, Loader2, AlertCircle, Download, FileDown } from 'lucide-react';
import { getTaskStatus, getPageSvgUrl, downloadPptx } from '~/utils/pptApi';
import type { TaskProgress } from '~/utils/pptApi';

interface PPTTaskProgressProps {
  taskId: string;
  onComplete?: (pptxUrl: string) => void;
}

const STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  preprocessing: '预处理中',
  outline_ready: '大纲已生成',
  outline_confirmed: '大纲已确认',
  generating: '正在生成幻灯片',
  finalizing: '正在优化',
  exporting: '正在导出 PPTX',
  completed: '生成完成',
  failed: '生成失败',
};

function PageStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'done':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'generating':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
    case 'error':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-text-tertiary" />;
  }
}

export default function PPTTaskProgress({ taskId, onComplete }: PPTTaskProgressProps) {
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [error, setError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await getTaskStatus(taskId);
        setProgress(data);

        // Stop polling when terminal
        if (data.status === 'completed' || data.status === 'failed') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (data.status === 'completed' && data.pptx_url && onComplete) {
            onComplete(data.pptx_url);
          }
        }
      } catch (err: any) {
        setError(err.message);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId, onComplete]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <p className="text-sm text-red-500">加载失败: {error}</p>
      </div>
    );
  }

  if (!progress) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
      </div>
    );
  }

  const pct = progress.total_pages > 0
    ? Math.round((progress.completed_pages / progress.total_pages) * 100)
    : 0;

  const isTerminal = progress.status === 'completed' || progress.status === 'failed';

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border-medium px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">
            {STATUS_LABELS[progress.status] || progress.status}
          </h3>
          {progress.status === 'generating' && (
            <span className="text-xs text-text-secondary">
              {progress.completed_pages}/{progress.total_pages}
            </span>
          )}
        </div>

        {/* Progress bar */}
        {!isTerminal && (
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-tertiary">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
        )}

        {progress.progress_message && (
          <p className="mt-1 text-xs text-text-secondary">{progress.progress_message}</p>
        )}
      </div>

      {/* Page list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {progress.pages.map((page) => (
          <div
            key={page.page_num}
            className="flex items-center gap-3 rounded-xl border border-border-light bg-surface-secondary px-3 py-2"
          >
            <PageStatusIcon status={page.status} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                第 {page.page_num} 页 · {page.title || page.page_type}
              </p>
            </div>
            {page.status === 'done' && (
              <a
                href={getPageSvgUrl(taskId, page.page_num)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                预览
              </a>
            )}
          </div>
        ))}
      </div>

      {/* Download button */}
      {progress.status === 'completed' && progress.pptx_url && (
        <div className="border-t border-border-medium px-4 py-3">
          <button
            onClick={() => downloadPptx(taskId).catch(console.error)}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-600 py-2.5 text-sm font-medium text-white hover:bg-green-700 transition-colors"
          >
            <FileDown className="h-4 w-4" />
            下载 PPTX
          </button>
        </div>
      )}

      {/* Error display */}
      {progress.status === 'failed' && progress.error && (
        <div className="border-t border-border-medium px-4 py-3">
          <p className="text-sm text-red-500">{progress.error}</p>
        </div>
      )}
    </div>
  );
}
