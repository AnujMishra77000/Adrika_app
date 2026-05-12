'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';
import { API_BASE_URL } from '@/lib/env';
import styles from '../details.module.css';

type StudentProfilePayload = {
  student: {
    student_id: string;
    full_name: string;
    phone: string | null;
    parent_contact_number: string | null;
    class_name: string | null;
    stream: string | null;
    admission_no: string;
    roll_no: string;
    subjects: string[];
    progress: {
      tests_taken: number;
      scored_marks: number;
      total_marks: number;
      percentage: number;
      last_result_at: string | null;
    };
    attendance: {
      present_sessions: number;
      total_sessions: number;
      percentage: number;
    };
    fee: {
      fee_structure_name: string | null;
      total_amount: number;
      paid_amount: number;
      pending_amount: number;
      status: string;
      is_fully_paid: boolean;
      last_paid_at: string | null;
    };
  };
  analytics: {
    recent_results: Array<{
      result_id: string;
      title: string;
      topic: string | null;
      subject: string;
      score: number;
      total_marks: number;
      percentage: number;
      rank: number | null;
      published_at: string | null;
    }>;
    attendance_timeline: Array<{
      date: string;
      status: string;
    }>;
    attendance_status_counts: {
      present: number;
      absent: number;
      late: number;
      leave: number;
    };
    payment_ledger: Array<{
      payment_id: string;
      invoice_no: string;
      period_label: string;
      amount: number;
      payment_mode: string;
      reference_no: string | null;
      paid_at: string;
    }>;
  };
};

function formatDateTime(value: string | null): string {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '-';
  return parsed.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function backendOrigin(): string {
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return API_BASE_URL.replace(/\/+$/, '');
  }
}

function toAbsoluteMediaUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return `${backendOrigin()}${url.startsWith('/') ? url : `/${url}`}`;
}

function barColor(status: string): string {
  if (status === 'present') return '#16a34a';
  if (status === 'late') return '#f59e0b';
  if (status === 'leave') return '#0ea5e9';
  return '#ef4444';
}

export default function StudentFullProfilePage({ params }: { params: { studentId: string } }) {
  const { studentId } = params;
  const [payload, setPayload] = useState<StudentProfilePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<StudentProfilePayload>(`/api/v1/admin/students/${studentId}/full-profile`);
      setPayload(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student full profile');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  const attendanceChartData = useMemo(() => {
    if (!payload) return [];
    const counts = payload.analytics.attendance_status_counts;
    const entries = [
      { label: 'Present', key: 'present', value: counts.present },
      { label: 'Absent', key: 'absent', value: counts.absent },
      { label: 'Late', key: 'late', value: counts.late },
      { label: 'Leave', key: 'leave', value: counts.leave },
    ] as const;
    const total = entries.reduce((sum, item) => sum + item.value, 0);
    return entries.map((item) => ({
      ...item,
      percentage: total > 0 ? Math.round((item.value / total) * 100) : 0,
    }));
  }, [payload]);

  async function exportProfilePdf() {
    if (!payload) return;
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiRequest<{ profile_export: { download_url: string } }>(
        `/api/v1/admin/students/${payload.student.student_id}/full-profile/export`,
      );
      const url = toAbsoluteMediaUrl(response.profile_export.download_url);
      if (typeof window !== 'undefined') {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
      setSuccess('Profile export generated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export profile');
    } finally {
      setActionLoading(false);
    }
  }

  async function sendReportCardToParent() {
    if (!payload) return;
    setActionLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/api/v1/admin/students/${payload.student.student_id}/report-card/whatsapp`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setSuccess('Report card sent to parent WhatsApp.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send report card');
    } finally {
      setActionLoading(false);
    }
  }

  function printProfile() {
    if (typeof window !== 'undefined') {
      window.print();
    }
  }

  return (
    <section className={`student-admin-theme ${styles.pageRoot}`}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.pageTitle}>Student Full Profile</h1>
          <p className={`muted ${styles.pageSubtitle}`}>
            Drill-down view with attendance, performance trend and fee ledger.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Link className={`btn ${styles.primaryButton}`} href="/admin/students/details">
            Back To Student Details
          </Link>
          <button className={`btn ${styles.primaryButton}`} type="button" onClick={printProfile} disabled={actionLoading}>
            Print Profile
          </button>
          <button
            className={`btn ${styles.primaryButton}`}
            type="button"
            onClick={() => void exportProfilePdf()}
            disabled={actionLoading}
          >
            Export Profile PDF
          </button>
          <button
            className={`btn ${styles.primaryButton}`}
            type="button"
            onClick={() => void sendReportCardToParent()}
            disabled={actionLoading}
          >
            Send Report To Parent
          </button>
        </div>
      </div>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
      {success ? <p style={{ color: '#166534' }}>{success}</p> : null}

      {loading || !payload ? (
        <div className="card">Loading full profile...</div>
      ) : (
        <>
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <h3 className={styles.summaryTitle}>Student Identity</h3>
              <div className={styles.summaryValue}>{payload.student.full_name}</div>
              <div className={styles.summarySubtle}>
                {payload.student.class_name ?? '-'} • {payload.student.stream ?? '-'}
              </div>
              <div className={styles.summarySubtle}>
                Admission: {payload.student.admission_no} • Roll: {payload.student.roll_no}
              </div>
              <div className={styles.summarySubtle}>
                Student: {payload.student.phone ?? '-'} | Parent: {payload.student.parent_contact_number ?? '-'}
              </div>
            </div>

            <div className={styles.summaryCard}>
              <h3 className={styles.summaryTitle}>Attendance</h3>
              <div className={styles.summaryValue}>{payload.student.attendance.percentage.toFixed(2)}%</div>
              <div className={styles.summarySubtle}>
                {payload.student.attendance.present_sessions}/{payload.student.attendance.total_sessions} sessions
              </div>
              <div className={styles.progressTrack}>
                <div
                  className={styles.progressFill}
                  style={{
                    width: `${Math.min(Math.max(payload.student.attendance.percentage, 0), 100)}%`,
                    background: '#16a34a',
                  }}
                />
              </div>
            </div>

            <div className={styles.summaryCard}>
              <h3 className={styles.summaryTitle}>Progress</h3>
              <div className={styles.summaryValue}>{payload.student.progress.percentage.toFixed(2)}%</div>
              <div className={styles.summarySubtle}>
                {payload.student.progress.scored_marks.toFixed(2)} / {payload.student.progress.total_marks.toFixed(2)}
              </div>
              <div className={styles.summarySubtle}>Tests Taken: {payload.student.progress.tests_taken}</div>
            </div>

            <div className={styles.summaryCard}>
              <h3 className={styles.summaryTitle}>Fee Status</h3>
              <div className={styles.summaryValue}>INR {payload.student.fee.pending_amount.toFixed(2)}</div>
              <div className={styles.summarySubtle}>Pending Amount</div>
              <div className={styles.summarySubtle}>Plan: {payload.student.fee.fee_structure_name ?? '-'}</div>
              <div className={styles.summarySubtle}>Paid: INR {payload.student.fee.paid_amount.toFixed(2)}</div>
            </div>
          </div>

          <div className={styles.twoColGrid}>
            <div className="card">
              <h3 className={styles.cardTitle}>Result Trend (Recent Tests)</h3>
              {payload.analytics.recent_results.length === 0 ? (
                <p className="muted">No result history yet.</p>
              ) : (
                <div className={styles.listStack}>
                  {payload.analytics.recent_results.slice(0, 8).map((item) => (
                    <div key={item.result_id} className={styles.listItem}>
                      <div className={styles.listHeader}>
                        <div>
                          <div className={styles.listTitle}>
                            {item.subject} • {item.title}
                          </div>
                          <div className={`muted ${styles.listMeta}`}>
                            {item.topic ?? '-'} • {formatDateTime(item.published_at)}
                          </div>
                        </div>
                        <div className={styles.listTitle}>{item.percentage.toFixed(2)}%</div>
                      </div>
                      <div className={styles.progressTrack}>
                        <div
                          className={styles.progressFill}
                          style={{
                            width: `${Math.min(Math.max(item.percentage, 0), 100)}%`,
                            background: '#6d28d9',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <h3 className={styles.cardTitle}>Attendance Distribution</h3>
              <div className={styles.listStack}>
                {attendanceChartData.map((item) => (
                  <div key={item.key} className={styles.listItem}>
                    <div className={styles.listHeader}>
                      <span>{item.label}</span>
                      <span>
                        {item.value} ({item.percentage}%)
                      </span>
                    </div>
                    <div className={styles.progressTrack}>
                      <div
                        className={styles.progressFill}
                        style={{
                          width: `${Math.min(Math.max(item.percentage, 0), 100)}%`,
                          background: barColor(item.key),
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className={styles.bottomGrid}>
            <div className="card">
              <h3 className={styles.cardTitle}>Attendance Timeline</h3>
              {payload.analytics.attendance_timeline.length === 0 ? (
                <p className="muted">No attendance records yet.</p>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payload.analytics.attendance_timeline.slice(0, 12).map((item, idx) => (
                      <tr key={`${item.date}-${idx}`}>
                        <td>{item.date}</td>
                        <td>
                          <span className="badge">{item.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="card">
              <h3 className={styles.cardTitle}>Fee Payment Ledger</h3>
              {payload.analytics.payment_ledger.length === 0 ? (
                <p className="muted">No successful payments yet.</p>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Invoice</th>
                      <th>Amount</th>
                      <th>Mode</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payload.analytics.payment_ledger.slice(0, 12).map((item) => (
                      <tr key={item.payment_id}>
                        <td>{item.invoice_no}</td>
                        <td>INR {item.amount.toFixed(2)}</td>
                        <td>{item.payment_mode}</td>
                        <td>{formatDateTime(item.paid_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
