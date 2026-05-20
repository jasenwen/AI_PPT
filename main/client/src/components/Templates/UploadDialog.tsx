import React, { useState, useCallback, useRef } from 'react';
import { Upload, X } from 'lucide-react';
import { OGDialog, OGDialogContent, useToastContext } from '@librechat/client';
import { uploadTemplate } from '~/utils/pptApi';
import { cn } from '~/utils';

interface UploadDialogProps {
  open: boolean;
  onClose: () => void;
  onUploaded: () => void;
}

export default function UploadDialog({ open, onClose, onUploaded }: UploadDialogProps) {
  const { showToast } = useToastContext();
  const [file, setFile] = useState<File | null>(null);
  const [templateId, setTemplateId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [category, setCategory] = useState('general');
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setFile(null);
    setTemplateId('');
    setDisplayName('');
    setCategory('general');
  }, []);

  const handleClose = useCallback(() => {
    if (!uploading) {
      reset();
      onClose();
    }
  }, [uploading, reset, onClose]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.toLowerCase().endsWith('.pptx')) {
      setFile(f);
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !templateId || !displayName) return;

    setUploading(true);
    try {
      await uploadTemplate(file, templateId, displayName, category);
      showToast({ status: 'success', message: '模板上传成功' });
      reset();
      onUploaded();
      onClose();
    } catch (err: any) {
      showToast({ status: 'error', message: err.message || '上传失败' });
    } finally {
      setUploading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const inputCls =
    'w-full rounded-lg border border-border-medium bg-surface-secondary px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-colors';

  return (
    <OGDialog open={open} onOpenChange={(v: boolean) => !v && handleClose()}>
      <OGDialogContent className="w-11/12 max-w-md border-border-light bg-surface-primary p-0 text-text-primary">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-light px-5 py-4">
          <h2 className="text-base font-semibold text-text-primary">上传 PPT 模板</h2>
          <button
            onClick={handleClose}
            className="rounded-md p-1 text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
          >
            <X className="size-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-5 py-4">
          {/* Drop zone */}
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={cn(
              'flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors',
              dragOver
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/10'
                : 'border-border-medium hover:border-border-heavy',
            )}
          >
            <Upload className="size-7 text-text-tertiary" />
            {file ? (
              <div className="text-center">
                <p className="text-sm font-medium text-text-primary">{file.name}</p>
                <p className="text-xs text-text-secondary">{formatSize(file.size)}</p>
              </div>
            ) : (
              <p className="text-sm text-text-secondary">
                拖拽或点击选择 <span className="font-medium text-text-primary">.pptx</span> 文件
              </p>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".pptx"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>

          {/* Template ID */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-secondary">模板 ID</label>
            <input
              type="text"
              placeholder="英文标识 (如 acme_brand_2024)"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
              className={inputCls}
            />
          </div>

          {/* Display name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-secondary">显示名称</label>
            <input
              type="text"
              placeholder="如: ACME 企业模板"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className={inputCls}
            />
          </div>

          {/* Category */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-secondary">分类</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className={inputCls}>
              <option value="general">通用</option>
              <option value="brand">品牌</option>
              <option value="scenario">场景</option>
              <option value="government">政务</option>
            </select>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 border-t border-border-light pt-4">
            <button
              type="button"
              onClick={handleClose}
              disabled={uploading}
              className="rounded-lg border border-border-medium px-4 py-2 text-sm text-text-secondary transition-colors hover:bg-surface-hover disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={uploading || !file || !templateId || !displayName}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading ? '导入中…' : '上传并导入'}
            </button>
          </div>
        </form>
      </OGDialogContent>
    </OGDialog>
  );
}
