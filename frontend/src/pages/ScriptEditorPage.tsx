import { useNavigate, useParams } from 'react-router-dom';

export default function ScriptEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <div className="editor-page">
      <header style={{ padding: '1rem' }}>
        <button onClick={() => navigate('/')}>← Back</button>
        <span style={{ marginLeft: '1rem' }}>
          {id ? `Script #${id}` : 'New script'}
        </span>
      </header>
      <main style={{ padding: '1rem' }}>
        <p>Script editor — coming in Step 10</p>
      </main>
    </div>
  );
}
