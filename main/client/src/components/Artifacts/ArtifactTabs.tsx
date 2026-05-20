import { useRef, useEffect, useCallback, lazy, Suspense, useMemo } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import type { SandpackPreviewRef } from '@codesandbox/sandpack-react/unstyled';
import type { editor } from 'monaco-editor';
import type { Artifact } from '~/common';
import { useCodeState } from '~/Providers/EditorContext';
import useArtifactProps from '~/hooks/Artifacts/useArtifactProps';
import { ArtifactCodeEditor } from './ArtifactCodeEditor';
import { useGetStartupConfig } from '~/data-provider';
import { ArtifactPreview } from './ArtifactPreview';
import { TOOL_ARTIFACT_TYPES } from '~/utils/artifacts';
import { createTask } from '~/utils/pptApi';

/* PPT Engine components — lazy-loaded to avoid bloating the main bundle
 * for users who never trigger PPT artifacts. */
const PPTOutlineEditor = lazy(() => import('./PPTOutlineEditor'));
const PPTTaskProgress = lazy(() => import('./PPTTaskProgress'));
const PPTSlidePreview = lazy(() => import('./PPTSlidePreview'));

const PPT_TYPES: ReadonlySet<string> = new Set([
  TOOL_ARTIFACT_TYPES.PPT_OUTLINE,
  TOOL_ARTIFACT_TYPES.PPT_PROGRESS,
  TOOL_ARTIFACT_TYPES.PPT_PREVIEW,
]);

function isPPTArtifact(type: string | undefined): boolean {
  return type != null && PPT_TYPES.has(type);
}

/**
 * Render the correct PPT component based on the artifact type.
 * Content is expected to be a JSON string that the component parses.
 */
function PPTContent({ artifact }: { artifact: Artifact }) {
  const content = artifact.content ?? '{}';
  const type = artifact.type ?? '';

  const parsed = useMemo(() => {
    try {
      return JSON.parse(content);
    } catch {
      return {};
    }
  }, [content]);

  const handleOutlineConfirm = useCallback(
    async (data: {
      outline: { title: string; pages: Array<{ type: string; title: string; points: string[] }> };
      template_id: string;
    }) => {
      try {
        const pagesPayload = data.outline.pages.map((p) => ({
          type: p.type,
          title: p.title,
        }));

        const result = await createTask({
          user_id: 'local-user', // Will be replaced by real auth in production
          source_markdown: parsed.source_markdown || '',
          outline: data.outline,
          template_id: data.template_id,
          pages: pagesPayload,
        });

        console.log('[PPT] Task created:', result);

        // Dispatch event so parent/chat components can show progress artifact
        window.dispatchEvent(
          new CustomEvent('ppt:task-created', {
            detail: {
              task_id: result.task_id,
              total_pages: result.total_pages,
            },
          }),
        );
      } catch (err) {
        console.error('[PPT] Failed to create task:', err);
        window.dispatchEvent(
          new CustomEvent('ppt:task-error', {
            detail: { error: err instanceof Error ? err.message : String(err) },
          }),
        );
      }
    },
    [parsed],
  );

  return (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent" />
        </div>
      }
    >
      {type === TOOL_ARTIFACT_TYPES.PPT_OUTLINE && (
        <PPTOutlineEditor
          outline={parsed}
          onConfirm={handleOutlineConfirm}
        />
      )}
      {type === TOOL_ARTIFACT_TYPES.PPT_PROGRESS && (
        <PPTTaskProgress taskId={parsed.task_id || ''} />
      )}
      {type === TOOL_ARTIFACT_TYPES.PPT_PREVIEW && (
        <PPTSlidePreview taskId={parsed.task_id || ''} />
      )}
    </Suspense>
  );
}

export default function ArtifactTabs({
  artifact,
  previewRef,
  isSharedConvo,
}: {
  artifact: Artifact;
  previewRef: React.MutableRefObject<SandpackPreviewRef>;
  isSharedConvo?: boolean;
}) {
  const { currentCode, setCurrentCode } = useCodeState();
  const { data: startupConfig } = useGetStartupConfig();
  const monacoRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const lastIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (artifact.id !== lastIdRef.current) {
      setCurrentCode(undefined);
    }
    lastIdRef.current = artifact.id;
  }, [setCurrentCode, artifact.id]);

  const { files, fileKey, template, sharedProps } = useArtifactProps({ artifact });

  /* PPT artifacts bypass the Sandpack code/preview split entirely.
   * They render a dedicated React component that fills the full panel. */
  if (isPPTArtifact(artifact.type)) {
    return (
      <div className="flex h-full w-full flex-col">
        <Tabs.Content
          value="preview"
          className="h-full w-full flex-grow overflow-hidden"
          tabIndex={-1}
        >
          <PPTContent artifact={artifact} />
        </Tabs.Content>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col">
      <Tabs.Content
        value="code"
        id="artifacts-code"
        className="h-full w-full flex-grow overflow-auto"
        tabIndex={-1}
      >
        <ArtifactCodeEditor artifact={artifact} monacoRef={monacoRef} readOnly={isSharedConvo} />
      </Tabs.Content>

      <Tabs.Content
        value="preview"
        className="h-full w-full flex-grow overflow-hidden"
        tabIndex={-1}
      >
        <ArtifactPreview
          files={files}
          fileKey={fileKey}
          template={template}
          previewRef={previewRef}
          sharedProps={sharedProps}
          currentCode={currentCode}
          startupConfig={startupConfig}
        />
      </Tabs.Content>
    </div>
  );
}
