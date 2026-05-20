/**
 * Template Management Page — /templates route.
 *
 * Standalone page for managing PPT templates:
 * - Browse uploaded templates in a grid
 * - Upload new PPTX templates
 * - Preview template pages (SVG)
 * - Delete templates
 * - Filter by category
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Presentation, Plus, FolderOpen, Search } from 'lucide-react';
import { Spinner, useToastContext } from '@librechat/client';
import {
  listTemplates,
  deleteTemplate,
  getTemplate,
} from '~/utils/pptApi';
import type { TemplateSummary, TemplateDetail } from '~/utils/pptApi';
import { cn } from '~/utils';
import TemplateCard from './TemplateCard';
import UploadDialog from './UploadDialog';
import PreviewDialog from './PreviewDialog';

// ------------------------------------------------------------------
// Category filter tabs
// ------------------------------------------------------------------

const CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'general', label: '通用' },
  { key: 'brand', label: '品牌' },
  { key: 'scenario', label: '场景' },
  { key: 'government', label: '政务' },
];

// ------------------------------------------------------------------
// Skeleton Card (loading state)
// ------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-border-light bg-surface-primary-alt">
      <div className="aspect-[16/10] w-full animate-pulse bg-surface-tertiary" />
      <div className="flex flex-col gap-2 px-3 py-3">
        <div className="h-4 w-3/4 animate-pulse rounded bg-surface-tertiary" />
        <div className="h-3 w-1/2 animate-pulse rounded bg-surface-tertiary" />
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Main Page
// ------------------------------------------------------------------

export default function TemplatesPage() {
  const { showToast } = useToastContext();
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<TemplateDetail | null>(null);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
      showToast({ status: 'error', message: '加载模板列表失败' });
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  // Filtered list
  const filtered = useMemo(() => {
    let list = templates;
    if (activeCategory !== 'all') {
      list = list.filter((t) => t.category === activeCategory);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (t) =>
          t.display_name.toLowerCase().includes(q) ||
          t.template_id.toLowerCase().includes(q),
      );
    }
    return list;
  }, [templates, activeCategory, searchQuery]);

  const handlePreview = async (id: string) => {
    try {
      const detail = await getTemplate(id);
      setPreviewTemplate(detail);
    } catch (err) {
      console.error('Failed to load template:', err);
      showToast({ status: 'error', message: '加载模板详情失败' });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`确定要删除模板 "${id}" 吗？此操作不可撤销。`)) return;
    try {
      await deleteTemplate(id);
      showToast({ status: 'success', message: '模板已删除' });
      loadTemplates();
    } catch (err) {
      console.error('Failed to delete template:', err);
      showToast({ status: 'error', message: '删除失败' });
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-presentation">
      {/* Top bar */}
      <div className="shrink-0 border-b border-border-light px-5 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-green-600/10">
              <Presentation className="size-5 text-green-600" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-primary">PPT 模板库</h1>
              {!loading && (
                <p className="text-xs text-text-secondary">
                  共 {templates.length} 个模板
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => setUploadOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-green-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-green-700"
          >
            <Plus className="size-4" />
            上传模板
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="shrink-0 border-b border-border-light bg-surface-primary-alt px-5 py-2.5">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          {/* Category tabs */}
          <div className="flex items-center gap-1">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setActiveCategory(cat.key)}
                className={cn(
                  'rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                  activeCategory === cat.key
                    ? 'bg-surface-primary text-text-primary shadow-sm'
                    : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary',
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative ml-auto">
            <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-text-tertiary" />
            <input
              type="text"
              placeholder="搜索模板…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-48 rounded-lg border border-border-medium bg-surface-secondary py-1.5 pl-8 pr-3 text-xs text-text-primary placeholder:text-text-tertiary focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500/30 transition-colors"
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        <div className="mx-auto max-w-6xl">
          {loading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-text-secondary">
              <FolderOpen className="mb-3 size-12 opacity-20" aria-hidden="true" />
              <p className="text-base font-medium">
                {templates.length === 0 ? '暂无模板' : '未找到匹配的模板'}
              </p>
              <p className="mt-1 text-sm text-text-tertiary">
                {templates.length === 0
                  ? '上传企业 PPTX 文件，自动解析为可复用模板'
                  : '尝试调整搜索条件或分类筛选'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filtered.map((t) => (
                <TemplateCard
                  key={t.template_id}
                  template={t}
                  onPreview={handlePreview}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Upload dialog */}
      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={loadTemplates}
      />

      {/* Preview dialog */}
      <PreviewDialog
        template={previewTemplate}
        onClose={() => setPreviewTemplate(null)}
      />
    </div>
  );
}
