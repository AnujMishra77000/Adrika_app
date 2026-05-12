'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';
import { API_BASE_URL } from '@/lib/env';
import styles from './details.module.css';

type StudentDetail = {
  student_id: string;
  full_name: string;
  phone: string | null;
  parent_contact_number: string | null;
  class_name: string | null;
  stream: string | null;
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
  };
};

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

export default function AdminStudentDetailsPage() {
  const [items, setItems] = useState<StudentDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeActionStudentId, setActiveActionStudentId] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState<'all' | '10' | '11' | '12'>('all');
  const [streamFilter, setStreamFilter] = useState<'all' | 'science' | 'commerce'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive' | 'suspended'>('all');

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: '100',
        offset: '0',
      });
      if (search.trim()) params.set('search', search.trim());
      if (classFilter !== 'all') params.set('class_level', classFilter);
      if (streamFilter !== 'all') params.set('stream', streamFilter);
      if (statusFilter !== 'all') params.set('status', statusFilter);

      const response = await apiRequest<{ items: StudentDetail[] }>(`/api/v1/admin/students/details?${params.toString()}`);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student details');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function downloadReportCard(studentId: string) {
    setActiveActionStudentId(studentId);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiRequest<{ report_card: { download_url: string } }>(
        `/api/v1/admin/students/${studentId}/report-card`,
      );
      const downloadUrl = toAbsoluteMediaUrl(response.report_card.download_url);
      if (typeof window !== 'undefined') {
        window.open(downloadUrl, '_blank', 'noopener,noreferrer');
      }
      setSuccess('Report card generated and opened.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report card');
    } finally {
      setActiveActionStudentId(null);
    }
  }

  async function sendToParent(studentId: string) {
    setActiveActionStudentId(studentId);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/api/v1/admin/students/${studentId}/report-card/whatsapp`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setSuccess('Report card sent to parent WhatsApp.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send report card to parent');
    } finally {
      setActiveActionStudentId(null);
    }
  }

  return (
    <section className={`student-admin-theme ${styles.pageRoot}`}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Student Details</h1>
        <p className={`muted ${styles.pageSubtitle}`}>
          Class and stream wise student analytics with attendance, test marks, fee status and report card actions.
        </p>
      </header>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
      {success ? <p style={{ color: '#166534' }}>{success}</p> : null}

      <div className={`card ${styles.panelCard}`}>
        <h3 className={styles.cardTitle}>Search and Filters</h3>
        <div className={styles.filterGrid}>
          <label className={`field ${styles.filterField}`}>
            <span>Search Student</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="name / mobile / admission"
            />
          </label>
          <label className={`field ${styles.filterField}`}>
            <span>Class</span>
            <select value={classFilter} onChange={(e) => setClassFilter(e.target.value as 'all' | '10' | '11' | '12')}>
              <option value="all">All</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>
          <label className={`field ${styles.filterField}`}>
            <span>Stream</span>
            <select value={streamFilter} onChange={(e) => setStreamFilter(e.target.value as 'all' | 'science' | 'commerce')}>
              <option value="all">All</option>
              <option value="science">Science</option>
              <option value="commerce">Commerce</option>
            </select>
          </label>
          <label className={`field ${styles.filterField}`}>
            <span>Status</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive' | 'suspended')}>
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>
        </div>
        <button className={`btn ${styles.primaryButton}`} type="button" onClick={() => void load()}>
          Apply Filters
        </button>
      </div>

      <div className={`card ${styles.panelCard}`}>
        <h3 className={styles.cardTitle}>Student Performance Directory</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={`table ${styles.detailsTable}`}>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Class / Stream</th>
                  <th>Progress</th>
                  <th>Attendance</th>
                  <th>Fee Details</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((student) => (
                  <tr key={student.student_id}>
                    <td className={styles.studentCell}>
                      <div className={styles.studentName}>{student.full_name}</div>
                      <div className={`muted ${styles.studentMeta}`}>
                        {student.phone ?? '-'} • Parent: {student.parent_contact_number ?? '-'}
                      </div>
                    </td>
                    <td>
                      <div className={styles.classValue}>{student.class_name ?? '-'}</div>
                      <div className={`muted ${styles.streamValue}`}>{student.stream ?? '-'}</div>
                    </td>
                    <td>
                      <div className={styles.metricStack}>
                        <div className={styles.metricRow}>
                          <span>Tests</span>
                          <strong>{student.progress.tests_taken}</strong>
                        </div>
                        <div className={styles.metricRow}>
                          <span>Marks</span>
                          <strong>
                            {student.progress.scored_marks.toFixed(0)} / {student.progress.total_marks.toFixed(0)}
                          </strong>
                        </div>
                        <div className={`${styles.metricRow} ${styles.metricHighlight}`}>
                          <span>Score</span>
                          <strong>{student.progress.percentage.toFixed(2)}%</strong>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className={styles.metricStack}>
                        <div className={styles.metricRow}>
                          <span>Sessions</span>
                          <strong>
                            {student.attendance.present_sessions}/{student.attendance.total_sessions}
                          </strong>
                        </div>
                        <div className={`${styles.metricRow} ${styles.metricHighlight}`}>
                          <span>Attendance</span>
                          <strong>{student.attendance.percentage.toFixed(2)}%</strong>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className={styles.feeMeta}>{student.fee.fee_structure_name ?? '-'}</div>
                      <div className={styles.metricRow}>
                        <span>Paid</span>
                        <strong>INR {student.fee.paid_amount.toFixed(2)}</strong>
                      </div>
                      <div className={styles.metricRow}>
                        <span>Pending</span>
                        <strong>INR {student.fee.pending_amount.toFixed(2)}</strong>
                      </div>
                      <span
                        className={`${styles.feeStatus} ${
                          student.fee.is_fully_paid ? styles.feePaid : styles.feePending
                        }`}
                      >
                        {student.fee.is_fully_paid ? 'Full Paid' : 'Pending'}
                      </span>
                    </td>
                    <td>
                      <div className={styles.actionStack}>
                        <Link className={`btn ${styles.primaryButton}`} href={`/admin/students/details/${student.student_id}`}>
                          Open Full Profile
                        </Link>
                        <button
                          className={`btn ${styles.primaryButton}`}
                          type="button"
                          onClick={() => void downloadReportCard(student.student_id)}
                          disabled={activeActionStudentId === student.student_id}
                        >
                          Download Report Card PDF
                        </button>
                        <button
                          className={`btn ${styles.primaryButton}`}
                          type="button"
                          onClick={() => void sendToParent(student.student_id)}
                          disabled={activeActionStudentId === student.student_id}
                        >
                          Send To Parents (PDF)
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="muted">
                      No student data found for selected filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
