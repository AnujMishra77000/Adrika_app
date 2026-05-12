
'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './page.module.css';

type CredentialItem = {
  student_id: string;
  user_id: string;
  full_name: string;
  login_id: string | null;
  status: 'active' | 'inactive' | 'suspended' | string;
  class_name: string | null;
  stream: string | null;
  parent_contact_number: string | null;
  credentials_ready: boolean;
  current_password: string | null;
  password_last_updated_at?: string | null;
  batch: {
    id: string;
    name: string;
    academic_year: number;
    standard_name: string | null;
  } | null;
};

export default function StudentCredentialsPage() {
  const [items, setItems] = useState<CredentialItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [classLevel, setClassLevel] = useState('all');
  const [stream, setStream] = useState('all');
  const [status, setStatus] = useState('all');

  const activeFilters = useMemo(() => ({ search, classLevel, stream, status }), [search, classLevel, stream, status]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('limit', '200');
      params.set('offset', '0');
      if (activeFilters.search.trim()) params.set('search', activeFilters.search.trim());
      if (activeFilters.classLevel !== 'all') params.set('class_level', activeFilters.classLevel);
      if (activeFilters.stream !== 'all') params.set('stream', activeFilters.stream);
      if (activeFilters.status !== 'all') params.set('status', activeFilters.status);

      const response = await apiRequest<{ items: CredentialItem[] }>(`/api/v1/admin/students/credentials?${params.toString()}`);
      setItems(response.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student credentials');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeFilters]);

  async function onResetPassword(item: CredentialItem) {
    setError(null);
    setSuccess(null);

    const entered = window.prompt(
      `Enter new password for ${item.full_name} (6-8 chars letters+numbers). Leave empty for auto-generate:`,
      '',
    );

    if (entered === null) {
      return;
    }

    const newPassword = entered.trim();

    try {
      const response = await apiRequest<{
        login_id: string;
        temporary_password: string;
        generated: boolean;
      }>(`/api/v1/admin/students/${item.student_id}/credentials/reset`, {
        method: 'POST',
        body: JSON.stringify({
          new_password: newPassword.length > 0 ? newPassword : null,
        }),
      });

      setSuccess(
        `Credentials updated for ${item.full_name}. Login ID: ${response.login_id}, Password: ${response.temporary_password}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset student password');
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Student Credentials</h1>
          <p className={styles.subtitle}>
            Admin-managed login IDs (phone) and password reset controls, class-wise and section-wise.
          </p>
        </div>
        <Link className={styles.backLink} href="/admin/students">
          Back to Student Ops
        </Link>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {success ? <p className={styles.success}>{success}</p> : null}

      <div className={styles.filters}>
        <input
          className={styles.input}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name / phone / admission no"
        />

        <select className={styles.input} value={classLevel} onChange={(e) => setClassLevel(e.target.value)}>
          <option value="all">All Classes</option>
          <option value="0">JrKG-5</option>
          <option value="6">6th</option>
          <option value="7">7th</option>
          <option value="8">8th</option>
          <option value="9">9th</option>
          <option value="10">10th</option>
          <option value="11">11th</option>
          <option value="12">12th</option>
        </select>

        <select className={styles.input} value={stream} onChange={(e) => setStream(e.target.value)}>
          <option value="all">All Streams</option>
          <option value="science">Science</option>
          <option value="commerce">Commerce</option>
        </select>

        <select className={styles.input} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Student</th>
              <th>Class</th>
              <th>Stream</th>
              <th>Login ID</th>
              <th>Parent Contact</th>
              <th>Status</th>
              <th>Credentials</th>
              <th>Password</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9}>Loading...</td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9}>No students found for selected filters.</td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.student_id}>
                  <td>
                    <div className={styles.name}>{item.full_name}</div>
                    <div className={styles.meta}>{item.batch?.name ?? '-'}</div>
                  </td>
                  <td>{item.class_name ?? item.batch?.standard_name ?? '-'}</td>
                  <td>{item.stream ?? '-'}</td>
                  <td>{item.login_id ?? '-'}</td>
                  <td>{item.parent_contact_number ?? '-'}</td>
                  <td className={styles.capitalize}>{item.status}</td>
                  <td>
                    <span className={item.credentials_ready ? styles.ready : styles.missing}>
                      {item.credentials_ready ? 'Ready' : 'Missing'}
                    </span>
                  </td>
                  <td>{item.current_password ?? "-"}</td>
                  <td>
                    <button className={styles.resetButton} type="button" onClick={() => onResetPassword(item)}>
                      Reset Password
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
