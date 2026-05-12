'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Student = {
  student_id: string;
  user_id: string;
  full_name: string;
  phone: string | null;
  status: 'active' | 'inactive' | 'suspended' | string;
  class_name: string | null;
  stream: string | null;
  parent_contact_number: string | null;
  admission_no: string;
};

type StudentSummary = {
  total_students: number;
  active_students: number;
  inactive_students: number;
  suspended_students: number;
};

function nextStatus(current: string): 'active' | 'inactive' {
  return current === 'active' ? 'inactive' : 'active';
}

export default function AdminStudentCountPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [summary, setSummary] = useState<StudentSummary>({
    total_students: 0,
    active_students: 0,
    inactive_students: 0,
    suspended_students: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [statusUpdatingUserId, setStatusUpdatingUserId] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive' | 'suspended'>('all');
  const [classFilter, setClassFilter] = useState<'all' | '10' | '11' | '12'>('all');

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: '100',
        offset: '0',
      });
      if (search.trim()) {
        params.set('search', search.trim());
      }
      if (statusFilter !== 'all') {
        params.set('status', statusFilter);
      }
      if (classFilter !== 'all') {
        params.set('class_level', classFilter);
      }

      const [summaryRes, studentRes] = await Promise.all([
        apiRequest<StudentSummary>('/api/v1/admin/students/summary'),
        apiRequest<{ items: Student[] }>(`/api/v1/admin/students?${params.toString()}`),
      ]);

      setSummary(summaryRes);
      setStudents(studentRes.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student count page');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const statusCounts = useMemo(() => {
    return {
      total: summary.total_students,
      active: summary.active_students,
      inactive: summary.inactive_students,
      suspended: summary.suspended_students,
    };
  }, [summary]);

  async function updateStudentStatus(student: Student) {
    const targetStatus = nextStatus(student.status);
    setStatusUpdatingUserId(student.user_id);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/api/v1/admin/students/${student.user_id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: targetStatus }),
      });
      setSuccess(`${student.full_name} is now ${targetStatus}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update student status');
    } finally {
      setStatusUpdatingUserId(null);
    }
  }

  return (
    <section className="student-admin-theme">
      <h1 style={{ marginTop: 0, marginBottom: 6 }}>Student Count</h1>
      <p className="muted" style={{ marginTop: 0, marginBottom: 14 }}>
        Total, active and inactive student tracking with class-based filtering and direct status controls.
      </p>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
      {success ? <p style={{ color: '#166534' }}>{success}</p> : null}

      <div className="grid" style={{ marginBottom: 14 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Total Students</h3>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{statusCounts.total}</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Active</h3>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#166534' }}>{statusCounts.active}</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Inactive</h3>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#b91c1c' }}>{statusCounts.inactive}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <h3 style={{ marginTop: 0 }}>Filters</h3>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          <label className="field">
            <span>Search (name/mobile/admission)</span>
            <input value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
          <label className="field">
            <span>Status</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive' | 'suspended')}>
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>
          <label className="field">
            <span>Class</span>
            <select value={classFilter} onChange={(e) => setClassFilter(e.target.value as 'all' | '10' | '11' | '12')}>
              <option value="all">All</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>
        </div>
        <button className="btn" type="button" onClick={() => void load()}>
          Apply Filters
        </button>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Student List</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Class</th>
                <th>Stream</th>
                <th>Contact</th>
                <th>Parent</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.student_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{student.full_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{student.admission_no}</div>
                  </td>
                  <td>{student.class_name ?? '-'}</td>
                  <td>{student.stream ?? '-'}</td>
                  <td>{student.phone ?? '-'}</td>
                  <td>{student.parent_contact_number ?? '-'}</td>
                  <td><span className="badge">{student.status}</span></td>
                  <td>
                    <button
                      className="btn"
                      type="button"
                      onClick={() => void updateStudentStatus(student)}
                      disabled={statusUpdatingUserId === student.user_id}
                    >
                      {statusUpdatingUserId === student.user_id
                        ? 'Updating...'
                        : student.status === 'active'
                          ? 'Deactivate'
                          : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
              {students.length === 0 ? (
                <tr>
                  <td colSpan={7} className="muted">No students found for selected filters.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
