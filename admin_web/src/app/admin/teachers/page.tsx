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
  teaching_scope: string | null;
  status: 'active' | 'inactive' | 'suspended' | string;
  created_at: string | null;
  assignment_count: number;
  hourly_salary_rate?: number;
  current_password?: string | null;
};

type StreamValue = 'science' | 'commerce' | '';
type TeacherAction = 'active' | 'inactive' | 'suspended' | 'reset_password' | 'salary_slip' | 'delete';

type SalaryLedgerItem = {
  ledger_id: string;
  teacher_id: string;
  teacher_name: string;
  employee_code: string;
  class_level: number;
  stream: string;
  topic: string;
  lecture_duration_minutes: number;
  hourly_rate: number;
  amount: number;
  attendance_date: string;
  completed_at: string;
};

type SalaryLedgerResponse = {
  items: SalaryLedgerItem[];
  summary: {
    total_amount: number;
    lecture_count: number;
    teacher_count: number;
  };
};

const TEACHING_SCOPES = [
  { value: '6-common', label: '6th' },
  { value: '7-common', label: '7th' },
  { value: '8-common', label: '8th' },
  { value: '9-common', label: '9th' },
  { value: '10-common', label: '10th' },
  { value: '11-science', label: '11th Science' },
  { value: '11-commerce', label: '11th Commerce' },
  { value: '12-science', label: '12th Science' },
  { value: '12-commerce', label: '12th Commerce' },
];

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

function formatInr(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value || 0);
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

function formatTeachingScope(value: string | null): string {
  if (!value) return '-';
  const parts = value
    .split(',')
    .map((raw) => raw.trim())
    .filter(Boolean)
    .map((token) => {
      const [cls, stream] = token.split('-');
      if (!cls || !stream) return token;
      if (stream === 'common') return `${cls}th`;
      return `${cls}th ${stream.charAt(0).toUpperCase()}${stream.slice(1)}`;
    });
  return parts.join(', ');
}

export default function AdminTeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [creatingTeacher, setCreatingTeacher] = useState(false);
  const [updatingTeacherId, setUpdatingTeacherId] = useState<string | null>(null);
  const [deletingTeacherId, setDeletingTeacherId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [classLevel, setClassLevel] = useState('');
  const [stream, setStream] = useState<StreamValue>('');
  const [status, setStatus] = useState('');

  const [salaryItems, setSalaryItems] = useState<SalaryLedgerItem[]>([]);
  const [salarySummary, setSalarySummary] = useState<SalaryLedgerResponse['summary']>({
    total_amount: 0,
    lecture_count: 0,
    teacher_count: 0,
  });
  const [salaryLoading, setSalaryLoading] = useState(false);
  const [salaryTeacherId, setSalaryTeacherId] = useState('');
  const [salaryClassLevel, setSalaryClassLevel] = useState('');
  const [salaryStream, setSalaryStream] = useState<StreamValue>('');
  const [salaryFromDate, setSalaryFromDate] = useState('');
  const [salaryToDate, setSalaryToDate] = useState('');
  const [selectedActionByTeacher, setSelectedActionByTeacher] = useState<Record<string, TeacherAction | ''>>({});

  const [createForm, setCreateForm] = useState({
    full_name: '',
    phone: '',
    password: '',
    employee_code: '',
    designation: '',
    qualification: '',
    specialization: '',
    hourly_salary_rate: '0',
  });
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['10-common']);

  async function loadTeachers(options?: {
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

      if (nextSearch.trim()) params.set('search', nextSearch.trim());
      if (nextClassLevel) params.set('class_level', nextClassLevel);
      if ((nextClassLevel === '11' || nextClassLevel === '12') && nextStream) params.set('stream', nextStream);
      if (nextStatus) params.set('status', nextStatus);

      const response = await apiRequest<{ items: Teacher[] }>(`/api/v1/admin/teachers?${params.toString()}`);
      setTeachers(response.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teachers');
    } finally {
      setLoading(false);
      setFetching(false);
    }
  }

  async function loadSalaryLedger() {
    setSalaryLoading(true);
    try {
      const params = new URLSearchParams({
        limit: '100',
        offset: '0',
      });
      if (salaryTeacherId) params.set('teacher_id', salaryTeacherId);
      if (salaryClassLevel) params.set('class_level', salaryClassLevel);
      if ((salaryClassLevel === '11' || salaryClassLevel === '12') && salaryStream) {
        params.set('stream', salaryStream);
      }
      if (salaryFromDate) params.set('from_date', salaryFromDate);
      if (salaryToDate) params.set('to_date', salaryToDate);

      const response = await apiRequest<SalaryLedgerResponse>(`/api/v1/admin/teachers/salary-ledger?${params.toString()}`);
      setSalaryItems(response.items ?? []);
      setSalarySummary(response.summary ?? { total_amount: 0, lecture_count: 0, teacher_count: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load salary ledger');
    } finally {
      setSalaryLoading(false);
    }
  }

  async function createTeacher() {
    setCreatingTeacher(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const payload = {
        full_name: createForm.full_name.trim(),
        phone: createForm.phone.trim(),
        password: createForm.password.trim() || null,
        employee_code: createForm.employee_code.trim() || null,
        designation: createForm.designation.trim() || null,
        qualification: createForm.qualification.trim() || null,
        specialization: createForm.specialization.trim() || null,
        hourly_salary_rate: Number(createForm.hourly_salary_rate || '0'),
        teaching_scopes: selectedScopes,
      };

      const response = await apiRequest<{ full_name: string; login_id: string; issued_password: string }>(
        '/api/v1/admin/teachers',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
      );

      setSuccessMessage(
        `Teacher created: ${response.full_name} | Login ID: ${response.login_id} | Password: ${response.issued_password}`,
      );
      setCreateForm({
        full_name: '',
        phone: '',
        password: '',
        employee_code: '',
        designation: '',
        qualification: '',
        specialization: '',
        hourly_salary_rate: '0',
      });
      setSelectedScopes(['10-common']);
      await loadTeachers({ search, classLevel, stream, status });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create teacher');
    } finally {
      setCreatingTeacher(false);
    }
  }

  async function updateTeacherStatus(teacher: Teacher, nextStatus: 'active' | 'inactive' | 'suspended') {
    setUpdatingTeacherId(teacher.teacher_id);
    setError(null);
    try {
      await apiRequest(`/api/v1/admin/teachers/${teacher.teacher_id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: nextStatus }),
      });
      await loadTeachers({ search, classLevel, stream, status });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update teacher status');
    } finally {
      setUpdatingTeacherId(null);
    }
  }

  async function resetCredentials(teacher: Teacher) {
    const password = window.prompt(`Enter new password for ${teacher.full_name} (leave blank to auto-generate):`, '');
    if (password === null) return;

    setUpdatingTeacherId(teacher.teacher_id);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await apiRequest<{ login_id: string; temporary_password: string }>(
        `/api/v1/admin/teachers/${teacher.teacher_id}/credentials/reset`,
        {
          method: 'POST',
          body: JSON.stringify({ new_password: password.trim() || null }),
        },
      );
      setSuccessMessage(
        `Credentials updated for ${teacher.full_name} | Login ID: ${response.login_id} | Password: ${response.temporary_password}`,
      );
      await loadTeachers({ search, classLevel, stream, status });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset teacher credentials');
    } finally {
      setUpdatingTeacherId(null);
    }
  }

  async function deleteTeacher(teacher: Teacher) {
    const confirmed = window.confirm(
      `Delete teacher ${teacher.full_name}? This will remove teacher role access immediately.`,
    );
    if (!confirmed) return;

    setDeletingTeacherId(teacher.teacher_id);
    setError(null);
    try {
      await apiRequest(`/api/v1/admin/teachers/${teacher.teacher_id}`, {
        method: 'DELETE',
      });
      await loadTeachers({ search, classLevel, stream, status });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete teacher account');
    } finally {
      setDeletingTeacherId(null);
    }
  }

  async function executeTeacherAction(teacher: Teacher) {
    const selectedAction = selectedActionByTeacher[teacher.teacher_id] || '';
    if (!selectedAction) return;

    if (selectedAction === 'active' || selectedAction === 'inactive' || selectedAction === 'suspended') {
      await updateTeacherStatus(teacher, selectedAction);
    } else if (selectedAction === 'reset_password') {
      await resetCredentials(teacher);
    } else if (selectedAction === 'salary_slip') {
      await openSalarySlip(teacher);
    } else if (selectedAction === 'delete') {
      await deleteTeacher(teacher);
    }

    setSelectedActionByTeacher((prev) => ({ ...prev, [teacher.teacher_id]: '' }));
  }

  async function openSalarySlip(teacher: Teacher) {
    try {
      const params = new URLSearchParams();
      if (salaryFromDate) params.set('from_date', salaryFromDate);
      if (salaryToDate) params.set('to_date', salaryToDate);
      const response = await apiRequest<{
        teacher: { full_name: string; employee_code: string; teaching_scope: string | null };
        period: { from_date: string | null; to_date: string | null };
        summary: { total_amount: number; lecture_count: number };
        entries: SalaryLedgerItem[];
      }>(`/api/v1/admin/teachers/${teacher.teacher_id}/salary-slip?${params.toString()}`);

      const popup = window.open('', '_blank', 'width=980,height=720');
      if (!popup) return;

      const rows = response.entries
        .map(
          (item) => `<tr>
            <td>${item.attendance_date}</td>
            <td>${item.class_level} ${item.stream}</td>
            <td>${item.topic}</td>
            <td>${item.lecture_duration_minutes} min</td>
            <td>${formatInr(item.hourly_rate)}</td>
            <td>${formatInr(item.amount)}</td>
          </tr>`,
        )
        .join('');

      popup.document.write(`
        <html>
          <head>
            <title>Teacher Salary Slip</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 24px; color: #111827; }
              h1 { margin: 0 0 6px; }
              .muted { color: #4b5563; margin: 0 0 14px; }
              table { width: 100%; border-collapse: collapse; margin-top: 12px; }
              th, td { border: 1px solid #d1d5db; padding: 8px; font-size: 12px; }
              th { background: #f3f4f6; text-align: left; }
            </style>
          </head>
          <body>
            <h1>Teacher Salary Slip</h1>
            <p class="muted"><strong>${response.teacher.full_name}</strong> (${response.teacher.employee_code})</p>
            <p class="muted">Period: ${response.period.from_date ?? '-'} to ${response.period.to_date ?? '-'}</p>
            <p><strong>Total Lectures:</strong> ${response.summary.lecture_count} &nbsp; <strong>Total Amount:</strong> ${formatInr(response.summary.total_amount)}</p>
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Class/Stream</th>
                  <th>Topic</th>
                  <th>Duration</th>
                  <th>Hourly Rate</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </body>
        </html>
      `);
      popup.document.close();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load salary slip');
    }
  }

  useEffect(() => {
    void loadTeachers({
      search: '',
      classLevel: '',
      stream: '',
      status: '',
      initial: true,
    });
    void loadSalaryLedger();
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

  const compactSummaryCardStyle: React.CSSProperties = {
    background: '#efe7ff',
    borderColor: '#d9c7ff',
    padding: '10px 12px',
    minHeight: 86,
  };

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Teachers</h1>
      <p className="muted" style={{ marginTop: -4 }}>
        Admin-managed teacher onboarding, credentials, class allocation, status control, and lecture-based salary tracking.
      </p>

      {error ? <p style={{ color: '#dc2626', fontWeight: 600 }}>{error}</p> : null}
      {successMessage ? <p style={{ color: '#166534', fontWeight: 600 }}>{successMessage}</p> : null}

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card" style={compactSummaryCardStyle}><h3 style={{ marginTop: 0, marginBottom: 4, fontSize: 14 }}>Total Teachers</h3><div style={{ fontSize: 20, fontWeight: 800 }}>{summary.total}</div></div>
        <div className="card" style={compactSummaryCardStyle}><h3 style={{ marginTop: 0, marginBottom: 4, fontSize: 14 }}>Active</h3><div style={{ fontSize: 20, fontWeight: 800, color: '#166534' }}>{summary.active}</div></div>
        <div className="card" style={compactSummaryCardStyle}><h3 style={{ marginTop: 0, marginBottom: 4, fontSize: 14 }}>Inactive</h3><div style={{ fontSize: 20, fontWeight: 800, color: '#92400e' }}>{summary.inactive}</div></div>
        <div className="card" style={compactSummaryCardStyle}><h3 style={{ marginTop: 0, marginBottom: 4, fontSize: 14 }}>Suspended</h3><div style={{ fontSize: 20, fontWeight: 800, color: '#991b1b' }}>{summary.suspended}</div></div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create Teacher (Admin)</h3>
        <div className="grid">
          <label className="field"><span>Full Name</span><input value={createForm.full_name} onChange={(event) => setCreateForm((prev) => ({ ...prev, full_name: event.target.value }))} /></label>
          <label className="field"><span>Phone (Login ID)</span><input value={createForm.phone} onChange={(event) => setCreateForm((prev) => ({ ...prev, phone: event.target.value }))} /></label>
          <label className="field"><span>Password (optional)</span><input value={createForm.password} onChange={(event) => setCreateForm((prev) => ({ ...prev, password: event.target.value }))} placeholder="Auto-generated if blank" /></label>
          <label className="field"><span>Employee Code (optional)</span><input value={createForm.employee_code} onChange={(event) => setCreateForm((prev) => ({ ...prev, employee_code: event.target.value }))} /></label>
          <label className="field"><span>Designation</span><input value={createForm.designation} onChange={(event) => setCreateForm((prev) => ({ ...prev, designation: event.target.value }))} /></label>
          <label className="field"><span>Qualification</span><input value={createForm.qualification} onChange={(event) => setCreateForm((prev) => ({ ...prev, qualification: event.target.value }))} /></label>
          <label className="field"><span>Specialization</span><input value={createForm.specialization} onChange={(event) => setCreateForm((prev) => ({ ...prev, specialization: event.target.value }))} /></label>
          <label className="field"><span>Hourly Salary (INR)</span><input type="number" min={0} value={createForm.hourly_salary_rate} onChange={(event) => setCreateForm((prev) => ({ ...prev, hourly_salary_rate: event.target.value }))} /></label>
        </div>

        <div style={{ marginBottom: 10 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Teaching Scopes (6th to 12th)</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8 }}>
            {TEACHING_SCOPES.map((scope) => (
              <label key={scope.value} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={selectedScopes.includes(scope.value)}
                  onChange={(event) => {
                    if (event.target.checked) {
                      setSelectedScopes((prev) => [...prev, scope.value]);
                      return;
                    }
                    setSelectedScopes((prev) => prev.filter((item) => item !== scope.value));
                  }}
                />
                {scope.label}
              </label>
            ))}
          </div>
        </div>

        <button className="btn" type="button" disabled={creatingTeacher} onClick={() => void createTeacher()}>
          {creatingTeacher ? 'Creating...' : 'Create Teacher'}
        </button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Filter Teachers</h3>
        <div className="grid" style={{ marginBottom: 10 }}>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Search</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, phone, employee code" />
          </label>

          <label className="field" style={{ marginBottom: 0 }}>
            <span>Class</span>
            <select value={classLevel} onChange={(event) => {
              const nextClass = event.target.value;
              setClassLevel(nextClass);
              if (nextClass !== '11' && nextClass !== '12') setStream('');
            }}>
              <option value="">All classes</option>
              <option value="6">6th</option>
              <option value="7">7th</option>
              <option value="8">8th</option>
              <option value="9">9th</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>

          <label className="field" style={{ marginBottom: 0 }}>
            <span>Stream</span>
            <select value={stream} onChange={(event) => setStream(event.target.value as StreamValue)} disabled={classLevel !== '11' && classLevel !== '12'}>
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
          <button className="btn" type="button" disabled={fetching} onClick={() => void loadTeachers()}>
            {fetching ? 'Applying...' : 'Apply Filters'}
          </button>
          <button
            className="btn"
            type="button"
            style={{ background: '#5b21b6', color: '#ffffff', borderColor: '#4c1d95' }}
            onClick={() => {
              setSearch('');
              setClassLevel('');
              setStream('');
              setStatus('');
              void loadTeachers({ search: '', classLevel: '', stream: '', status: '' });
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Teacher Directory</h3>
        {loading ? (
          <p>Loading teachers...</p>
        ) : (
          <div style={{ overflowX: 'hidden' }}>
            <table className="table" style={{ width: '100%', tableLayout: 'fixed' }}>
              <thead>
                <tr>
                  <th style={{ width: '12%' }}>Name</th>
                  <th style={{ width: '11%' }}>Contact</th>
                  <th style={{ width: '10%' }}>Designation</th>
                  <th style={{ width: '14%' }}>Teaching Scope</th>
                  <th style={{ width: '10%' }}>Hourly Salary</th>
                  <th style={{ width: '13%' }}>Credentials</th>
                  <th style={{ width: '8%' }}>Status</th>
                  <th style={{ width: '10%' }}>Joined</th>
                  <th style={{ width: '12%' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {teachers.length === 0 ? (
                  <tr><td colSpan={9} className="muted">No teachers found for selected filters.</td></tr>
                ) : (
                  teachers.map((teacher) => (
                    <tr key={teacher.teacher_id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{teacher.full_name}</div>
                        <div className="muted" style={{ fontSize: 12 }}>{teacher.employee_code}</div>
                      </td>
                      <td style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{teacher.phone ?? '-'}</td>
                      <td style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{teacher.designation ?? '-'}</td>
                      <td style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{formatTeachingScope(teacher.teaching_scope)}</td>
                      <td style={{ whiteSpace: 'normal' }}>{formatInr(teacher.hourly_salary_rate || 0)}</td>
                      <td>
                        <div style={{ fontSize: 12 }}><strong>ID:</strong> {teacher.phone ?? '-'}</div>
                        <div style={{ fontSize: 12 }}><strong>Pass:</strong> {teacher.current_password ?? '-'}</div>
                      </td>
                      <td>
                        <span className="badge" style={{ textTransform: 'capitalize', background: statusBadgeColor(teacher.status), color: '#0f172a' }}>
                          {titleCase(teacher.status)}
                        </span>
                      </td>
                      <td style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{formatDateTime(teacher.created_at)}</td>
                      <td style={{ verticalAlign: 'top' }}>
                        <div style={{ display: 'grid', gap: 8 }}>
                          <select
                            value={selectedActionByTeacher[teacher.teacher_id] ?? ''}
                            onChange={(event) => {
                              const nextValue = event.target.value as TeacherAction | '';
                              setSelectedActionByTeacher((prev) => ({ ...prev, [teacher.teacher_id]: nextValue }));
                            }}
                            disabled={updatingTeacherId === teacher.teacher_id || deletingTeacherId === teacher.teacher_id}
                            style={{
                              width: '100%',
                              minHeight: 34,
                              borderRadius: 8,
                              border: '1px solid #c4b5fd',
                              background: '#f5f3ff',
                              color: '#312e81',
                              fontWeight: 600,
                              fontSize: 12,
                              padding: '6px 8px',
                            }}
                          >
                            <option value="">Select action</option>
                            <option value="active">Set Active</option>
                            <option value="inactive">Set Inactive</option>
                            <option value="suspended">Set Suspended</option>
                            <option value="reset_password">Reset Password</option>
                            <option value="salary_slip">Open Salary Slip</option>
                            <option value="delete">Delete Teacher</option>
                          </select>

                          <button
                            className="btn"
                            type="button"
                            style={{
                              width: '100%',
                              borderRadius: 8,
                              minHeight: 34,
                              fontSize: 12,
                              fontWeight: 700,
                              background: '#6d28d9',
                              borderColor: '#5b21b6',
                              color: '#ffffff',
                            }}
                            disabled={
                              !selectedActionByTeacher[teacher.teacher_id] ||
                              updatingTeacherId === teacher.teacher_id ||
                              deletingTeacherId === teacher.teacher_id
                            }
                            onClick={() => void executeTeacherAction(teacher)}
                          >
                            {updatingTeacherId === teacher.teacher_id || deletingTeacherId === teacher.teacher_id ? 'Processing...' : 'Proceed'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Teacher Salary Ledger</h3>
        <div className="grid" style={{ marginBottom: 10 }}>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Teacher</span>
            <select value={salaryTeacherId} onChange={(event) => setSalaryTeacherId(event.target.value)}>
              <option value="">All teachers</option>
              {teachers.map((teacher) => (
                <option key={teacher.teacher_id} value={teacher.teacher_id}>{teacher.full_name}</option>
              ))}
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Class</span>
            <select value={salaryClassLevel} onChange={(event) => {
              const nextClass = event.target.value;
              setSalaryClassLevel(nextClass);
              if (nextClass !== '11' && nextClass !== '12') setSalaryStream('');
            }}>
              <option value="">All classes</option>
              <option value="6">6th</option>
              <option value="7">7th</option>
              <option value="8">8th</option>
              <option value="9">9th</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Stream</span>
            <select value={salaryStream} onChange={(event) => setSalaryStream(event.target.value as StreamValue)} disabled={salaryClassLevel !== '11' && salaryClassLevel !== '12'}>
              <option value="">All streams</option>
              <option value="science">Science</option>
              <option value="commerce">Commerce</option>
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>From</span>
            <input type="date" value={salaryFromDate} onChange={(event) => setSalaryFromDate(event.target.value)} />
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>To</span>
            <input type="date" value={salaryToDate} onChange={(event) => setSalaryToDate(event.target.value)} />
          </label>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <button className="btn" type="button" disabled={salaryLoading} onClick={() => void loadSalaryLedger()}>
            {salaryLoading ? 'Loading...' : 'Load Salary Data'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 10 }}>
          <span><strong>Total Salary:</strong> {formatInr(salarySummary.total_amount)}</span>
          <span><strong>Completed Lectures:</strong> {salarySummary.lecture_count}</span>
          <span><strong>Teachers:</strong> {salarySummary.teacher_count}</span>
        </div>

        <div style={{ overflowX: 'hidden' }}>
          <table className="table" style={{ width: '100%', tableLayout: 'fixed' }}>
            <thead>
              <tr>
                <th>Teacher</th>
                <th>Class</th>
                <th>Topic</th>
                <th>Duration</th>
                <th>Rate</th>
                <th>Amount</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {salaryItems.length === 0 ? (
                <tr><td colSpan={7} className="muted">No salary records found for selected filters.</td></tr>
              ) : (
                salaryItems.map((item) => (
                  <tr key={item.ledger_id}>
                    <td style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{item.teacher_name}</td>
                    <td>{item.class_level} {item.stream}</td>
                    <td style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{item.topic}</td>
                    <td>{item.lecture_duration_minutes} min</td>
                    <td>{formatInr(item.hourly_rate)}</td>
                    <td>{formatInr(item.amount)}</td>
                    <td>{item.attendance_date}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
