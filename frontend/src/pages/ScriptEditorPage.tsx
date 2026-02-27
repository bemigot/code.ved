import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import type {
  CompleteResponse,
  ExecutionResult,
  ScriptDetail,
  VersionInfo,
} from '../api/types';
import { useAuth } from '../contexts/AuthContext';
import { useLanguageService } from '../hooks/useLanguageService';

// ── Status toast ──────────────────────────────────────────────────────────────

interface Status {
  text: string;
  kind: 'ok' | 'err';
}

// ── Version history panel ─────────────────────────────────────────────────────

function VersionHistory({
  scriptId,
  onClose,
}: {
  scriptId: number;
  onClose: () => void;
}) {
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<VersionInfo[]>(`/api/scripts/${scriptId}/versions`)
      .then(setVersions)
      .finally(() => setLoading(false));
  }, [scriptId]);

  return (
    <div className="version-overlay">
      <div className="version-panel">
        <div className="version-panel-header">
          <span>Version history</span>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>
        {loading ? (
          <p className="version-loading">Loading…</p>
        ) : (
          <ul className="version-list">
            {versions.map((v) => (
              <li key={v.id} className="version-item">
                <span className="version-tag">v{v.major}.{v.minor}</span>
                <span className="version-meta">
                  {v.committer} · {new Date(v.created_at).toLocaleString()}
                </span>
                <code className="version-hash">{v.git_commit_hash.slice(0, 7)}</code>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── LLM panel ─────────────────────────────────────────────────────────────────

function LLMPanel({
  scriptId,
  versionId,
  code,
  onInsert,
}: {
  scriptId: number | null;
  versionId: number | null;
  code: string;
  onInsert: (text: string) => void;
}) {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit() {
    if (!prompt.trim()) return;
    setLoading(true);
    setError('');
    setResponse('');
    try {
      const res = await apiFetch<CompleteResponse>('/api/llm/complete', {
        method: 'POST',
        body: JSON.stringify({
          script_id: scriptId,
          script_version_id: versionId,
          prompt,
          context_code: code,
        }),
      });
      setResponse(res.response_text);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'LLM error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="llm-panel">
      <div className="llm-panel-title">Ask the LLM</div>
      <textarea
        className="llm-textarea"
        placeholder="Ask something about this script…"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit();
        }}
        disabled={loading}
      />
      <button
        className="llm-send-btn"
        onClick={handleSubmit}
        disabled={loading || !prompt.trim()}
      >
        {loading ? 'Asking…' : 'Send  Ctrl+↵'}
      </button>
      {error && <p className="llm-error">{error}</p>}
      {response && (
        <div className="llm-response-area">
          <pre className="llm-response">{response}</pre>
          <button className="llm-insert-btn" onClick={() => onInsert(response)}>
            Insert into editor
          </button>
        </div>
      )}
    </div>
  );
}

// ── Output panel ──────────────────────────────────────────────────────────────

function OutputPanel({ result, error }: { result: ExecutionResult | null; error: string }) {
  if (error) return <div className="output-panel output-error">{error}</div>;
  if (!result) return <div className="output-panel output-empty">No output yet — run the script.</div>;

  const success = result.exit_code === 0;
  return (
    <div className="output-panel">
      <span className={`run-badge ${success ? 'run-ok' : 'run-fail'}`}>
        exit {result.exit_code}
      </span>
      {result.stdout && <pre className="output-stream">{result.stdout}</pre>}
      {result.stderr && (
        <pre className="output-stream output-stderr">{result.stderr}</pre>
      )}
      {!result.stdout && !result.stderr && (
        <span className="output-empty-msg">  (no output)</span>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ScriptEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isEditor = user?.roles.includes('editor') ?? false;

  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  useLanguageService(); // reserved for Phase 2 Pyright wiring

  const [code, setCode] = useState('');
  const [detail, setDetail] = useState<ScriptDetail | null>(null);
  const [loading, setLoading] = useState(!!id);
  const [loadError, setLoadError] = useState('');

  // button states
  const [saving, setSaving] = useState(false);
  const [merging, setMerging] = useState(false);
  const [running, setRunning] = useState(false);

  // feedback
  const [status, setStatus] = useState<Status | null>(null);

  // output
  const [output, setOutput] = useState<ExecutionResult | null>(null);
  const [runError, setRunError] = useState('');

  // version history
  const [showVersions, setShowVersions] = useState(false);

  // auto-dismiss status toast
  useEffect(() => {
    if (!status) return;
    const t = setTimeout(() => setStatus(null), 3000);
    return () => clearTimeout(t);
  }, [status]);

  // load existing script
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    apiFetch<ScriptDetail>(`/api/scripts/${id}`)
      .then((d) => {
        setDetail(d);
        setCode(d.content);
      })
      .catch((err) =>
        setLoadError(err instanceof ApiError ? err.message : 'Failed to load script'),
      )
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSave() {
    if (!isEditor) return;
    setSaving(true);
    try {
      if (!detail) {
        // new script
        const d = await apiFetch<ScriptDetail>('/api/scripts', {
          method: 'POST',
          body: JSON.stringify({ content: code }),
        });
        setDetail(d);
        navigate(`/editor/${d.id}`, { replace: true });
        setStatus({ text: 'Created', kind: 'ok' });
      } else {
        const d = await apiFetch<ScriptDetail>(`/api/scripts/${detail.id}`, {
          method: 'PUT',
          body: JSON.stringify({ content: code }),
        });
        setDetail(d);
        setStatus({ text: `Saved v${d.version.major}.${d.version.minor}`, kind: 'ok' });
      }
    } catch (err) {
      setStatus({
        text: err instanceof ApiError ? err.message : 'Save failed',
        kind: 'err',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleFork() {
    if (!detail || !isEditor) return;
    try {
      const d = await apiFetch<ScriptDetail>(`/api/scripts/${detail.id}/fork`, {
        method: 'POST',
      });
      navigate(`/editor/${d.id}`, { replace: true });
    } catch (err) {
      setStatus({
        text: err instanceof ApiError ? err.message : 'Fork failed',
        kind: 'err',
      });
    }
  }

  async function handleBumpMajor() {
    if (!detail || !isEditor) return;
    try {
      const d = await apiFetch<ScriptDetail>(`/api/scripts/${detail.id}/bump-major`, {
        method: 'POST',
      });
      setDetail(d);
      setStatus({ text: `Bumped to v${d.version.major}.0`, kind: 'ok' });
    } catch (err) {
      setStatus({
        text: err instanceof ApiError ? err.message : 'Bump failed',
        kind: 'err',
      });
    }
  }

  async function handleMerge() {
    if (!detail || !isEditor) return;
    setMerging(true);
    try {
      await apiFetch(`/api/scripts/${detail.id}/merge`, { method: 'POST' });
      setStatus({ text: 'Merged to prod', kind: 'ok' });
    } catch (err) {
      setStatus({
        text: err instanceof ApiError ? err.message : 'Merge failed',
        kind: 'err',
      });
    } finally {
      setMerging(false);
    }
  }

  async function handleRun() {
    if (!detail || !isEditor) return;
    setRunning(true);
    setRunError('');
    setOutput(null);
    try {
      const result = await apiFetch<ExecutionResult>(`/api/execute/${detail.id}`, {
        method: 'POST',
        body: JSON.stringify({ test_data: '' }),
      });
      setOutput(result);
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : 'Run failed');
    } finally {
      setRunning(false);
    }
  }

  function handleInsertLLM(text: string) {
    setCode(text);
    editorRef.current?.setValue(text);
  }

  // ── Keyboard shortcut: Ctrl/Cmd+S → save ────────────────────────────────────
  useEffect(() => {
    if (!isEditor) return;
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return <div className="editor-page editor-loading">Loading…</div>;
  }
  if (loadError) {
    return (
      <div className="editor-page editor-loading">
        <p style={{ color: '#f87171' }}>{loadError}</p>
        <button onClick={() => navigate('/')}>← Back</button>
      </div>
    );
  }

  const title = detail?.descriptive_name ?? 'New script';
  const versionLabel = detail
    ? `v${detail.version.major}.${detail.version.minor}`
    : null;

  return (
    <div className="editor-page">
      {/* ── Header ── */}
      <header className="editor-header">
        <button className="editor-back-btn" onClick={() => navigate('/')}>←</button>

        <span className="editor-title" title={title}>{title}</span>

        {versionLabel && (
          <button
            className="version-badge-btn"
            onClick={() => setShowVersions((v) => !v)}
            title="Show version history"
          >
            {versionLabel}
          </button>
        )}

        {status && (
          <span className={`editor-status ${status.kind === 'err' ? 'editor-status-err' : 'editor-status-ok'}`}>
            {status.text}
          </span>
        )}

        <div className="editor-spacer" />

        {isEditor && (
          <>
            <button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            {detail && (
              <>
                <button onClick={handleFork} title="Fork to a new script">Fork</button>
                <button onClick={handleBumpMajor} title="Increment major version">Bump major</button>
                <button onClick={handleMerge} disabled={merging} title="Merge ed1 → prod">
                  {merging ? 'Merging…' : 'Merge'}
                </button>
                <button
                  className="run-btn"
                  onClick={handleRun}
                  disabled={running}
                  title="Run from prod branch"
                >
                  {running ? 'Running…' : '▶ Run'}
                </button>
              </>
            )}
          </>
        )}
      </header>

      {/* ── Body ── */}
      <div className="editor-body">
        {/* Monaco */}
        <div className="editor-pane">
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="vs-dark"
            value={code}
            onChange={(val) => setCode(val ?? '')}
            onMount={(editorInstance) => {
              editorRef.current = editorInstance;
            }}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              tabSize: 4,
              insertSpaces: true,
              wordWrap: 'off',
            }}
          />
        </div>

        {/* LLM sidebar */}
        <LLMPanel
          scriptId={detail?.id ?? null}
          versionId={detail?.version.id ?? null}
          code={code}
          onInsert={handleInsertLLM}
        />
      </div>

      {/* ── Output ── */}
      <OutputPanel result={output} error={runError} />

      {/* ── Version history overlay ── */}
      {showVersions && detail && (
        <VersionHistory
          scriptId={detail.id}
          onClose={() => setShowVersions(false)}
        />
      )}
    </div>
  );
}
