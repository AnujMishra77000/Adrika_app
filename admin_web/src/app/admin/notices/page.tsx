'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Notice = { id: string; title: string; status: string; priority: number; publish_at: string | null };

export default function AdminNoticesPage() {
  const [items, setItems] = useState<Notice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [priority, setPriority] = useState('0');
  const [targetsJson, setTargetsJson] = useState('[{"target_type":"all","target_id":"all"}]');

  async function load() {
    setLoading(true);
    try {
      const response = await apiRequest<{ items: Notice[] }>('/api/v1/admin/notices?limit=50&offset=0');
      setItems(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notices');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createNotice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const targets = JSON.parse(targetsJson);
      await apiRequest('/api/v1/admin/notices', {
        method: 'POST',
        body: JSON.stringify({
          title,
          body,
          priority: Number(priority),
          targets,
        }),
      });
      setTitle('');
      setBody('');
      setPriority('0');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create notice');
    }
  }

  async function publishNotice(noticeId: string) {
    try {
      await apiRequest(`/api/v1/admin/notices/${noticeId}/publish`, { method: 'POST' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish notice');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Notices</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create Notice</h3>
        <form onSubmit={createNotice}>
          <label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} required /></label>
          <label className="field"><span>Body</span><textarea rows={4} value={body} onChange={(e) => setBody(e.target.value)} required /></label>
          <label className="field"><span>Priority</span><input value={priority} onChange={(e) => setPriority(e.target.value)} /></label>
          <label className="field"><span>Targets (JSON)</span><textarea rows={3} value={targetsJson} onChange={(e) => setTargetsJson(e.target.value)} /></label>
          <button className="btn" type="submit">Create Notice</button>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Notice List</h3>
        {loading ? <p>Loading...</p> : (
          <table className="table">
            <thead><tr><th>Title</th><th>Status</th><th>Priority</th><th>Actions</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td><span className="badge">{item.status}</span></td>
                  <td>{item.priority}</td>
                  <td>
                    <button className="btn" style={{ background: '#16a34a' }} onClick={() => publishNotice(item.id)}>Publish</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
