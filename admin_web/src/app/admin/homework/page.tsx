'use client';

import Link from 'next/link';
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './homework.module.css';

type HomeworkTarget = {
  target_type: string;
  target_id: string;
  label?: string;
};

type Homework = {
  id: string;
  title: string;
  description: string;
  subject_id: string;
  status: string;
  due_date: string | null;
  due_at: string | null;
  publish_at: string | null;
  expires_at: string | null;
  attachment_count: number;
  targets: HomeworkTarget[];
};

type Subject = {
  id: string;
  code: string;
  name: string;
};

type TargetMode = 'all' | 'grade';
type HomeworkStatusFilter = 'all' | 'draft' | 'published';

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '-';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
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

function targetText(target: HomeworkTarget): string {
  if (target.label && target.label.trim()) {
    return target.label;
  }

  if (target.target_type === 'all_students') {
    return 'All Students';
  }
  if (target.target_type === 'grade') {
    return 'Class ' + target.target_id;
  }
  return target.target_type + ':' + target.target_id;
}

function toLocalDateTimeInputValue(date: Date): string {
  const pad = (value: number) => value.toString().padStart(2, '0');
  const yyyy = date.getFullYear();
  const mm = pad(date.getMonth() + 1);
  const dd = pad(date.getDate());
  const hh = pad(date.getHours());
  const min = pad(date.getMinutes());
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
}

export default function AdminHomeworkPage() {
  const [items, setItems] = useState<Homework[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishingId, setPublishingId] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<HomeworkStatusFilter>('all');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [dueAt, setDueAt] = useState('');
  const [targetMode, setTargetMode] = useState<TargetMode>('all');
  const [classLevel, setClassLevel] = useState<'10' | '11' | '12'>('10');
  const [stream, setStream] = useState<'science' | 'commerce'>('science');
  const [publishNow, setPublishNow] = useState(true);
  const [files, setFiles] = useState<File[]>([]);

  const selectedTargetPreview = useMemo(() => {
    if (targetMode === 'all') {
      return 'All students (10th, 11th, 12th)';
    }
    if (classLevel === '10') {
      return 'Class 10';
    }
    return 'Class ' + classLevel + ' ' + (stream === 'science' ? 'Science' : 'Commerce');
  }, [classLevel, stream, targetMode]);

  const summaryCards = useMemo(() => {
    const published = items.filter((item) => item.status === 'published').length;
    const draft = items.filter((item) => item.status !== 'published').length;
    const activeWindow = items.filter((item) => {
      if (item.status !== 'published') {
        return false;
      }
      if (!item.expires_at) {
        return true;
      }
      return new Date(item.expires_at).getTime() > Date.now();
    }).length;
    const attachments = items.reduce((sum, item) => sum + (item.attachment_count ?? 0), 0);

    return [
      { title: 'Total Homework', value: String(items.length) },
      { title: 'Published', value: String(published) },
      { title: 'Draft', value: String(draft) },
      { title: 'Active Window', value: String(activeWindow) },
      { title: 'Attachments', value: String(attachments) },
    ];
  }, [items]);

  async function loadSubjects() {
    const response = await apiRequest<{ items: Subject[] }>('/api/v1/admin/subjects?limit=100&offset=0');
    setSubjects(response.items);
    if (!subjectId && response.items.length > 0) {
      setSubjectId(response.items[0].id);
    }
  }

  async function loadHomework(nextStatus: HomeworkStatusFilter = statusFilter) {
    const params = new URLSearchParams({ limit: '100', offset: '0' });
    if (nextStatus !== 'all') {
      params.set('status', nextStatus);
    }

    const response = await apiRequest<{ items: Homework[] }>(`/api/v1/admin/homework?${params.toString()}`);
    setItems(response.items);
  }

  async function bootstrap() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadSubjects(), loadHomework('all')]);
      if (!dueAt) {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 30);
        setDueAt(toLocalDateTimeInputValue(now));
      }
    } catch (err) {
      setError(friendlyError(err, 'Failed to load homework module'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (loading) {
      return;
    }

    void (async () => {
      try {
        setError(null);
        await loadHomework(statusFilter);
      } catch (err) {
        setError(friendlyError(err, 'Failed to load homework list'));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  function buildTargets(): HomeworkTarget[] {
    if (targetMode === 'all') {
      return [{ target_type: 'all_students', target_id: 'all' }];
    }

    if (classLevel === '10') {
      return [{ target_type: 'grade', target_id: '10' }];
    }

    return [{ target_type: 'grade', target_id: classLevel + ':' + stream }];
  }

  async function uploadAttachments(homeworkId: string): Promise<void> {
    if (files.length === 0) {
      return;
    }

    for (const file of files) {
      const form = new FormData();
      form.append('file', file);
      await apiRequest(`/api/v1/admin/homework/${homeworkId}/attachments`, {
        method: 'POST',
        body: form,
      });
    }
  }

  async function createHomework(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }

    if (!subjectId) {
      setError('Please select a subject before creating homework.');
      return;
    }

    if (!dueAt) {
      setError('Please set completion date and time.');
      return;
    }

    const dueDateValue = new Date(dueAt);
    if (Number.isNaN(dueDateValue.getTime())) {
      setError('Please select a valid completion date and time.');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const createBody: Record<string, unknown> = {
        title: title.trim(),
        subject_id: subjectId,
        due_at: dueDateValue.toISOString(),
        targets: buildTargets(),
      };
      const instruction = description.trim();
      if (instruction) {
        createBody.description = instruction;
      }

      const createResponse = await apiRequest<{ id: string }>('/api/v1/admin/homework', {
        method: 'POST',
        body: JSON.stringify(createBody),
      });

      await uploadAttachments(createResponse.id);

      if (publishNow) {
        await apiRequest(`/api/v1/admin/homework/${createResponse.id}/publish`, { method: 'POST' });
      }

      setTitle('');
      setDescription('');
      setFiles([]);
      setTargetMode('all');
      setClassLevel('10');
      setStream('science');
      setPublishNow(true);
      setDueAt(toLocalDateTimeInputValue(new Date(Date.now() + 30 * 60 * 1000)));

      await loadHomework(statusFilter);
    } catch (err) {
      setError(friendlyError(err, 'Failed to create homework'));
    } finally {
      setSaving(false);
    }
  }

  async function publishHomework(homeworkId: string) {
    if (publishingId) {
      return;
    }

    setPublishingId(homeworkId);
    setError(null);
    try {
      await apiRequest(`/api/v1/admin/homework/${homeworkId}/publish`, { method: 'POST' });
      await loadHomework(statusFilter);
    } catch (err) {
      setError(friendlyError(err, 'Failed to publish homework'));
    } finally {
      setPublishingId(null);
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []).filter((file) => {
      return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    });
    setFiles(selected);
  }

  const isBusy = loading || saving;

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Homework</h1>
          <p className={styles.subtitle}>
            Create and publish homework in IST, collect student PDF submissions, and monitor completions in one flow.
          </p>
        </div>
        <div className={styles.buttonRow}>
          <Link className={styles.btnNeutral} href="/admin/homework/completions">
            Homework Completion
          </Link>
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
          ['all', 'All Homework'],
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
              disabled={loading}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Create Homework</h3>
        <p className={styles.cardSubtle}>
          Instruction text is optional. If provided, it is auto-converted into a homework PDF sheet.
        </p>

        <form onSubmit={createHomework}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Homework Title</span>
            <input
              className={styles.input}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
              minLength={2}
              maxLength={255}
              placeholder="Chapter 5 Algebra Practice"
            />
          </label>

          <div className={styles.formGridCompact}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Subject</span>
              <select
                className={styles.select}
                value={subjectId}
                onChange={(event) => setSubjectId(event.target.value)}
                required
              >
                <option value="">Select subject</option>
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.code} - {subject.name}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Completion Time (IST)</span>
              <input
                className={styles.input}
                type="datetime-local"
                step={60}
                value={dueAt}
                onChange={(event) => setDueAt(event.target.value)}
                required
              />
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Audience</span>
              <select
                className={styles.select}
                value={targetMode}
                onChange={(event) => setTargetMode(event.target.value as TargetMode)}
              >
                <option value="all">All Students</option>
                <option value="grade">Specific Class / Stream</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Class</span>
              <select
                className={styles.select}
                value={classLevel}
                onChange={(event) => setClassLevel(event.target.value as '10' | '11' | '12')}
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
                onChange={(event) => setStream(event.target.value as 'science' | 'commerce')}
                disabled={targetMode !== 'grade' || classLevel === '10'}
              >
                <option value="science">Science</option>
                <option value="commerce">Commerce</option>
              </select>
            </label>
          </div>

          <div className={styles.targetPreview}>{selectedTargetPreview}</div>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Instruction (optional)</span>
            <textarea
              className={styles.textarea}
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional notes for students..."
            />
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Attach PDF (optional)</span>
            <input className={styles.input} type="file" multiple accept="application/pdf,.pdf" onChange={onFileChange} />
          </label>

          {files.length > 0 ? (
            <div className={styles.fileList}>
              {files.map((file) => (
                <div className={styles.fileItem} key={`${file.name}-${file.size}`}>
                  {file.name} ({Math.max(1, Math.round(file.size / 1024))} KB)
                </div>
              ))}
            </div>
          ) : null}

          <label className={styles.checkboxRow}>
            <input
              className={styles.checkbox}
              type="checkbox"
              checked={publishNow}
              onChange={(event) => setPublishNow(event.target.checked)}
            />
            <span className={styles.checkboxLabel}>Publish immediately after create</span>
          </label>

          <div className={styles.buttonRow}>
            <button className={styles.btnPrimary} type="submit" disabled={isBusy}>
              {saving ? 'Creating...' : 'Create Homework'}
            </button>
            <button
              className={styles.btnSecondary}
              type="button"
              onClick={() => {
                setTitle('');
                setDescription('');
                setFiles([]);
                setTargetMode('all');
                setClassLevel('10');
                setStream('science');
                setPublishNow(true);
                setDueAt(toLocalDateTimeInputValue(new Date(Date.now() + 30 * 60 * 1000)));
              }}
              disabled={isBusy}
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      <div className={styles.card}>
        <h3 className={styles.cardTitle}>Homework List</h3>
        <p className={styles.cardSubtle}>Track published tasks, expiry windows and attachment volume.</p>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Homework</th>
                <th>Targets</th>
                <th>Due</th>
                <th>Expires</th>
                <th>Status</th>
                <th>Attachments</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const status = item.status.toLowerCase();
                const isPublished = status === 'published';
                const badgeClass = isPublished ? `${styles.badge} ${styles.badgePublished}` : `${styles.badge} ${styles.badgeDraft}`;
                const dueText = formatDateTime(item.due_at ?? item.due_date);
                const expiresText = formatDateTime(item.expires_at);

                return (
                  <tr key={item.id}>
                    <td>
                      <div className={styles.rowTitle}>{item.title}</div>
                      <div className={styles.rowDescription}>{item.description || 'No instruction added.'}</div>
                    </td>
                    <td>
                      {item.targets.length > 0 ? item.targets.map(targetText).join(' | ') : <span className={styles.muted}>-</span>}
                    </td>
                    <td>{dueText}</td>
                    <td>{expiresText}</td>
                    <td>
                      <span className={badgeClass}>{item.status}</span>
                    </td>
                    <td>{item.attachment_count}</td>
                    <td>
                      {isPublished ? (
                        <span className={styles.badge}>Published</span>
                      ) : (
                        <button
                          type="button"
                          className={styles.btnSuccess}
                          onClick={() => publishHomework(item.id)}
                          disabled={publishingId !== null}
                        >
                          {publishingId === item.id ? 'Publishing...' : 'Publish'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!loading && items.length === 0 ? (
                <tr>
                  <td colSpan={7} className={styles.muted}>
                    No homework records found for this filter.
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
