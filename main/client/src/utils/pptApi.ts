/**
 * PPT Engine API client — React hooks and fetch helpers.
 *
 * Provides typed API calls to the PPT Engine proxy endpoints
 * for template management, document conversion, and task lifecycle.
 */

import { getTokenHeader } from 'librechat-data-provider';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface TemplateSummary {
  template_id: string;
  display_name: string;
  category: string;
  canvas_format: string;
  primary_color: string;
  page_count: number;
  created_at: string;
}

export interface TemplatePage {
  filename: string;
  page_type: string;
  svg_path: string;
  thumbnail: string;
}

export interface TemplateDetail extends TemplateSummary {
  font_stack: string[];
  design_spec_md: string;
  pages: TemplatePage[];
  assets: Array<{ filename: string; path: string; usage: string }>;
  storage_path: string;
}

export interface TaskProgress {
  task_id: string;
  status: string;
  progress_message: string;
  total_pages: number;
  completed_pages: number;
  pages: Array<{
    page_num: number;
    page_type: string;
    title: string;
    svg_path: string;
    status: string;
    error: string;
  }>;
  pptx_url: string;
  error: string;
  updated_at: string;
}

export interface ConvertResult {
  markdown: string;
  source: string;
  source_type: string;
  char_count: number;
}

// ------------------------------------------------------------------
// API base path
// ------------------------------------------------------------------

const API_BASE = '/api/ppt';

/**
 * Build request headers including the JWT auth token from LibreChat's
 * auth system. The token is stored in axios defaults by the login flow
 * via `setTokenHeader()` — we read it back with `getTokenHeader()`.
 */
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const auth = getTokenHeader();
  if (auth) {
    headers['Authorization'] = auth;
  }
  return headers;
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: authHeaders({
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string> | undefined),
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

// ------------------------------------------------------------------
// Template API
// ------------------------------------------------------------------

export async function listTemplates(): Promise<TemplateSummary[]> {
  return fetchJSON(`${API_BASE}/templates`);
}

export async function getTemplate(templateId: string): Promise<TemplateDetail> {
  return fetchJSON(`${API_BASE}/templates/${templateId}`);
}

export async function uploadTemplate(
  file: File,
  templateId: string,
  displayName: string,
  category: string = 'general',
): Promise<TemplateSummary> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('template_id', templateId);
  formData.append('display_name', displayName);
  formData.append('category', category);

  const res = await fetch(`${API_BASE}/templates/upload`, {
    method: 'POST',
    body: formData,
    headers: authHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed: ${text}`);
  }
  return res.json();
}

export async function deleteTemplate(templateId: string): Promise<void> {
  await fetchJSON(`${API_BASE}/templates/${templateId}`, { method: 'DELETE' });
}

export function getTemplatePageSvgUrl(templateId: string, filename: string): string {
  return `${API_BASE}/templates/${templateId}/pages/${filename}`;
}

// ------------------------------------------------------------------
// Task API
// ------------------------------------------------------------------

export async function createTask(data: {
  user_id: string;
  conversation_id?: string;
  source_markdown: string;
  template_id?: string;
  outline: Record<string, unknown>;
  design_spec?: string;
  spec_lock?: string;
  total_pages?: number;
  pages?: Array<{ type: string; title: string }>;
}): Promise<{ task_id: string; status: string; total_pages: number }> {
  return fetchJSON(`${API_BASE}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getTaskStatus(taskId: string): Promise<TaskProgress> {
  return fetchJSON(`${API_BASE}/tasks/${taskId}`);
}

export function getPageSvgUrl(taskId: string, pageNum: number): string {
  return `${API_BASE}/tasks/${taskId}/pages/${pageNum}/svg`;
}

export function getDownloadUrl(taskId: string): string {
  return `${API_BASE}/tasks/${taskId}/download`;
}

/**
 * Authenticated PPTX download — fetches the file with the JWT token
 * and triggers a browser save-as dialog.
 */
export async function downloadPptx(taskId: string, filename?: string): Promise<void> {
  const res = await fetch(getDownloadUrl(taskId), {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Download failed ${res.status}: ${text}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'presentation.pptx';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Authenticated SVG page fetch for the slide preview component.
 */
export async function fetchPageSvg(taskId: string, pageNum: number): Promise<string> {
  const res = await fetch(getPageSvgUrl(taskId, pageNum), {
    headers: authHeaders(),
  });
  if (!res.ok) {
    return '';
  }
  return res.text();
}

// ------------------------------------------------------------------
// Convert API
// ------------------------------------------------------------------

export async function convertDocument(file: File): Promise<ConvertResult> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/convert`, {
    method: 'POST',
    body: formData,
    headers: authHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Conversion failed: ${text}`);
  }
  return res.json();
}
