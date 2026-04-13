'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';
import { API_BASE_URL } from '@/lib/env';

import styles from './completions.module.css';

type HomeworkOption = {
  id: string;
  title: string;
};

type CompletionAttachment = {
  id: string;
  file_name: string;
  file_url: string;
  content_type: string;
  file_size_bytes: number;
};

type CompletionItem = {
  submission_id: string;
  homework_id: string;
  homework_title: string;
  student_id: string;
  student_name: string;
  contact: string | null;
  admission_no: string | null;
  class_name: string;
  stream: string;
  status: string;
  submitted_at: string;
  submitted_at_ist?: string;
  notes: string | null;
  attachments: CompletionAttachment[];
};

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

function resolveMediaUrl(fileUrl: string): string {
  const trimmed = fileUrl.trim();
  if (!trimmed) {
    return '#';
  }
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  const base = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  return base + (trimmed.startsWith('/') ? trimmed : '/' + trimmed);
}

function parseError(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback;
  }
  const raw = error.message.trim();
  if (!raw) {
    return fallback;
  }
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.detail === 'string' && parsed.detail) {
      return parsed.detail;
    }
    if (Array.isArray(parsed?.detail) && parsed.detail.length > 0) {
      const first = parsed.detail[0];
      if (typeof first?.msg === 'string' && first.msg) {
        return first.msg;
      }
    }
  } catch {
    return raw;
  }
  return raw;
}

export default function AdminHomeworkCompletionsPage() {
  const [items, setItems] = useState<CompletionItem[]>([]);
  const [homeworkOptions, setHomeworkOptions] = useState<HomeworkOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [homeworkId, setHomeworkId] = useState('');
  const [classLevel, setClassLevel] = useState<'all' | '10' | '11' | '12'>('all');
  const [stream, setStream] = useState<'all' | 'science' | 'commerce'>('all');
  const [search, setSearch] = useState('');

  const summary = useMemo(() => {
    const total = items.length;
    const late = items.filter((item) => item.status.toLowerCase() === 'late').length;
    const withAttachment = items.filter((item) => item.attachments.length > 0).length;
    return { total, late, withAttachment };
  }, [items]);

  async function loadHomeworkOptions() {
    const response = await apiRequest<{ items: HomeworkOption[] }>('/api/v1/admin/homework?limit=100&offset=0');
    setHomeworkOptions(response.items);
  }

  async function loadCompletions() {
    const params = new URLSearchParams({ limit: '100', offset: '0' });
    if (homeworkId) {
      params.set('homework_id', homeworkId);
    }
    if (classLevel !== 'all') {
      params.set('class_level', classLevel);
    }
    if (stream !== 'all') {
      params.set('stream', stream);
    }
    const q = search.trim();
    if (q) {
      params.set('search', q);
    }

    const response = await apiRequest<{ items: CompletionItem[] }>(
      '/api/v1/admin/homework/completions?' + params.toString(),
    );
    setItems(response.items);
  }

  async function bootstrap() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadHomeworkOptions(), loadCompletions()]);
    } catch (err) {
      setError(parseError(err, 'Failed to load homework completions'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await loadCompletions();
    } catch (err) {
      setError(parseError(err, 'Failed to fetch completions'));
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Homework Completion</h1>
          <p className={styles.subtitle}>
            Track submissions by class and stream, verify submission time, and open student PDF files.
          </p>
        </div>
        <div className={styles.actions}>
          <Link href="/admin/homework" className={styles.btnSecondary}>
            Back to Homework
          </Link>
        </div>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Total Submitted</div>
          <div className={styles.summaryValue}>{summary.total}</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Late Submissions</div>
          <div className={styles.summaryValue}>{summary.late}</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryLabel}>With Attachments</div>
          <div className={styles.summaryValue}>{summary.withAttachment}</div>
        </div>
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Filters</h3>
        <form className={styles.formGrid} onSubmit={applyFilters}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Homework</span>
            <select className={styles.select} value={homeworkId} onChange={(e) => setHomeworkId(e.target.value)}>
              <option value="">All Homework</option>
              {homeworkOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.title}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Class</span>
            <select className={styles.select} value={classLevel} onChange={(e) => setClassLevel(e.target.value as 'all' | '10' | '11' | '12')}>
              <option value="all">All</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Stream</span>
            <select className={styles.select} value={stream} onChange={(e) => setStream(e.target.value as 'all' | 'science' | 'commerce')}>
              <option value="all">All</option>
              <option value="science">Science</option>
              <option value="commerce">Commerce</option>
            </select>
          </label>

          <label className={styles.fieldWide}>
            <span className={styles.fieldLabel}>Search Student</span>
            <input
              className={styles.input}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name / phone / admission no"
            />
          </label>

          <div className={styles.buttons}>
            <button className={styles.btnPrimary} type="submit" disabled={loading}>
              {loading ? 'Loading...' : 'Apply'}
            </button>
            <button
              className={styles.btnSecondary}
              type="button"
              onClick={() => {
                setHomeworkId('');
                setClassLevel('all');
                setStream('all');
                setSearch('');
                void loadCompletions();
              }}
              disabled={loading}
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Submission List</h3>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Student</th>
                <th>Class / Stream</th>
                <th>Homework</th>
                <th>Submitted At</th>
                <th>Status</th>
                <th>Attachment</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const firstAttachment = item.attachments[0];
                const isLate = item.status.toLowerCase() === 'late';
                return (
                  <tr key={item.submission_id}>
                    <td>
                      <div className={styles.rowTitle}>{item.student_name}</div>
                      <div className={styles.rowMuted}>Phone: {item.contact ?? '-'}</div>
                      <div className={styles.rowMuted}>Adm: {item.admission_no ?? '-'}</div>
                    </td>
                    <td>{item.class_name} / {item.stream}</td>
                    <td>{item.homework_title}</td>
                    <td>{formatDateTime(item.submitted_at_ist ?? item.submitted_at)}</td>
                    <td>
                      <span className={`${styles.badge} ${isLate ? styles.badgeLate : styles.badgeOnTime}`.trim()}>
                        {item.status}
                      </span>
                    </td>
                    <td>
                      {firstAttachment ? (
                        <a className={styles.linkBtn} href={resolveMediaUrl(firstAttachment.file_url)} target="_blank" rel="noreferrer">
                          View PDF
                        </a>
                      ) : (
                        <span className={styles.rowMuted}>No file</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!loading && items.length === 0 ? (
                <tr>
                  <td colSpan={6} className={styles.rowMuted}>
                    No submissions found for current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
