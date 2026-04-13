'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

type DoubtItem = {
  id: string;
  student_id: string;
  student_name: string;
  teacher_id?: string | null;
  teacher_name?: string | null;
  lecture_id?: string | null;
  lecture_topic?: string | null;
  subject_id: string;
  topic: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at?: string;
};

type DoubtMessage = {
  id: string;
  sender_user_id?: string | null;
  sender_name?: string;
  message: string;
  created_at: string;
};

type DoubtConversation = {
  doubt: {
    id: string;
    student_id: string;
    student_name: string;
    teacher_id?: string | null;
    teacher_name?: string | null;
    lecture_id?: string | null;
    lecture_topic?: string | null;
    subject_id: string;
    topic: string;
    description: string;
    status: string;
    priority: string;
    created_at: string;
    updated_at?: string;
  };
  messages: DoubtMessage[];
};

const STATUSES = ['open', 'in_progress', 'resolved', 'closed'];

function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString();
}

export default function AdminDoubtsPage() {
  const [items, setItems] = useState<DoubtItem[]>([]);
  const [selectedDoubtId, setSelectedDoubtId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<DoubtConversation | null>(null);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedItem = useMemo(
    () => items.find((item) => item.id == selectedDoubtId) ?? null,
    [items, selectedDoubtId],
  );

  async function loadQueue() {
    try {
      const response = await apiRequest<{ items: DoubtItem[] }>('/api/v1/admin/doubts?limit=100&offset=0');
      setItems(response.items ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load doubts');
    }
  }

  async function loadConversation(doubtId: string, silent = false) {
    if (!silent) {
      setLoadingConversation(true);
    }

    try {
      const response = await apiRequest<DoubtConversation>(`/api/v1/admin/doubts/${doubtId}/conversation`);
      setConversation(response);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setLoadingConversation(false);
    }
  }

  useEffect(() => {
    void loadQueue();
  }, []);

  useEffect(() => {
    if (!selectedDoubtId) {
      setConversation(null);
      return;
    }
    void loadConversation(selectedDoubtId);
  }, [selectedDoubtId]);

  useEffect(() => {
    if (!selectedDoubtId) return;

    const timer = window.setInterval(() => {
      void loadConversation(selectedDoubtId, true);
    }, 8000);

    return () => window.clearInterval(timer);
  }, [selectedDoubtId]);

  async function updateStatus(doubtId: string, status: string) {
    try {
      await apiRequest(`/api/v1/admin/doubts/${doubtId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      await loadQueue();
      if (selectedDoubtId === doubtId) {
        await loadConversation(doubtId, true);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update doubt status');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Doubt Conversations</h1>
      <p style={{ marginTop: 0, color: '#6b7280' }}>
        Track student-teacher doubt threads in real time with full conversation visibility.
      </p>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(420px, 1fr) minmax(460px, 1.2fr)',
          gap: 16,
          alignItems: 'start',
        }}
      >
        <div className="card" style={{ overflowX: 'auto' }}>
          <h3 style={{ marginTop: 0 }}>Queue</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Topic</th>
                <th>Lecture</th>
                <th>Status</th>
                <th>Update</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} style={{ background: selectedDoubtId === item.id ? '#f3f4ff' : undefined }}>
                  <td>{item.student_name}</td>
                  <td>{item.topic}</td>
                  <td>{item.lecture_topic || '—'}</td>
                  <td>
                    <span className="badge">{item.status}</span>
                  </td>
                  <td>
                    <select value={item.status} onChange={(e) => void updateStatus(item.id, e.target.value)}>
                      {STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => setSelectedDoubtId(item.id)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: '#6b7280' }}>
                    No doubts found.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Conversation</h3>
          {!selectedDoubtId ? (
            <p style={{ color: '#6b7280' }}>Select a doubt from queue to open the chat transcript.</p>
          ) : loadingConversation && !conversation ? (
            <p>Loading conversation...</p>
          ) : conversation ? (
            <>
              <div
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: 12,
                  padding: 12,
                  marginBottom: 12,
                  background: '#fafafa',
                }}
              >
                <div style={{ display: 'grid', gap: 6 }}>
                  <div>
                    <strong>Student:</strong> {conversation.doubt.student_name}
                  </div>
                  <div>
                    <strong>Teacher:</strong> {conversation.doubt.teacher_name || selectedItem?.teacher_name || 'Unassigned'}
                  </div>
                  <div>
                    <strong>Topic:</strong> {conversation.doubt.topic}
                  </div>
                  <div>
                    <strong>Lecture:</strong> {conversation.doubt.lecture_topic || '—'}
                  </div>
                  <div>
                    <strong>Status:</strong> <span className="badge">{conversation.doubt.status}</span>
                  </div>
                  <div>
                    <strong>Description:</strong> {conversation.doubt.description}
                  </div>
                  <div>
                    <strong>Opened:</strong> {formatDateTime(conversation.doubt.created_at)}
                  </div>
                </div>
              </div>

              <div
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: 12,
                  maxHeight: 420,
                  overflowY: 'auto',
                  padding: 12,
                  background: '#ffffff',
                }}
              >
                {conversation.messages.length === 0 ? (
                  <p style={{ color: '#6b7280' }}>No messages yet.</p>
                ) : (
                  <div style={{ display: 'grid', gap: 10 }}>
                    {conversation.messages.map((msg) => (
                      <div
                        key={msg.id}
                        style={{
                          border: '1px solid #e5e7eb',
                          borderRadius: 10,
                          padding: 10,
                          background: '#f9fafb',
                        }}
                      >
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>{msg.sender_name || 'Unknown'}</div>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.message}</div>
                        <div style={{ marginTop: 6, fontSize: 12, color: '#6b7280' }}>{formatDateTime(msg.created_at)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <p style={{ color: '#6b7280' }}>Conversation data unavailable.</p>
          )}
        </div>
      </div>
    </section>
  );
}
