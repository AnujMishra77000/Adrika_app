'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type AttendanceItem = {
  id: string;
  student_name: string;
  attendance_date: string;
  session_code: string;
  status: string;
  source: string;
};

type CorrectionItem = {
  id: string;
  attendance_record_id: string;
  student_name: string;
  attendance_date: string;
  current_status: string;
  requested_status: string;
  reason: string;
};

export default function AdminAttendancePage() {
  const [items, setItems] = useState<AttendanceItem[]>([]);
  const [corrections, setCorrections] = useState<CorrectionItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [attendanceRecordId, setAttendanceRecordId] = useState('');
  const [reason, setReason] = useState('');
  const [newStatuses, setNewStatuses] = useState<Record<string, string>>({});

  async function load() {
    try {
      const [attendanceRes, correctionRes] = await Promise.all([
        apiRequest<{ items: AttendanceItem[] }>('/api/v1/admin/attendance?limit=100&offset=0'),
        apiRequest<{ items: CorrectionItem[] }>('/api/v1/admin/attendance/corrections?limit=100&offset=0'),
      ]);
      setItems(attendanceRes.items);
      setCorrections(correctionRes.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load attendance');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function requestCorrection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await apiRequest('/api/v1/admin/attendance/corrections', {
        method: 'POST',
        body: JSON.stringify({ attendance_record_id: attendanceRecordId, reason }),
      });
      setAttendanceRecordId('');
      setReason('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request correction');
    }
  }

  async function decideCorrection(correctionId: string, decision: 'approved' | 'rejected') {
    try {
      const payload: { status: string; new_attendance_status?: string } = { status: decision };
      if (decision === 'approved') {
        payload.new_attendance_status = newStatuses[correctionId] ?? 'present';
      }
      await apiRequest(`/api/v1/admin/attendance/corrections/${correctionId}/decision`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to decide correction');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Attendance</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Request Correction</h3>
        <form onSubmit={requestCorrection}>
          <label className="field"><span>Attendance Record ID</span><input value={attendanceRecordId} onChange={(e) => setAttendanceRecordId(e.target.value)} required /></label>
          <label className="field"><span>Reason</span><textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required /></label>
          <button className="btn" type="submit">Submit Correction Request</button>
        </form>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Correction Queue</h3>
        <table className="table">
          <thead><tr><th>Student</th><th>Date</th><th>Current</th><th>Requested</th><th>Reason</th><th>Action</th></tr></thead>
          <tbody>
            {corrections.map((item) => (
              <tr key={item.id}>
                <td>{item.student_name}</td>
                <td>{item.attendance_date}</td>
                <td>{item.current_status}</td>
                <td><span className="badge">{item.requested_status}</span></td>
                <td>{item.reason}</td>
                <td>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <select
                      value={newStatuses[item.id] ?? 'present'}
                      onChange={(e) => setNewStatuses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    >
                      <option value="present">present</option>
                      <option value="absent">absent</option>
                      <option value="late">late</option>
                      <option value="leave">leave</option>
                    </select>
                    <button className="btn" type="button" style={{ background: '#16a34a' }} onClick={() => decideCorrection(item.id, 'approved')}>Approve</button>
                    <button className="btn" type="button" style={{ background: '#b91c1c' }} onClick={() => decideCorrection(item.id, 'rejected')}>Reject</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Attendance Records</h3>
        <table className="table">
          <thead><tr><th>Student</th><th>Date</th><th>Session</th><th>Status</th><th>Source</th><th>ID</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.student_name}</td>
                <td>{item.attendance_date}</td>
                <td>{item.session_code}</td>
                <td><span className="badge">{item.status}</span></td>
                <td>{item.source}</td>
                <td>{item.id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
