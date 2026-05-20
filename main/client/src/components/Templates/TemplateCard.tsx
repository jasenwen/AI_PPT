import React from 'react';
import { Trash2, Eye, Layers } from 'lucide-react';
import { TooltipAnchor } from '@librechat/client';
import type { TemplateSummary } from '~/utils/pptApi';
import { getTemplatePageSvgUrl } from '~/utils/pptApi';
import { cn } from '~/utils';

interface TemplateCardProps {
  template: TemplateSummary;
  onPreview: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function TemplateCard({ template, onPreview, onDelete }: TemplateCardProps) {
  const thumbUrl = getTemplatePageSvgUrl(template.template_id, 'cover.svg');

  return (
    <div
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-lg border border-border-light',
        'bg-surface-primary-alt shadow-sm transition-all duration-200',
        'hover:shadow-md hover:border-border-medium',
      )}
    >
      {/* Thumbnail area */}
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-surface-tertiary">
        <img
          src={thumbUrl}
          alt={template.display_name}
          className="h-full w-full object-contain p-2"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
        {/* Fallback when no thumbnail */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-text-tertiary">
          <Layers className="mb-1 size-8 opacity-30" aria-hidden="true" />
        </div>

        {/* Hover overlay */}
        <div
          className={cn(
            'absolute inset-0 flex items-center justify-center gap-2',
            'bg-black/40 opacity-0 transition-opacity duration-200',
            'group-hover:opacity-100',
          )}
        >
          <button
            onClick={() => onPreview(template.template_id)}
            className="flex items-center gap-1.5 rounded-md bg-white/90 px-3 py-1.5 text-xs font-medium text-gray-800 shadow-sm transition-colors hover:bg-white"
          >
            <Eye className="size-3.5" />
            预览
          </button>
        </div>

        {/* Color indicator */}
        <div
          className="absolute bottom-0 left-0 right-0 h-1"
          style={{ backgroundColor: template.primary_color }}
        />
      </div>

      {/* Info */}
      <div className="flex flex-1 flex-col gap-1 px-3 py-2.5">
        <h3
          className="truncate text-sm font-semibold text-text-primary"
          title={template.display_name}
        >
          {template.display_name}
        </h3>
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <span className="rounded bg-surface-tertiary px-1.5 py-0.5">{template.category}</span>
          <span>{template.page_count} 页</span>
        </div>
      </div>

      {/* Delete — hover only */}
      <div className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100">
        <TooltipAnchor
          description="删除模板"
          side="left"
          render={
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(template.template_id);
              }}
              className="rounded-md bg-black/50 p-1.5 text-white/80 transition-colors hover:bg-red-600 hover:text-white"
              aria-label="删除模板"
            >
              <Trash2 className="size-3.5" />
            </button>
          }
        />
      </div>
    </div>
  );
}
