import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ScriptCatalogPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="catalog-page">
      <header className="catalog-header">
        <h1>code.ved</h1>
        <div className="catalog-actions">
          <span className="catalog-username">{user?.username}</span>
          {user?.roles.includes('editor') && (
            <button onClick={() => navigate('/editor/new')}>+ New script</button>
          )}
          <button onClick={logout}>Sign out</button>
        </div>
      </header>
      <main style={{ padding: '1rem' }}>
        <p>Script catalog — coming in Step 9</p>
      </main>
    </div>
  );
}
