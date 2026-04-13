'use client';

import { useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type AuditItem = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  ip_address: string | null;
  created_at: string;
};

export default function AdminAuditLogsPage() {
  const [items, setItems] = useState<AuditItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await apiRequest<{ items: AuditItem[] }>('/api/v1/admin/audit-logs?limit=100&offset=0');
        setItems(response.items);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load audit logs');
      }
    }

    void load();
  }, []);

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Audit Logs</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Entity ID</th>
              <th>Actor</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{new Date(item.created_at).toLocaleString()}</td>
                <td>{item.action}</td>
                <td>{item.entity_type}</td>
                <td>{item.entity_id}</td>
                <td>{item.actor_user_id ?? '-'}</td>
                <td>{item.ip_address ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
