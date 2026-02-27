import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import type { ScriptSummary } from '../api/types';
import { useAuth } from '../contexts/AuthContext';

function relativeTime(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ScriptCatalogPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [scripts, setScripts] = useState<ScriptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const isEditor = user?.roles.includes('editor') ?? false;

  useEffect(() => {
    apiFetch<ScriptSummary[]>('/api/scripts')
      .then(setScripts)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : 'Failed to load scripts'),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="catalog-page">
      <header className="catalog-header">
        <h1>code.ved</h1>
        <div className="catalog-actions">
          <span className="catalog-username">{user?.username}</span>
          {isEditor && (
            <button onClick={() => navigate('/editor/new')}>+ New script</button>
          )}
          <button onClick={logout}>Sign out</button>
        </div>
      </header>

      <main className="catalog-main">
        {loading && <p className="catalog-status">Loading…</p>}
        {error && <p className="catalog-status catalog-error">{error}</p>}
        {!loading && !error && scripts.length === 0 && (
          <p className="catalog-status">
            No scripts yet.
            {isEditor && ' Click "+ New script" to create one.'}
          </p>
        )}

        {scripts.length > 0 && (
          <table className="catalog-table">
            <thead>
              <tr>
                <th className="col-num">#</th>
                <th className="col-name">Name</th>
                <th className="col-version">Version</th>
                <th className="col-run">Last run</th>
              </tr>
            </thead>
            <tbody>
              {scripts.map((s) => {
                const tooltip = [
                  s.descriptive_name,
                  `v${s.major}.${s.minor}`,
                  s.last_run_at
                    ? `Last run: ${new Date(s.last_run_at).toLocaleString()} (exit ${s.last_run_exit_code})`
                    : 'Never run',
                ].join('\n');

                return (
                  <tr
                    key={s.id}
                    className="catalog-row"
                    title={tooltip}
                    onClick={() => navigate(`/editor/${s.id}`)}
                  >
                    <td className="col-num">{s.ordering_number}</td>
                    <td className="col-name">{s.descriptive_name}</td>
                    <td className="col-version">
                      v{s.major}.{s.minor}
                    </td>
                    <td className="col-run">
                      {s.last_run_at == null ? (
                        <span className="run-never">Never</span>
                      ) : s.last_run_exit_code === 0 ? (
                        <>
                          <span className="run-badge run-ok">OK</span>{' '}
                          {relativeTime(s.last_run_at)}
                        </>
                      ) : (
                        <>
                          <span className="run-badge run-fail">Fail</span>{' '}
                          {relativeTime(s.last_run_at)}
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}
