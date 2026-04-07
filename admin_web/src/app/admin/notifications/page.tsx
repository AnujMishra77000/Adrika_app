'use client';

import { FormEvent, useState } from 'react';

import { apiRequest } from '@/lib/api';

export default function AdminNotificationsPage() {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [notificationType, setNotificationType] = useState('system');
  const [targetsJson, setTargetsJson] = useState('[{"target_type":"all","target_id":"all"}]');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function sendNotification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    try {
      const targets = JSON.parse(targetsJson);
      const response = await apiRequest<{ recipient_count: number }>('/api/v1/admin/notifications', {
        method: 'POST',
        body: JSON.stringify({
          title,
          body,
          notification_type: notificationType,
          targets,
        }),
      });
      setResult(`Notification queued for ${response.recipient_count} users`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send notification');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Notifications</h1>
      <div className="card" style={{ maxWidth: 760 }}>
        <h3 style={{ marginTop: 0 }}>Broadcast Notification</h3>
        <form onSubmit={sendNotification}>
          <label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} required /></label>
          <label className="field"><span>Body</span><textarea rows={4} value={body} onChange={(e) => setBody(e.target.value)} required /></label>
          <label className="field">
            <span>Type</span>
            <select value={notificationType} onChange={(e) => setNotificationType(e.target.value)}>
              <option value="system">System</option>
              <option value="notice">Notice</option>
              <option value="homework">Homework</option>
              <option value="test">Test</option>
              <option value="result">Result</option>
              <option value="doubt">Doubt</option>
            </select>
          </label>
          <label className="field"><span>Targets (JSON)</span><textarea rows={3} value={targetsJson} onChange={(e) => setTargetsJson(e.target.value)} /></label>
          {result ? <p style={{ color: '#166534' }}>{result}</p> : null}
          {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
          <button className="btn" type="submit">Send</button>
        </form>
      </div>
    </section>
  );
}
