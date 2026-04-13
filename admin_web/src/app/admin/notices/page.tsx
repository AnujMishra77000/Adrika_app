'use client';

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './notices.module.css';

type NoticeTarget = {
  target_type: string;
  target_id: string;
  label?: string;
};

type Notice = {
  id: string;
  title: string;
  status: string;
  priority: number;
  publish_at: string | null;
  attachment_count?: number;
  created_at?: string;
  targets?: NoticeTarget[];
};

type NoticeAttachment = {
  id: string;
  file_name: string;
  file_url: string;
  attachment_type: 'image' | 'pdf';
  file_size_bytes: number;
};

type TargetMode = 'all' | 'grade';
type NoticeStatusFilter = 'all' | 'draft' | 'published';

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '-';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(size >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function friendlyError(err: unknown, fallback: string): string {
  if (err instanceof Error) {
    const text = err.message.trim();
    if (!text) {
      return fallback;
    }

    try {
      const parsed = JSON.parse(text);
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
      return text;
    }

    return text;
  }

  return fallback;
}

export default function AdminNoticesPage() {
  const [items, setItems] = useState<Notice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<NoticeStatusFilter>('all');

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [priority, setPriority] = useState('0');
  const [targetMode, setTargetMode] = useState<TargetMode>('all');
  const [classLevel, setClassLevel] = useState<'10' | '11' | '12'>('10');
  const [stream, setStream] = useState<'science' | 'commerce'>('science');
  const [publishNow, setPublishNow] = useState(true);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  const selectedTargetPreview = useMemo(() => {
    if (targetMode === 'all') {
      return 'All students (10th, 11th, 12th)';
    }
    if (classLevel === '10') {
      return 'Class 10';
    }
    return `Class ${classLevel} ${stream === 'science' ? 'Science' : 'Commerce'}`;
  }, [classLevel, stream, targetMode]);

  const summaryCards = useMemo(() => {
    const published = items.filter((item) => item.status === 'published').length;
    const draft = items.filter((item) => item.status !== 'published').length;
    const attachments = items.reduce((sum, item) => sum + (item.attachment_count ?? 0), 0);

    return [
      { title: 'Total Notices', value: String(items.length) },
      { title: 'Published', value: String(published) },
      { title: 'Draft', value: String(draft) },
      { title: 'Attachments', value: String(attachments) },
    ];
  }, [items]);

  async function load(nextStatus: NoticeStatusFilter = statusFilter) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '100', offset: '0' });
      if (nextStatus !== 'all') {
        params.set('status', nextStatus);
      }
      const response = await apiRequest<{ items: Notice[] }>(`/api/v1/admin/notices?${params.toString()}`);
      setItems(response.items);
      setError(null);
    } catch (err) {
      setError(friendlyError(err, 'Failed to load notices'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  function buildTargets(): NoticeTarget[] {
    if (targetMode === 'all') {
      return [{ target_type: 'all_students', target_id: 'all' }];
    }

    if (classLevel === '10') {
      return [{ target_type: 'grade', target_id: '10' }];
    }

    return [{ target_type: 'grade', target_id: `${classLevel}:${stream}` }];
  }

  async function uploadAttachments(noticeId: string): Promise<NoticeAttachment[]> {
    if (files.length === 0) {
      return [];
    }

    const uploaded: NoticeAttachment[] = [];
    for (const file of files) {
      const form = new FormData();
      form.append('file', file);
      const response = await apiRequest<NoticeAttachment>(`/api/v1/admin/notices/${noticeId}/attachments`, {
        method: 'POST',
        body: form,
      });
      uploaded.push(response);
    }

    return uploaded;
  }

  async function createNotice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const create = await apiRequest<{ id: string }>('/api/v1/admin/notices', {
        method: 'POST',
        body: JSON.stringify({
          title,
          body,
          priority: Number(priority) || 0,
          targets: buildTargets(),
        }),
      });

      await uploadAttachments(create.id);

      if (publishNow) {
        await apiRequest(`/api/v1/admin/notices/${create.id}/publish`, { method: 'POST' });
      }

      setTitle('');
      setBody('');
      setPriority('0');
      setTargetMode('all');
      setClassLevel('10');
      setStream('science');
      setFiles([]);
      setPublishNow(true);
      await load(statusFilter);
    } catch (err) {
      setError(friendlyError(err, 'Failed to create notice'));
    } finally {
      setSaving(false);
    }
  }

  async function publishNotice(noticeId: string) {
    try {
      setError(null);
      await apiRequest(`/api/v1/admin/notices/${noticeId}/publish`, { method: 'POST' });
      await load(statusFilter);
    } catch (err) {
      setError(friendlyError(err, 'Failed to publish notice'));
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    setFiles(selected);
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Notices</h1>
          <p className={styles.subtitle}>Publish targeted notices to student notice board and notification bell.</p>
        </div>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.summaryGrid}>
        {summaryCards.map((card) => (
          <div className={styles.summaryCard} key={card.title}>
            <div className={styles.summaryLabel}>{card.title}</div>
            <div className={styles.summaryValue}>{card.value}</div>
          </div>
        ))}
      </div>

      <div className={styles.sectionTabs}>
        {([
          ['all', 'All Notices'],
          ['draft', 'Draft'],
          ['published', 'Published'],
        ] as const).map(([key, label]) => {
          const active = statusFilter === key;
          return (
            <button
              key={key}
              type="button"
              className={`${styles.tabButton} ${active ? styles.tabActive : ''}`.trim()}
              onClick={() => setStatusFilter(key)}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Create Notice</h3>
        <p className={styles.cardSubtle}>Upload image/PDF, select audience and publish in one flow.</p>
        <form onSubmit={createNotice}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Title</span>
            <input
              className={styles.input}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              minLength={2}
              maxLength={255}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Notice Content</span>
            <textarea
              className={styles.textarea}
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              minLength={5}
            />
          </label>

          <div className={styles.formGrid}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Priority</span>
              <input
                className={styles.input}
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                type="number"
                min={0}
                max={100}
              />
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Audience</span>
              <select className={styles.select} value={targetMode} onChange={(e) => setTargetMode(e.target.value as TargetMode)}>
                <option value="all">All Students</option>
                <option value="grade">Specific Class / Stream</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Class</span>
              <select
                className={styles.select}
                value={classLevel}
                onChange={(e) => setClassLevel(e.target.value as '10' | '11' | '12')}
                disabled={targetMode !== 'grade'}
              >
                <option value="10">10th</option>
                <option value="11">11th</option>
                <option value="12">12th</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Stream</span>
              <select
                className={styles.select}
                value={stream}
                onChange={(e) => setStream(e.target.value as 'science' | 'commerce')}
                disabled={targetMode !== 'grade' || classLevel === '10'}
              >
                <option value="science">Science</option>
                <option value="commerce">Commerce</option>
              </select>
            </label>
          </div>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Attachments (Images or PDF)</span>
            <input
              className={styles.input}
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              multiple
              onChange={onFileChange}
            />
          </label>

          {files.length > 0 ? (
            <div className={styles.fileList}>
              {files.map((file) => (
                <div key={`${file.name}-${file.size}`} className={styles.fileItem}>
                  {file.name} ({formatBytes(file.size)})
                </div>
              ))}
            </div>
          ) : null}

          <label className={styles.checkboxRow}>
            <input
              className={styles.checkbox}
              type="checkbox"
              checked={publishNow}
              onChange={(e) => setPublishNow(e.target.checked)}
            />
            <span className={styles.checkboxLabel}>Publish immediately and trigger student bell notification</span>
          </label>

          <p className={styles.targetPreview}>Target: {selectedTargetPreview}</p>

          <div className={styles.buttonRow}>
            <button className={styles.btnPrimary} type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Create Notice'}
            </button>
            <button className={styles.btnSecondary} type="button" onClick={() => load(statusFilter)} disabled={loading}>
              Refresh List
            </button>
          </div>
        </form>
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Notice List</h3>
        <p className={styles.cardSubtle}>Monitor publish status, audience and attachment count.</p>
        {loading ? (
          <p className={styles.muted}>Loading...</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Audience</th>
                  <th>Attachments</th>
                  <th>Status</th>
                  <th>Published At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isPublished = item.status === 'published';
                  return (
                    <tr key={item.id}>
                      <td>
                        <div style={{ fontWeight: 700 }}>{item.title}</div>
                        <div className={styles.priorityText}>Priority {item.priority}</div>
                      </td>
                      <td>
                        {(item.targets ?? []).length === 0 ? (
                          <span className={styles.muted}>-</span>
                        ) : (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {(item.targets ?? []).map((target, index) => (
                              <span key={`${target.target_type}-${target.target_id}-${index}`} className={styles.badge}>
                                {target.label ?? `${target.target_type}:${target.target_id}`}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td>{item.attachment_count ?? 0}</td>
                      <td>
                        <span className={`${styles.badge} ${isPublished ? styles.badgePublished : styles.badgeDraft}`.trim()}>
                          {item.status}
                        </span>
                      </td>
                      <td>{formatDate(item.publish_at)}</td>
                      <td>
                        <button
                          className={isPublished ? styles.btnSecondary : styles.btnSuccess}
                          onClick={() => publishNotice(item.id)}
                          disabled={isPublished}
                        >
                          {isPublished ? 'Published' : 'Publish'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className={styles.muted}>
                      No notices available for this filter.
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
