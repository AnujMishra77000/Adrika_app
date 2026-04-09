'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

type RegistrationRequestItem = {
  request_id: string;
  status: string;
  requested_role: 'student' | 'teacher';
  submitted_at: string;
  user: {
    id: string;
    full_name: string;
    phone: string | null;
    email: string | null;
    status: string;
  };
  student_profile?: {
    class_name: string | null;
    stream: string | null;
    parent_contact_number: string | null;
    address: string | null;
    school_details: string | null;
    photo_url: string | null;
  };
  teacher_profile?: {
    age: number | null;
    gender: string | null;
    qualification: string | null;
    specialization: string | null;
    school_college: string | null;
    address: string | null;
    photo_url: string | null;
  };
};

type RoleFilter = 'all' | 'student' | 'teacher';

export default function AdminRegistrationsPage() {
  const [items, setItems] = useState<RegistrationRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [role, setRole] = useState<RoleFilter>('all');
  const [busyRequestId, setBusyRequestId] = useState<string | null>(null);

  const endpoint = useMemo(
    () => `/api/v1/admin/registration-requests?status=pending&role=${role}&limit=100&offset=0`,
    [role],
  );

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<{ items: RegistrationRequestItem[] }>(endpoint);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load registration requests');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 15000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  async function decide(requestId: string, status: 'approved' | 'rejected') {
    const note = window.prompt(`Optional note for ${status}:`) ?? undefined;
    setBusyRequestId(requestId);
    setError(null);
    try {
      await apiRequest(`/api/v1/admin/registration-requests/${requestId}/decision`, {
        method: 'POST',
        body: JSON.stringify({ status, note: note?.trim() || undefined }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to mark request as ${status}`);
    } finally {
      setBusyRequestId(null);
    }
  }

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h1 style={{ marginTop: 0 }}>Registration Approvals</h1>
        <label className="field" style={{ marginBottom: 0, minWidth: 200 }}>
          <span>Role Filter</span>
          <select value={role} onChange={(event) => setRole(event.target.value as RoleFilter)}>
            <option value="all">All</option>
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
          </select>
        </label>
      </div>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card" style={{ marginTop: 12 }}>
        {loading ? (
          <p>Loading pending registration requests...</p>
        ) : items.length === 0 ? (
          <p className="muted">No pending registrations for the selected role.</p>
        ) : (
          <div style={{ display: 'grid', gap: 12 }}>
            {items.map((item) => (
              <article
                key={item.request_id}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 12,
                  padding: 14,
                  display: 'grid',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <div>
                    <strong>{item.user.full_name}</strong>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {item.requested_role.toUpperCase()} • {item.user.phone ?? '-'} • {new Date(item.submitted_at).toLocaleString()}
                    </div>
                  </div>
                  <span className="badge">{item.status}</span>
                </div>

                {item.requested_role === 'student' && item.student_profile ? (
                  <div style={{ display: 'grid', gap: 4, fontSize: 14 }}>
                    <div><strong>Class:</strong> {item.student_profile.class_name ?? '-'}</div>
                    <div><strong>Stream:</strong> {item.student_profile.stream ?? '-'}</div>
                    <div><strong>Parent Contact:</strong> {item.student_profile.parent_contact_number ?? '-'}</div>
                    <div><strong>School:</strong> {item.student_profile.school_details ?? '-'}</div>
                    <div><strong>Address:</strong> {item.student_profile.address ?? '-'}</div>
                  </div>
                ) : null}

                {item.requested_role === 'teacher' && item.teacher_profile ? (
                  <div style={{ display: 'grid', gap: 4, fontSize: 14 }}>
                    <div><strong>Age / Gender:</strong> {item.teacher_profile.age ?? '-'} / {item.teacher_profile.gender ?? '-'}</div>
                    <div><strong>Qualification:</strong> {item.teacher_profile.qualification ?? '-'}</div>
                    <div><strong>Specialization:</strong> {item.teacher_profile.specialization ?? '-'}</div>
                    <div><strong>School / College:</strong> {item.teacher_profile.school_college ?? '-'}</div>
                    <div><strong>Address:</strong> {item.teacher_profile.address ?? '-'}</div>
                  </div>
                ) : null}

                <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                  <button
                    className="btn"
                    disabled={busyRequestId === item.request_id}
                    onClick={() => void decide(item.request_id, 'approved')}
                  >
                    Approve
                  </button>
                  <button
                    className="btn"
                    style={{ background: '#ef4444' }}
                    disabled={busyRequestId === item.request_id}
                    onClick={() => void decide(item.request_id, 'rejected')}
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
