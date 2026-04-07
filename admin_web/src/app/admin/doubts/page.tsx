'use client';

import { useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Doubt = {
  id: string;
  student_name: string;
  topic: string;
  status: string;
  priority: string;
  created_at: string;
};

const STATUSES = ['open', 'in_progress', 'resolved', 'closed'];

export default function AdminDoubtsPage() {
  const [items, setItems] = useState<Doubt[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const response = await apiRequest<{ items: Doubt[] }>('/api/v1/admin/doubts?limit=100&offset=0');
      setItems(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load doubts');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function updateStatus(doubtId: string, status: string) {
    try {
      await apiRequest(`/api/v1/admin/doubts/${doubtId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update doubt');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Doubts</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Doubt Queue</h3>
        <table className="table">
          <thead><tr><th>Student</th><th>Topic</th><th>Status</th><th>Priority</th><th>Update</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.student_name}</td>
                <td>{item.topic}</td>
                <td><span className="badge">{item.status}</span></td>
                <td>{item.priority}</td>
                <td>
                  <select value={item.status} onChange={(e) => updateStatus(item.id, e.target.value)}>
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
