'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Student = {
  student_id: string;
  user_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  status: 'active' | 'inactive' | 'suspended' | string;
  admission_no: string;
  roll_no: string;
  class_name: string | null;
  stream: string | null;
  parent_contact_number: string | null;
  admission_date: string | null;
  batch: { id: string; name: string; academic_year: number; standard_name: string | null } | null;
};

type Batch = { id: string; name: string; academic_year: number };

type Standard = {
  id: string;
  name: string;
  branch: { id: string; code: string; name: string };
};

type StudentSummary = {
  total_students: number;
  active_students: number;
  inactive_students: number;
  suspended_students: number;
  grade_counts: Record<
    string,
    {
      total: number;
      common: number;
      science: number;
      commerce: number;
    }
  >;
};

const emptySummary: StudentSummary = {
  total_students: 0,
  active_students: 0,
  inactive_students: 0,
  suspended_students: 0,
  grade_counts: {
    '10': { total: 0, common: 0, science: 0, commerce: 0 },
    '11': { total: 0, common: 0, science: 0, commerce: 0 },
    '12': { total: 0, common: 0, science: 0, commerce: 0 },
  },
};

function nextStatus(current: string): 'active' | 'inactive' {
  return current === 'active' ? 'inactive' : 'active';
}

export default function AdminStudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [summary, setSummary] = useState<StudentSummary>(emptySummary);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusUpdatingUserId, setStatusUpdatingUserId] = useState<string | null>(null);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('Student@123');
  const [admissionNo, setAdmissionNo] = useState('');
  const [rollNo, setRollNo] = useState('');
  const [batchId, setBatchId] = useState('');

  const [newBatchName, setNewBatchName] = useState('');
  const [newBatchYear, setNewBatchYear] = useState(String(new Date().getFullYear()));
  const [newBatchStandardId, setNewBatchStandardId] = useState('');

  const gradeCards = useMemo(
    () => [
      {
        title: 'Class 10',
        lines: [`Total: ${summary.grade_counts['10']?.total ?? 0}`],
      },
      {
        title: 'Class 11',
        lines: [
          `Total: ${summary.grade_counts['11']?.total ?? 0}`,
          `Science: ${summary.grade_counts['11']?.science ?? 0}`,
          `Commerce: ${summary.grade_counts['11']?.commerce ?? 0}`,
        ],
      },
      {
        title: 'Class 12',
        lines: [
          `Total: ${summary.grade_counts['12']?.total ?? 0}`,
          `Science: ${summary.grade_counts['12']?.science ?? 0}`,
          `Commerce: ${summary.grade_counts['12']?.commerce ?? 0}`,
        ],
      },
    ],
    [summary],
  );

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [studentRes, batchRes, standardRes, summaryRes] = await Promise.all([
        apiRequest<{ items: Student[] }>('/api/v1/admin/students?limit=100&offset=0'),
        apiRequest<{ items: Batch[] }>('/api/v1/admin/batches?limit=100&offset=0'),
        apiRequest<{ items: Standard[] }>('/api/v1/admin/standards?limit=100&offset=0'),
        apiRequest<StudentSummary>('/api/v1/admin/students/summary'),
      ]);
      setStudents(studentRes.items);
      setBatches(batchRes.items);
      setStandards(standardRes.items);
      setSummary(summaryRes);
      if (!batchId && batchRes.items.length > 0) {
        setBatchId(batchRes.items[0].id);
      }
      if (!newBatchStandardId && standardRes.items.length > 0) {
        setNewBatchStandardId(standardRes.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load students');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest('/api/v1/admin/students', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName,
          email: email || null,
          phone: phone || null,
          password,
          admission_no: admissionNo,
          roll_no: rollNo,
          batch_id: batchId,
        }),
      });
      setFullName('');
      setEmail('');
      setPhone('');
      setAdmissionNo('');
      setRollNo('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create student');
    }
  }

  async function createBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await apiRequest<{ id: string }>('/api/v1/admin/batches', {
        method: 'POST',
        body: JSON.stringify({
          standard_id: newBatchStandardId,
          name: newBatchName,
          academic_year: Number(newBatchYear),
        }),
      });
      setNewBatchName('');
      await load();
      setBatchId(response.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create batch');
    }
  }

  async function toggleStatus(student: Student) {
    const targetStatus = nextStatus(student.status);
    setStatusUpdatingUserId(student.user_id);
    setError(null);
    try {
      await apiRequest(`/api/v1/admin/students/${student.user_id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: targetStatus }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update student status');
    } finally {
      setStatusUpdatingUserId(null);
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Students</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Student Count</h3>
          <div style={{ display: 'grid', gap: 6 }}>
            <div><strong>Total:</strong> {summary.total_students}</div>
            <div><strong>Active:</strong> {summary.active_students}</div>
            <div><strong>Inactive:</strong> {summary.inactive_students}</div>
            <div><strong>Suspended:</strong> {summary.suspended_students}</div>
          </div>
        </div>

        {gradeCards.map((card) => (
          <div className="card" key={card.title}>
            <h3 style={{ marginTop: 0 }}>{card.title}</h3>
            <div style={{ display: 'grid', gap: 4 }}>
              {card.lines.map((line) => (
                <div key={line}>{line}</div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Create Student</h3>
          <form onSubmit={createStudent}>
            <div className="grid">
              <label className="field"><span>Full Name</span><input value={fullName} onChange={(e) => setFullName(e.target.value)} required /></label>
              <label className="field"><span>Email</span><input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
              <label className="field"><span>Phone</span><input value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
              <label className="field"><span>Password</span><input value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
              <label className="field"><span>Admission No</span><input value={admissionNo} onChange={(e) => setAdmissionNo(e.target.value)} required /></label>
              <label className="field"><span>Roll No</span><input value={rollNo} onChange={(e) => setRollNo(e.target.value)} required /></label>
              <label className="field">
                <span>Batch</span>
                <select value={batchId} onChange={(e) => setBatchId(e.target.value)} required>
                  <option value="">Select</option>
                  {batches.map((batch) => (
                    <option key={batch.id} value={batch.id}>{batch.name} ({batch.academic_year})</option>
                  ))}
                </select>
              </label>
            </div>
            <button className="btn" type="submit">Create Student</button>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Create Batch</h3>
          <form onSubmit={createBatch}>
            <label className="field">
              <span>Standard</span>
              <select value={newBatchStandardId} onChange={(e) => setNewBatchStandardId(e.target.value)} required>
                <option value="">Select</option>
                {standards.map((standard) => (
                  <option key={standard.id} value={standard.id}>{standard.name} ({standard.branch.code})</option>
                ))}
              </select>
            </label>
            <label className="field"><span>Batch Name</span><input value={newBatchName} onChange={(e) => setNewBatchName(e.target.value)} required /></label>
            <label className="field"><span>Academic Year</span><input value={newBatchYear} onChange={(e) => setNewBatchYear(e.target.value)} required /></label>
            <button className="btn" type="submit">Create Batch</button>
          </form>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Student Directory</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Class</th>
                <th>Stream</th>
                <th>Student Contact</th>
                <th>Parent Contact</th>
                <th>Admission Date</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.student_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{student.full_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {student.admission_no} • {student.roll_no}
                    </div>
                  </td>
                  <td>{student.class_name ?? student.batch?.standard_name ?? '-'}</td>
                  <td>{student.stream ?? '-'}</td>
                  <td>{student.phone ?? '-'}</td>
                  <td>{student.parent_contact_number ?? '-'}</td>
                  <td>{student.admission_date ?? '-'}</td>
                  <td><span className="badge">{student.status}</span></td>
                  <td>
                    <button
                      className="btn"
                      type="button"
                      onClick={() => toggleStatus(student)}
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
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
