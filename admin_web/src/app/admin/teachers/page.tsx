'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Teacher = {
  teacher_id: string;
  user_id: string;
  full_name: string;
  phone: string | null;
  designation: string | null;
  employee_code: string;
  qualification: string | null;
  specialization: string | null;
  gender: string | null;
  age: number | null;
  school_college: string | null;
  status: 'active' | 'inactive' | 'suspended' | string;
  created_at: string | null;
  assignment_count: number;
};

type StreamValue = 'science' | 'commerce' | '';

function formatDateTime(value: string | null): string {
  if (!value) {
    return '-';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '-';
  }
  return parsed.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function statusBadgeColor(status: string): string {
  if (status === 'active') return '#dcfce7';
  if (status === 'inactive') return '#fef3c7';
  if (status === 'suspended') return '#fee2e2';
  return '#e2e8f0';
}

function titleCase(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function AdminTeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [classLevel, setClassLevel] = useState('');
  const [stream, setStream] = useState<StreamValue>('');
  const [status, setStatus] = useState('');

  async function load(options?: {
    search?: string;
    classLevel?: string;
    stream?: StreamValue;
    status?: string;
    initial?: boolean;
  }) {
    const nextSearch = options?.search ?? search;
    const nextClassLevel = options?.classLevel ?? classLevel;
    const nextStream = options?.stream ?? stream;
    const nextStatus = options?.status ?? status;

    if (options?.initial) {
      setLoading(true);
    } else {
      setFetching(true);
    }

    setError(null);
    try {
      const params = new URLSearchParams({
        limit: '100',
        offset: '0',
      });

      if (nextSearch.trim()) {
        params.set('search', nextSearch.trim());
      }
      if (nextClassLevel) {
        params.set('class_level', nextClassLevel);
      }
      if ((nextClassLevel === '11' || nextClassLevel === '12') && nextStream) {
        params.set('stream', nextStream);
      }
      if (nextStatus) {
        params.set('status', nextStatus);
      }

      const response = await apiRequest<{ items: Teacher[] }>(`/api/v1/admin/teachers?${params.toString()}`);
      setTeachers(response.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teachers');
    } finally {
      setLoading(false);
      setFetching(false);
    }
  }

  useEffect(() => {
    void load({
      search: '',
      classLevel: '',
      stream: '',
      status: '',
      initial: true,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = useMemo(() => {
    const active = teachers.filter((teacher) => teacher.status === 'active').length;
    const inactive = teachers.filter((teacher) => teacher.status === 'inactive').length;
    const suspended = teachers.filter((teacher) => teacher.status === 'suspended').length;
    return {
      total: teachers.length,
      active,
      inactive,
      suspended,
    };
  }, [teachers]);

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Teachers</h1>
      <p className="muted" style={{ marginTop: -4 }}>
        Registered teacher directory with class/stream tracking support for lecture scheduling.
      </p>

      {error ? <p style={{ color: '#dc2626', fontWeight: 600 }}>{error}</p> : null}

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Total Teachers</h3>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{summary.total}</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Active</h3>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#166534' }}>{summary.active}</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Inactive</h3>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#92400e' }}>{summary.inactive}</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Suspended</h3>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#991b1b' }}>{summary.suspended}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Filter Teachers</h3>
        <div className="grid" style={{ marginBottom: 10 }}>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Search</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name, phone, employee code"
            />
          </label>

          <label className="field" style={{ marginBottom: 0 }}>
            <span>Class</span>
            <select
              value={classLevel}
              onChange={(event) => {
                const nextClass = event.target.value;
                setClassLevel(nextClass);
                if (nextClass !== '11' && nextClass !== '12') {
                  setStream('');
                }
              }}
            >
              <option value="">All classes</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>

          <label className="field" style={{ marginBottom: 0 }}>
            <span>Stream</span>
            <select
              value={stream}
              onChange={(event) => setStream(event.target.value as StreamValue)}
              disabled={classLevel !== '11' && classLevel !== '12'}
            >
              <option value="">All streams</option>
              <option value="science">Science</option>
              <option value="commerce">Commerce</option>
            </select>
          </label>

          <label className="field" style={{ marginBottom: 0 }}>
            <span>Status</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="btn"
            type="button"
            disabled={fetching}
            onClick={() => void load()}
          >
            {fetching ? 'Applying...' : 'Apply Filters'}
          </button>
          <button
            className="btn"
            type="button"
            style={{ background: '#334155' }}
            onClick={() => {
              setSearch('');
              setClassLevel('');
              setStream('');
              setStatus('');
              void load({ search: '', classLevel: '', stream: '', status: '' });
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Teacher Directory</h3>
        {loading ? (
          <p>Loading teachers...</p>
        ) : (
          <div style={{ overflow: 'auto' }}>
            <table className="table" style={{ minWidth: 980 }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Contact</th>
                  <th>Designation</th>
                  <th>Qualification</th>
                  <th>Specialization</th>
                  <th>Assignments</th>
                  <th>Status</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {teachers.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="muted">
                      No teachers found for selected filters.
                    </td>
                  </tr>
                ) : (
                  teachers.map((teacher) => (
                    <tr key={teacher.teacher_id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{teacher.full_name}</div>
                        <div className="muted" style={{ fontSize: 12 }}>
                          {teacher.employee_code}
                        </div>
                      </td>
                      <td>{teacher.phone ?? '-'}</td>
                      <td>{teacher.designation ?? '-'}</td>
                      <td>{teacher.qualification ?? '-'}</td>
                      <td>{teacher.specialization ?? '-'}</td>
                      <td>{teacher.assignment_count}</td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            textTransform: 'capitalize',
                            background: statusBadgeColor(teacher.status),
                            color: '#0f172a',
                          }}
                        >
                          {titleCase(teacher.status)}
                        </span>
                      </td>
                      <td>{formatDateTime(teacher.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
