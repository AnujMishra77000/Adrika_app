'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './results.module.css';

type ScopeKey = '10' | '11_science' | '11_commerce' | '12_science' | '12_commerce';

type ScopeConfig = {
  key: ScopeKey;
  label: string;
  classLevel: number;
  stream: 'science' | 'commerce' | null;
};

const SCOPES: ScopeConfig[] = [
  { key: '10', label: '10th Class', classLevel: 10, stream: null },
  { key: '11_commerce', label: '11th Commerce', classLevel: 11, stream: 'commerce' },
  { key: '11_science', label: '11th Science', classLevel: 11, stream: 'science' },
  { key: '12_commerce', label: '12th Commerce', classLevel: 12, stream: 'commerce' },
  { key: '12_science', label: '12th Science', classLevel: 12, stream: 'science' },
];

type TopicItem = {
  assessment_id: string;
  assessment_title: string;
  topic: string | null;
  class_level: number;
  stream: string | null;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  question_count: number;
  submitted_count: number;
  avg_score: number | null;
  max_score: number | null;
  total_marks: number;
  passing_marks: number;
  last_published_at: string | null;
  subject: {
    id: string;
    code: string;
    name: string;
  };
};

type TopicStudentsResponse = {
  assessment: {
    id: string;
    title: string;
    topic: string | null;
    class_level: number | null;
    stream: string | null;
    starts_at: string | null;
    ends_at: string | null;
    total_marks: number;
    passing_marks: number;
    subject: {
      id: string;
      code: string;
      name: string;
    };
  };
  items: ResultStudentItem[];
};

type ResultStudentItem = {
  result_id: string;
  score: number;
  total_marks: number;
  percentage: number;
  rank: number;
  published_at: string;
  student: {
    id: string;
    name: string;
    phone: string | null;
    admission_no: string | null;
    roll_no: string | null;
    class_name: string | null;
    stream: string | null;
    parent_contact_number: string | null;
  };
};

function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function fmtScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return Number(value).toFixed(2);
}

function formatStream(stream: string | null | undefined): string {
  if (!stream) return 'General';
  const value = stream.trim().toLowerCase();
  if (!value) return 'General';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function AdminResultsPage() {
  const [scope, setScope] = useState<ScopeKey>('10');
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>('');
  const [topicSearch, setTopicSearch] = useState('');
  const [studentSearch, setStudentSearch] = useState('');

  const [loadingTopics, setLoadingTopics] = useState(false);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [sendingWhatsappByStudent, setSendingWhatsappByStudent] = useState<Record<string, boolean>>({});

  const [studentsPayload, setStudentsPayload] = useState<TopicStudentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const activeScope = useMemo(() => SCOPES.find((item) => item.key === scope) ?? SCOPES[0], [scope]);

  async function loadTopics(nextScope: ScopeConfig = activeScope, search: string = topicSearch) {
    setLoadingTopics(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        class_level: String(nextScope.classLevel),
        limit: '100',
        offset: '0',
      });
      if (nextScope.stream) {
        params.set('stream', nextScope.stream);
      }
      if (search.trim()) {
        params.set('search', search.trim());
      }

      const response = await apiRequest<{ items: TopicItem[] }>(`/api/v1/admin/results/topics?${params.toString()}`);
      setTopics(response.items);

      if (response.items.length === 0) {
        setSelectedAssessmentId('');
        setStudentsPayload(null);
      } else {
        const stillExists = response.items.some((item) => item.assessment_id === selectedAssessmentId);
        if (!selectedAssessmentId || !stillExists) {
          setSelectedAssessmentId(response.items[0].assessment_id);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load result topics');
    } finally {
      setLoadingTopics(false);
    }
  }

  async function loadTopicStudents(assessmentId: string, search: string = studentSearch) {
    if (!assessmentId) {
      setStudentsPayload(null);
      return;
    }

    setLoadingStudents(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: '200',
        offset: '0',
      });
      if (search.trim()) {
        params.set('search', search.trim());
      }

      const response = await apiRequest<TopicStudentsResponse>(
        `/api/v1/admin/results/topics/${assessmentId}/students?${params.toString()}`,
      );
      setStudentsPayload(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load topic results');
      setStudentsPayload(null);
    } finally {
      setLoadingStudents(false);
    }
  }

  useEffect(() => {
    void loadTopics(activeScope, topicSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeScope.key]);

  useEffect(() => {
    if (!selectedAssessmentId) {
      setStudentsPayload(null);
      return;
    }
    void loadTopicStudents(selectedAssessmentId, studentSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAssessmentId]);

  const groupedTopics = useMemo(() => {
    const map = new Map<string, TopicItem[]>();
    for (const item of topics) {
      const key = `${item.subject.code} - ${item.subject.name}`;
      const arr = map.get(key) ?? [];
      arr.push(item);
      map.set(key, arr);
    }
    return Array.from(map.entries()).map(([subjectLabel, items]) => ({ subjectLabel, items }));
  }, [topics]);

  const summary = useMemo(() => {
    const totalTests = topics.length;
    const totalSubmissions = topics.reduce((acc, item) => acc + item.submitted_count, 0);
    const avgScores = topics.filter((item) => item.avg_score !== null).map((item) => item.avg_score as number);
    const avgOfAvg = avgScores.length > 0 ? avgScores.reduce((a, b) => a + b, 0) / avgScores.length : 0;

    return {
      totalTests,
      totalSubmissions,
      avgOfAvg,
    };
  }, [topics]);

  async function handleSendWhatsapp(student: ResultStudentItem) {
    const studentId = student.student.id;
    setSendingWhatsappByStudent((state) => ({ ...state, [studentId]: true }));
    setError(null);
    setSuccess(null);

    try {
      const response = await apiRequest<{ delivery_status: string; to_phone: string | null }>(
        `/api/v1/admin/results/topics/${selectedAssessmentId}/students/${studentId}/whatsapp`,
        {
          method: 'POST',
          body: JSON.stringify({}),
        },
      );
      setSuccess(
        `Result sent to parent (${response.to_phone ?? 'N/A'}) with status: ${response.delivery_status}.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send result on WhatsApp');
    } finally {
      setSendingWhatsappByStudent((state) => ({ ...state, [studentId]: false }));
    }
  }

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Result Center</h1>
          <p className={styles.subtitle}>
            Class-wise result management with subject/topic history, rank view, and one-click WhatsApp report card delivery.
          </p>
        </div>
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}
      {success ? <p className={styles.success}>{success}</p> : null}

      <div className={styles.scopeRow}>
        {SCOPES.map((item) => (
          <button
            key={item.key}
            type="button"
            className={item.key === activeScope.key ? styles.scopeBtnActive : styles.scopeBtn}
            onClick={() => {
              setScope(item.key);
              setTopicSearch('');
              setStudentSearch('');
              setSuccess(null);
              setError(null);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span>Total Tests</span>
          <strong>{summary.totalTests}</strong>
        </div>
        <div className={styles.summaryCard}>
          <span>Total Submissions</span>
          <strong>{summary.totalSubmissions}</strong>
        </div>
        <div className={styles.summaryCard}>
          <span>Average Score (Topic Avg)</span>
          <strong>{summary.avgOfAvg.toFixed(2)}</strong>
        </div>
      </div>

      <div className={styles.layout}>
        <section className={styles.leftPanel}>
          <div className={styles.panelHeader}>
            <h3>Subject & Topic Tests</h3>
            <div className={styles.searchRow}>
              <input
                className={styles.input}
                placeholder="Search subject, topic or test title"
                value={topicSearch}
                onChange={(event) => setTopicSearch(event.target.value)}
              />
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={() => void loadTopics(activeScope, topicSearch)}
                disabled={loadingTopics}
              >
                {loadingTopics ? 'Loading...' : 'Apply'}
              </button>
            </div>
          </div>

          {loadingTopics ? <p className={styles.loading}>Loading topics...</p> : null}

          {!loadingTopics && groupedTopics.length === 0 ? (
            <p className={styles.empty}>No submitted assessments found for this class section.</p>
          ) : null}

          {groupedTopics.map((group) => (
            <div key={group.subjectLabel} className={styles.subjectGroup}>
              <h4>{group.subjectLabel}</h4>
              {group.items.map((topic) => {
                const selected = topic.assessment_id === selectedAssessmentId;
                return (
                  <button
                    type="button"
                    key={topic.assessment_id}
                    className={selected ? styles.topicCardActive : styles.topicCard}
                    onClick={() => {
                      setSelectedAssessmentId(topic.assessment_id);
                      setSuccess(null);
                    }}
                  >
                    <div className={styles.topicTitle}>{topic.topic || topic.assessment_title}</div>
                    <div className={styles.topicSub}>{topic.assessment_title}</div>
                    <div className={styles.topicMeta}>
                      <span>Time: {fmtDateTime(topic.starts_at)}</span>
                      <span>Submitted: {topic.submitted_count}</span>
                      <span>Avg: {fmtScore(topic.avg_score)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </section>

        <section className={styles.rightPanel}>
          <div className={styles.panelHeader}>
            <h3>Student Result Sheet</h3>
            <div className={styles.searchRow}>
              <input
                className={styles.input}
                placeholder="Search student name / phone / admission / parent number"
                value={studentSearch}
                onChange={(event) => setStudentSearch(event.target.value)}
              />
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={() => void loadTopicStudents(selectedAssessmentId, studentSearch)}
                disabled={!selectedAssessmentId || loadingStudents}
              >
                {loadingStudents ? 'Loading...' : 'Apply'}
              </button>
            </div>
          </div>

          {studentsPayload?.assessment ? (
            <div className={styles.assessmentMeta}>
              <span><strong>Test:</strong> {studentsPayload.assessment.title}</span>
              <span><strong>Topic:</strong> {studentsPayload.assessment.topic || '-'}</span>
              <span>
                <strong>Class:</strong> {studentsPayload.assessment.class_level ?? '-'} {formatStream(studentsPayload.assessment.stream)}
              </span>
              <span>
                <strong>Subject:</strong> {studentsPayload.assessment.subject.code} - {studentsPayload.assessment.subject.name}
              </span>
              <span><strong>Time:</strong> {fmtDateTime(studentsPayload.assessment.starts_at)}</span>
            </div>
          ) : null}

          {loadingStudents ? <p className={styles.loading}>Loading result sheet...</p> : null}

          {!loadingStudents && (!studentsPayload || studentsPayload.items.length === 0) ? (
            <p className={styles.empty}>Select a test topic to view submitted student results.</p>
          ) : null}

          {studentsPayload && studentsPayload.items.length > 0 ? (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Class</th>
                    <th>Marks</th>
                    <th>%</th>
                    <th>Rank</th>
                    <th>Published</th>
                    <th>Parent WhatsApp</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {studentsPayload.items.map((item) => (
                    <tr key={item.result_id}>
                      <td>
                        <div className={styles.studentName}>{item.student.name}</div>
                        <div className={styles.studentSub}>
                          Adm: {item.student.admission_no || '-'} | Roll: {item.student.roll_no || '-'}
                        </div>
                      </td>
                      <td>{item.student.class_name || '-'} ({formatStream(item.student.stream)})</td>
                      <td>{fmtScore(item.score)} / {fmtScore(item.total_marks)}</td>
                      <td>{fmtScore(item.percentage)}</td>
                      <td>{item.rank}</td>
                      <td>{fmtDateTime(item.published_at)}</td>
                      <td>{item.student.parent_contact_number || '-'}</td>
                      <td>
                        <button
                          type="button"
                          className={styles.btnPrimary}
                          onClick={() => void handleSendWhatsapp(item)}
                          disabled={Boolean(sendingWhatsappByStudent[item.student.id])}
                        >
                          {sendingWhatsappByStudent[item.student.id] ? 'Sending...' : 'Send WhatsApp'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
