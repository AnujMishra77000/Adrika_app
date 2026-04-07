'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Student = {
  student_id: string;
  user_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  status: string;
  admission_no: string;
  roll_no: string;
  batch: { id: string; name: string } | null;
};

type Batch = { id: string; name: string; academic_year: number };

type Standard = {
  id: string;
  name: string;
  branch: { id: string; code: string; name: string };
};

export default function AdminStudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [studentRes, batchRes, standardRes] = await Promise.all([
        apiRequest<{ items: Student[] }>('/api/v1/admin/students?limit=50&offset=0'),
        apiRequest<{ items: Batch[] }>('/api/v1/admin/batches?limit=100&offset=0'),
        apiRequest<{ items: Standard[] }>('/api/v1/admin/standards?limit=100&offset=0'),
      ]);
      setStudents(studentRes.items);
      setBatches(batchRes.items);
      setStandards(standardRes.items);
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

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Students</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

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
        <h3 style={{ marginTop: 0 }}>Student List</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Admission No</th>
                <th>Roll No</th>
                <th>Status</th>
                <th>Batch</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.student_id}>
                  <td>{student.full_name}</td>
                  <td>{student.admission_no}</td>
                  <td>{student.roll_no}</td>
                  <td><span className="badge">{student.status}</span></td>
                  <td>{student.batch?.name ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
