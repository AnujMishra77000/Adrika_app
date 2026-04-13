'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './assessments.module.css';

type SectionKey = 'save' | 'create' | 'assign';

type Subject = {
  id: string;
  code: string;
  name: string;
  scopes?: Array<{
    class_level: number;
    stream: 'science' | 'commerce' | null;
  }>;
};

type OptionItem = {
  key: string;
  text: string;
};

type QuestionBankItem = {
  id: string;
  class_level: number;
  stream: 'science' | 'commerce' | null;
  topic: string | null;
  prompt: string;
  options: OptionItem[];
  correct_option_key: string;
  default_marks: number;
  difficulty: string | null;
  is_active: boolean;
  subject: Subject;
  updated_at: string;
};

type AssessmentItem = {
  id: string;
  title: string;
  subject_id: string;
  assessment_type: string;
  status: string;
  starts_at: string | null;
  ends_at: string | null;
  duration_sec: number;
  attempt_limit: number;
};

type AssessmentQuestionPaper = {
  assessment: {
    id: string;
    title: string;
    status: string;
    class_level: number | null;
    stream: string | null;
    subject_id: string;
    topic: string | null;
    total_marks: number;
    passing_marks: number;
  };
  items: Array<{
    seq_no: number;
    question_id: string;
    prompt: string;
    options: OptionItem[];
    marks: number;
  }>;
};

type QuestionSelection = {
  question_id: string;
  marks: number;
  negative_marks: number;
};

const SECTION_LABELS: Record<SectionKey, string> = {
  save: 'Save Test',
  create: 'Create Test',
  assign: 'Assign Test',
};

const AUDIENCE_OPTIONS = [
  { value: 'all', label: 'All Students' },
  { value: '10', label: 'Class 10' },
  { value: '11:science', label: 'Class 11 Science' },
  { value: '11:commerce', label: 'Class 11 Commerce' },
  { value: '12:science', label: 'Class 12 Science' },
  { value: '12:commerce', label: 'Class 12 Commerce' },
] as const;

function cls(...items: Array<string | false | null | undefined>) {
  return items.filter(Boolean).join(' ');
}

function toInputDateTime(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hour = String(value.getHours()).padStart(2, '0');
  const minute = String(value.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function toDisplayDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function streamRequired(classLevel: number): boolean {
  return classLevel === 11 || classLevel === 12;
}

function normalizeScopeStream(classLevel: number, stream: string): 'science' | 'commerce' | null {
  if (!streamRequired(classLevel)) {
    return null;
  }
  return stream === 'science' ? 'science' : stream === 'commerce' ? 'commerce' : null;
}

function subjectMatchesScope(subject: Subject, classLevel: number, stream: string): boolean {
  const scopes = subject.scopes ?? [];
  if (scopes.length === 0) {
    // Legacy subjects without scope mapping are treated as globally available.
    return true;
  }

  const targetStream = normalizeScopeStream(classLevel, stream);
  return scopes.some((scope) => {
    if (scope.class_level !== classLevel) {
      return false;
    }
    if (!streamRequired(classLevel)) {
      return true;
    }
    return scope.stream === targetStream;
  });
}

function subjectName(subjects: Subject[], subjectId: string): string {
  const found = subjects.find((subject) => subject.id === subjectId);
  return found ? `${found.code} - ${found.name}` : subjectId;
}

export default function AdminAssessmentsPage() {
  const [section, setSection] = useState<SectionKey>('save');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [assessments, setAssessments] = useState<AssessmentItem[]>([]);
  const [questionBank, setQuestionBank] = useState<QuestionBankItem[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [savingQuestion, setSavingQuestion] = useState(false);
  const [deletingQuestionId, setDeletingQuestionId] = useState<string | null>(null);
  const [creatingTest, setCreatingTest] = useState(false);
  const [assigningTest, setAssigningTest] = useState(false);

  const [saveClassLevel, setSaveClassLevel] = useState('10');
  const [saveStream, setSaveStream] = useState<'science' | 'commerce' | ''>('');
  const [saveSubjectSearch, setSaveSubjectSearch] = useState('');
  const [saveSubjectId, setSaveSubjectId] = useState('');
  const [saveTopic, setSaveTopic] = useState('');
  const [savePrompt, setSavePrompt] = useState('');
  const [saveDifficulty, setSaveDifficulty] = useState<'easy' | 'medium' | 'hard'>('easy');
  const [saveDefaultMarks, setSaveDefaultMarks] = useState('1');
  const [saveCorrectKey, setSaveCorrectKey] = useState<'A' | 'B' | 'C' | 'D'>('A');
  const [saveOptionA, setSaveOptionA] = useState('');
  const [saveOptionB, setSaveOptionB] = useState('');
  const [saveOptionC, setSaveOptionC] = useState('');
  const [saveOptionD, setSaveOptionD] = useState('');

  const [filterClassLevel, setFilterClassLevel] = useState('');
  const [filterStream, setFilterStream] = useState('');
  const [filterSubjectId, setFilterSubjectId] = useState('');
  const [filterTopic, setFilterTopic] = useState('');
  const [filterSearch, setFilterSearch] = useState('');

  const [createTitle, setCreateTitle] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createClassLevel, setCreateClassLevel] = useState('10');
  const [createStream, setCreateStream] = useState<'science' | 'commerce' | ''>('');
  const [createSubjectSearch, setCreateSubjectSearch] = useState('');
  const [createSubjectId, setCreateSubjectId] = useState('');
  const [createTopic, setCreateTopic] = useState('');
  const [createType, setCreateType] = useState<'daily_practice' | 'subject_practice' | 'scheduled'>('scheduled');
  const [createDurationMinutes, setCreateDurationMinutes] = useState('30');
  const [createAttemptLimit, setCreateAttemptLimit] = useState('1');
  const [createPassingMarks, setCreatePassingMarks] = useState('0');
  const [questionSelection, setQuestionSelection] = useState<Record<string, QuestionSelection>>({});

  const [selectedAssessmentId, setSelectedAssessmentId] = useState('');
  const [selectedAudience, setSelectedAudience] = useState<(typeof AUDIENCE_OPTIONS)[number]['value']>('all');
  const [assignStartsAt, setAssignStartsAt] = useState(() => {
    const base = new Date();
    base.setMinutes(base.getMinutes() + 10);
    return toInputDateTime(base);
  });
  const [assignEndsAt, setAssignEndsAt] = useState(() => {
    const base = new Date();
    base.setMinutes(base.getMinutes() + 70);
    return toInputDateTime(base);
  });
  const [sendNotification, setSendNotification] = useState(true);
  const [publishNow, setPublishNow] = useState(true);
  const [paper, setPaper] = useState<AssessmentQuestionPaper | null>(null);

  const [newSubjectName, setNewSubjectName] = useState('');
  const [newSubjectCode, setNewSubjectCode] = useState('');
  const [newSubjectClassLevel, setNewSubjectClassLevel] = useState('10');
  const [newSubjectStream, setNewSubjectStream] = useState<'science' | 'commerce' | ''>('');
  const [creatingSubject, setCreatingSubject] = useState(false);

  const selectedQuestions = useMemo(() => {
    return Object.values(questionSelection);
  }, [questionSelection]);

  const saveSubjectOptions = useMemo(() => {
    const classLevel = Number(saveClassLevel);
    const search = saveSubjectSearch.trim().toLowerCase();
    return subjects.filter((subject) => {
      if (!subjectMatchesScope(subject, classLevel, saveStream)) return false;
      if (!search) return true;
      return (
        subject.name.toLowerCase().includes(search) ||
        subject.code.toLowerCase().includes(search)
      );
    });
  }, [subjects, saveClassLevel, saveStream, saveSubjectSearch]);

  const createSubjectOptions = useMemo(() => {
    const classLevel = Number(createClassLevel);
    const search = createSubjectSearch.trim().toLowerCase();
    return subjects.filter((subject) => {
      if (!subjectMatchesScope(subject, classLevel, createStream)) return false;
      if (!search) return true;
      return (
        subject.name.toLowerCase().includes(search) ||
        subject.code.toLowerCase().includes(search)
      );
    });
  }, [subjects, createClassLevel, createStream, createSubjectSearch]);

  const selectedQuestionCount = selectedQuestions.length;
  const selectedTotalMarks = selectedQuestions.reduce((sum, item) => sum + item.marks, 0);

  async function loadCore() {
    setLoading(true);
    setError(null);
    try {
      const [subjectsRes, assessmentsRes] = await Promise.all([
        apiRequest<{ items: Subject[] }>('/api/v1/admin/subjects?limit=100&offset=0'),
        apiRequest<{ items: AssessmentItem[] }>('/api/v1/admin/assessments?limit=100&offset=0'),
      ]);

      setSubjects(subjectsRes.items);
      setAssessments(assessmentsRes.items);

      if (!saveSubjectId && subjectsRes.items.length > 0) {
        setSaveSubjectId(subjectsRes.items[0].id);
      }
      if (!createSubjectId && subjectsRes.items.length > 0) {
        setCreateSubjectId(subjectsRes.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessment module');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateSubject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingSubject(true);
    setError(null);
    setSuccess(null);

    try {
      const classLevel = Number(newSubjectClassLevel);
      const payload = {
        name: newSubjectName.trim(),
        code: newSubjectCode.trim() || null,
        class_level: classLevel,
        stream: streamRequired(classLevel) ? newSubjectStream || null : null,
      };

      const created = await apiRequest<Subject>('/api/v1/admin/subjects', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setSuccess(`Subject ${created.code} - ${created.name} is ready.`);
      setNewSubjectName('');
      setNewSubjectCode('');

      await loadCore();

      const scopeMatchesSave =
        Number(saveClassLevel) === classLevel &&
        (!streamRequired(classLevel) || saveStream === payload.stream);
      if (scopeMatchesSave) {
        setSaveSubjectId(created.id);
      }

      const scopeMatchesCreate =
        Number(createClassLevel) === classLevel &&
        (!streamRequired(classLevel) || createStream === payload.stream);
      if (scopeMatchesCreate) {
        setCreateSubjectId(created.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create subject');
    } finally {
      setCreatingSubject(false);
    }
  }

  async function loadQuestionBank(params?: {
    class_level?: string;
    stream?: string;
    subject_id?: string;
    topic?: string;
    search?: string;
  }) {
    setLoadingQuestions(true);
    try {
      const query = new URLSearchParams({
        limit: '100',
        offset: '0',
      });

      const classLevel = params?.class_level ?? filterClassLevel;
      const stream = params?.stream ?? filterStream;
      const subjectId = params?.subject_id ?? filterSubjectId;
      const topic = params?.topic ?? filterTopic;
      const search = params?.search ?? filterSearch;

      if (classLevel) query.set('class_level', classLevel);
      if (stream) query.set('stream', stream);
      if (subjectId) query.set('subject_id', subjectId);
      if (topic.trim()) query.set('topic', topic.trim());
      if (search.trim()) query.set('search', search.trim());

      const response = await apiRequest<{ items: QuestionBankItem[] }>(
        `/api/v1/admin/assessments/question-bank?${query.toString()}`,
      );
      setQuestionBank(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch question bank');
    } finally {
      setLoadingQuestions(false);
    }
  }

  async function loadQuestionPaper(assessmentId: string) {
    if (!assessmentId) {
      setPaper(null);
      return;
    }

    try {
      const response = await apiRequest<AssessmentQuestionPaper>(`/api/v1/admin/assessments/${assessmentId}/questions`);
      setPaper(response);
    } catch (err) {
      setPaper(null);
      setError(err instanceof Error ? err.message : 'Failed to fetch test paper');
    }
  }

  useEffect(() => {
    void loadCore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadQuestionBank();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadQuestionPaper(selectedAssessmentId);
  }, [selectedAssessmentId]);

  useEffect(() => {
    if (saveSubjectOptions.length === 0) {
      setSaveSubjectId('');
      return;
    }
    if (saveSubjectId && saveSubjectOptions.some((item) => item.id === saveSubjectId)) {
      return;
    }
    setSaveSubjectId(saveSubjectOptions[0].id);
  }, [saveSubjectOptions, saveSubjectId]);

  useEffect(() => {
    if (createSubjectOptions.length === 0) {
      setCreateSubjectId('');
      return;
    }
    if (createSubjectId && createSubjectOptions.some((item) => item.id === createSubjectId)) {
      return;
    }
    setCreateSubjectId(createSubjectOptions[0].id);
  }, [createSubjectOptions, createSubjectId]);

  async function handleSaveQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingQuestion(true);
    setError(null);
    setSuccess(null);

    try {
      const classLevel = Number(saveClassLevel);
      const payload = {
        class_level: classLevel,
        stream: streamRequired(classLevel) ? saveStream || null : null,
        subject_id: saveSubjectId,
        topic: saveTopic.trim(),
        prompt: savePrompt.trim(),
        difficulty: saveDifficulty,
        default_marks: Number(saveDefaultMarks),
        correct_option_key: saveCorrectKey,
        is_active: true,
        options: [
          { key: 'A', text: saveOptionA.trim() },
          { key: 'B', text: saveOptionB.trim() },
          { key: 'C', text: saveOptionC.trim() },
          { key: 'D', text: saveOptionD.trim() },
        ],
      };

      await apiRequest('/api/v1/admin/assessments/question-bank', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setSaveTopic('');
      setSavePrompt('');
      setSaveOptionA('');
      setSaveOptionB('');
      setSaveOptionC('');
      setSaveOptionD('');
      setSaveDefaultMarks('1');
      setSaveCorrectKey('A');
      setSuccess('Question saved successfully.');
      await loadQuestionBank();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save question');
    } finally {
      setSavingQuestion(false);
    }
  }

  async function handleToggleQuestionActive(item: QuestionBankItem) {
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/api/v1/admin/assessments/question-bank/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !item.is_active }),
      });
      setSuccess(`Question ${!item.is_active ? 'activated' : 'deactivated'} successfully.`);
      await loadQuestionBank();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update question');
    }
  }

  async function handleDeleteQuestion(item: QuestionBankItem) {
    const confirmed = window.confirm('Delete this question permanently? This cannot be undone.');
    if (!confirmed) {
      return;
    }

    setDeletingQuestionId(item.id);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/api/v1/admin/assessments/question-bank/${item.id}`, {
        method: 'DELETE',
      });
      setQuestionSelection((current) => {
        if (!current[item.id]) {
          return current;
        }
        const next = { ...current };
        delete next[item.id];
        return next;
      });
      setSuccess('Question deleted successfully.');
      await loadQuestionBank();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete question');
    } finally {
      setDeletingQuestionId(null);
    }
  }

  function toggleQuestionSelection(item: QuestionBankItem) {
    setQuestionSelection((current) => {
      if (current[item.id]) {
        const next = { ...current };
        delete next[item.id];
        return next;
      }
      return {
        ...current,
        [item.id]: {
          question_id: item.id,
          marks: item.default_marks || 1,
          negative_marks: 0,
        },
      };
    });
  }

  function updateQuestionMarks(questionId: string, marks: number) {
    setQuestionSelection((current) => {
      const existing = current[questionId];
      if (!existing) return current;
      return {
        ...current,
        [questionId]: {
          ...existing,
          marks,
        },
      };
    });
  }

  function updateQuestionNegativeMarks(questionId: string, negativeMarks: number) {
    setQuestionSelection((current) => {
      const existing = current[questionId];
      if (!existing) return current;
      return {
        ...current,
        [questionId]: {
          ...existing,
          negative_marks: negativeMarks,
        },
      };
    });
  }

  async function handleCreateTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingTest(true);
    setError(null);
    setSuccess(null);

    try {
      const classLevel = Number(createClassLevel);
      const payload = {
        title: createTitle.trim(),
        description: createDescription.trim() || null,
        class_level: classLevel,
        stream: streamRequired(classLevel) ? createStream || null : null,
        subject_id: createSubjectId,
        topic: createTopic.trim() || null,
        assessment_type: createType,
        duration_minutes: Number(createDurationMinutes),
        attempt_limit: Number(createAttemptLimit),
        passing_marks: Number(createPassingMarks),
        questions: selectedQuestions,
      };

      const response = await apiRequest<{ id: string }>('/api/v1/admin/assessments/create-test', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setCreateTitle('');
      setCreateDescription('');
      setCreateTopic('');
      setCreateDurationMinutes('30');
      setCreateAttemptLimit('1');
      setCreatePassingMarks('0');
      setQuestionSelection({});
      setSelectedAssessmentId(response.id);
      setSection('assign');
      setSuccess('Test paper created. Next, schedule and assign it.');

      await loadCore();
      await loadQuestionPaper(response.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create test');
    } finally {
      setCreatingTest(false);
    }
  }

  async function handleAssignTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAssessmentId) {
      setError('Select a test first.');
      return;
    }

    setAssigningTest(true);
    setError(null);
    setSuccess(null);

    try {
      const audience = selectedAudience;
      const targets =
        audience === 'all'
          ? [{ target_type: 'all_students', target_id: 'all' }]
          : [{ target_type: 'grade', target_id: audience }];

      await apiRequest(`/api/v1/admin/assessments/${selectedAssessmentId}/assign`, {
        method: 'POST',
        body: JSON.stringify({
          starts_at: new Date(assignStartsAt).toISOString(),
          ends_at: new Date(assignEndsAt).toISOString(),
          targets,
          publish: publishNow,
          send_notification: sendNotification,
        }),
      });

      setSuccess('Test assigned successfully. Students will receive it as per schedule.');
      await loadCore();
      await loadQuestionPaper(selectedAssessmentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign test');
    } finally {
      setAssigningTest(false);
    }
  }

  async function applyQuestionFilters() {
    await loadQuestionBank();
  }

  const createQuestionPool = useMemo(() => {
    const classLevel = Number(createClassLevel);
    const stream = streamRequired(classLevel) ? createStream : '';

    return questionBank.filter((item) => {
      if (!item.is_active) return false;
      if (item.class_level !== classLevel) return false;
      if (streamRequired(classLevel) && item.stream !== stream) return false;
      if (createSubjectId && item.subject.id !== createSubjectId) return false;
      return true;
    });
  }, [createClassLevel, createStream, createSubjectId, questionBank]);

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Assessment Engine</h1>
          <p className={styles.subtitle}>
            Build high-quality tests in three steps: save questions, create paper, assign with schedule.
          </p>
        </div>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {success ? <p className={styles.success}>{success}</p> : null}

      <div className={styles.sectionTabs}>
        {(['save', 'create', 'assign'] as SectionKey[]).map((item) => (
          <button
            key={item}
            type="button"
            className={cls(styles.tabButton, section === item && styles.tabActive)}
            onClick={() => {
              setSection(item);
              setError(null);
              setSuccess(null);
            }}
          >
            {SECTION_LABELS[item]}
          </button>
        ))}
      </div>

      {loading ? <div className={styles.loading}>Loading assessment module...</div> : null}

      {!loading ? (
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Dynamic Subject Setup</h3>
          <p className={styles.cardSubtle}>
            Add any new subject for a specific class and stream. It becomes instantly available in Save Test and Create Test.
          </p>

          <form onSubmit={handleCreateSubject}>
            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Class</span>
                <select
                  className={styles.select}
                  value={newSubjectClassLevel}
                  onChange={(event) => {
                    setNewSubjectClassLevel(event.target.value);
                    if (event.target.value === '10') {
                      setNewSubjectStream('');
                    }
                  }}
                  required
                >
                  <option value="10">10</option>
                  <option value="11">11</option>
                  <option value="12">12</option>
                </select>
              </label>

              {streamRequired(Number(newSubjectClassLevel)) ? (
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Stream</span>
                  <select
                    className={styles.select}
                    value={newSubjectStream}
                    onChange={(event) => setNewSubjectStream(event.target.value as 'science' | 'commerce')}
                    required
                  >
                    <option value="">Select stream</option>
                    <option value="science">Science</option>
                    <option value="commerce">Commerce</option>
                  </select>
                </label>
              ) : null}

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Subject Name</span>
                <input
                  className={styles.input}
                  value={newSubjectName}
                  onChange={(event) => setNewSubjectName(event.target.value)}
                  placeholder="e.g. Physics"
                  required
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Subject Code (optional)</span>
                <input
                  className={styles.input}
                  value={newSubjectCode}
                  onChange={(event) => setNewSubjectCode(event.target.value)}
                  placeholder="e.g. PHYSICS"
                />
              </label>
            </div>

            <div className={styles.buttonRow}>
              <button className={styles.btnPrimary} type="submit" disabled={creatingSubject}>
                {creatingSubject ? 'Creating...' : 'Create Subject'}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {!loading && section === 'save' ? (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Save Test Question</h3>
            <p className={styles.cardSubtle}>
              Author MCQ questions by class, stream, subject and topic for reusable question bank.
            </p>

            <form onSubmit={handleSaveQuestion}>
              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Class</span>
                  <select
                    className={styles.select}
                    value={saveClassLevel}
                    onChange={(event) => {
                      setSaveClassLevel(event.target.value);
                      if (event.target.value === '10') setSaveStream('');
                    }}
                    required
                  >
                    <option value="10">10</option>
                    <option value="11">11</option>
                    <option value="12">12</option>
                  </select>
                </label>

                {streamRequired(Number(saveClassLevel)) ? (
                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>Stream</span>
                    <select
                      className={styles.select}
                      value={saveStream}
                      onChange={(event) => setSaveStream(event.target.value as 'science' | 'commerce')}
                      required
                    >
                      <option value="">Select stream</option>
                      <option value="science">Science</option>
                      <option value="commerce">Commerce</option>
                    </select>
                  </label>
                ) : null}

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Search Subject</span>
                  <input
                    className={styles.input}
                    value={saveSubjectSearch}
                    onChange={(event) => setSaveSubjectSearch(event.target.value)}
                    placeholder="Search by code or name"
                  />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Subject</span>
                  <select
                    className={styles.select}
                    value={saveSubjectId}
                    onChange={(event) => setSaveSubjectId(event.target.value)}
                    required
                  >
                    <option value="">Select subject</option>
                    {saveSubjectOptions.map((subject) => (
                      <option key={subject.id} value={subject.id}>
                        {subject.code} - {subject.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Topic</span>
                  <input
                    className={styles.input}
                    value={saveTopic}
                    onChange={(event) => setSaveTopic(event.target.value)}
                    placeholder="Algebra Basics"
                    required
                  />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Difficulty</span>
                  <select
                    className={styles.select}
                    value={saveDifficulty}
                    onChange={(event) => setSaveDifficulty(event.target.value as 'easy' | 'medium' | 'hard')}
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Default Marks</span>
                  <input
                    className={styles.input}
                    type="number"
                    min={1}
                    max={100}
                    step="0.5"
                    value={saveDefaultMarks}
                    onChange={(event) => setSaveDefaultMarks(event.target.value)}
                    required
                  />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Correct Option</span>
                  <select
                    className={styles.select}
                    value={saveCorrectKey}
                    onChange={(event) => setSaveCorrectKey(event.target.value as 'A' | 'B' | 'C' | 'D')}
                  >
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                  </select>
                </label>
              </div>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Question Prompt</span>
                <textarea
                  className={styles.textarea}
                  rows={3}
                  value={savePrompt}
                  onChange={(event) => setSavePrompt(event.target.value)}
                  placeholder="Write the exact test question prompt"
                  required
                />
              </label>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Option A</span>
                  <input className={styles.input} value={saveOptionA} onChange={(e) => setSaveOptionA(e.target.value)} required />
                </label>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Option B</span>
                  <input className={styles.input} value={saveOptionB} onChange={(e) => setSaveOptionB(e.target.value)} required />
                </label>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Option C</span>
                  <input className={styles.input} value={saveOptionC} onChange={(e) => setSaveOptionC(e.target.value)} required />
                </label>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Option D</span>
                  <input className={styles.input} value={saveOptionD} onChange={(e) => setSaveOptionD(e.target.value)} required />
                </label>
              </div>

              <div className={styles.buttonRow}>
                <button className={styles.btnPrimary} type="submit" disabled={savingQuestion}>
                  {savingQuestion ? 'Saving...' : 'Save Question'}
                </button>
              </div>
            </form>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Saved Questions</h3>
            <p className={styles.cardSubtle}>Use filters for class, stream, subject and topic to maintain clean question bank.</p>

            <div className={styles.filtersGrid}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Class</span>
                <select className={styles.select} value={filterClassLevel} onChange={(e) => setFilterClassLevel(e.target.value)}>
                  <option value="">All</option>
                  <option value="10">10</option>
                  <option value="11">11</option>
                  <option value="12">12</option>
                </select>
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Stream</span>
                <select className={styles.select} value={filterStream} onChange={(e) => setFilterStream(e.target.value)}>
                  <option value="">All</option>
                  <option value="science">Science</option>
                  <option value="commerce">Commerce</option>
                </select>
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Subject</span>
                <select className={styles.select} value={filterSubjectId} onChange={(e) => setFilterSubjectId(e.target.value)}>
                  <option value="">All</option>
                  {subjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>
                      {subject.code} - {subject.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Topic</span>
                <input className={styles.input} value={filterTopic} onChange={(e) => setFilterTopic(e.target.value)} placeholder="Search topic" />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Search Prompt</span>
                <input className={styles.input} value={filterSearch} onChange={(e) => setFilterSearch(e.target.value)} placeholder="Search question text" />
              </label>
            </div>

            <div className={styles.buttonRow}>
              <button type="button" className={styles.btnSecondary} onClick={applyQuestionFilters} disabled={loadingQuestions}>
                {loadingQuestions ? 'Filtering...' : 'Apply Filters'}
              </button>
            </div>

            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>Subject</th>
                    <th>Topic</th>
                    <th>Prompt</th>
                    <th>Correct</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {questionBank.map((item) => (
                    <tr key={item.id}>
                      <td>{item.class_level}{item.stream ? ` ${item.stream}` : ''}</td>
                      <td>{item.subject.code}</td>
                      <td>{item.topic || '-'}</td>
                      <td className={styles.promptCell}>{item.prompt}</td>
                      <td>{item.correct_option_key}</td>
                      <td>
                        <span className={cls(styles.badge, item.is_active ? styles.badgeSuccess : styles.badgeMuted)}>
                          {item.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <div className={styles.inlineActionRow}>
                          <button
                            type="button"
                            className={styles.btnInline}
                            onClick={() => handleToggleQuestionActive(item)}
                          >
                            {item.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button
                            type="button"
                            className={styles.btnDangerInline}
                            onClick={() => handleDeleteQuestion(item)}
                            disabled={deletingQuestionId === item.id}
                          >
                            {deletingQuestionId === item.id ? 'Deleting...' : 'Delete'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {questionBank.length === 0 ? (
                    <tr>
                      <td colSpan={7} className={styles.emptyRow}>No questions found for selected filters.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}

      {!loading && section === 'create' ? (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Create Test Paper</h3>
            <p className={styles.cardSubtle}>Select class + subject, choose saved questions, set marks and timings.</p>

            <form onSubmit={handleCreateTest}>
              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Test Title</span>
                  <input className={styles.input} value={createTitle} onChange={(e) => setCreateTitle(e.target.value)} required />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Class</span>
                  <select
                    className={styles.select}
                    value={createClassLevel}
                    onChange={(event) => {
                      setCreateClassLevel(event.target.value);
                      if (event.target.value === '10') setCreateStream('');
                    }}
                    required
                  >
                    <option value="10">10</option>
                    <option value="11">11</option>
                    <option value="12">12</option>
                  </select>
                </label>

                {streamRequired(Number(createClassLevel)) ? (
                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>Stream</span>
                    <select
                      className={styles.select}
                      value={createStream}
                      onChange={(event) => setCreateStream(event.target.value as 'science' | 'commerce')}
                      required
                    >
                      <option value="">Select stream</option>
                      <option value="science">Science</option>
                      <option value="commerce">Commerce</option>
                    </select>
                  </label>
                ) : null}

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Search Subject</span>
                  <input
                    className={styles.input}
                    value={createSubjectSearch}
                    onChange={(event) => setCreateSubjectSearch(event.target.value)}
                    placeholder="Search by code or name"
                  />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Subject</span>
                  <select className={styles.select} value={createSubjectId} onChange={(e) => setCreateSubjectId(e.target.value)} required>
                    <option value="">Select subject</option>
                    {createSubjectOptions.map((subject) => (
                      <option key={subject.id} value={subject.id}>{subject.code} - {subject.name}</option>
                    ))}
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Topic</span>
                  <input className={styles.input} value={createTopic} onChange={(e) => setCreateTopic(e.target.value)} placeholder="Optional topic" />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Type</span>
                  <select className={styles.select} value={createType} onChange={(e) => setCreateType(e.target.value as 'daily_practice' | 'subject_practice' | 'scheduled')}>
                    <option value="daily_practice">Daily Practice</option>
                    <option value="subject_practice">Subject Practice</option>
                    <option value="scheduled">Scheduled</option>
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Duration (minutes)</span>
                  <input className={styles.input} type="number" min={5} max={240} value={createDurationMinutes} onChange={(e) => setCreateDurationMinutes(e.target.value)} required />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Attempt Limit</span>
                  <input className={styles.input} type="number" min={1} max={5} value={createAttemptLimit} onChange={(e) => setCreateAttemptLimit(e.target.value)} required />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Passing Marks</span>
                  <input className={styles.input} type="number" min={0} step="0.5" value={createPassingMarks} onChange={(e) => setCreatePassingMarks(e.target.value)} required />
                </label>
              </div>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Description</span>
                <textarea className={styles.textarea} rows={2} value={createDescription} onChange={(e) => setCreateDescription(e.target.value)} />
              </label>

              <div className={styles.selectionSummary}>
                <span>Selected Questions: <strong>{selectedQuestionCount}</strong></span>
                <span>Total Marks: <strong>{selectedTotalMarks.toFixed(1)}</strong></span>
              </div>

              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Select</th>
                      <th>Topic</th>
                      <th>Prompt</th>
                      <th>Marks</th>
                      <th>Negative</th>
                    </tr>
                  </thead>
                  <tbody>
                    {createQuestionPool.map((item) => {
                      const checked = Boolean(questionSelection[item.id]);
                      return (
                        <tr key={item.id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleQuestionSelection(item)}
                            />
                          </td>
                          <td>{item.topic || '-'}</td>
                          <td className={styles.promptCell}>{item.prompt}</td>
                          <td>
                            <input
                              className={styles.inlineInput}
                              type="number"
                              min={0.5}
                              step="0.5"
                              value={questionSelection[item.id]?.marks ?? item.default_marks}
                              disabled={!checked}
                              onChange={(event) => updateQuestionMarks(item.id, Number(event.target.value))}
                            />
                          </td>
                          <td>
                            <input
                              className={styles.inlineInput}
                              type="number"
                              min={0}
                              step="0.5"
                              value={questionSelection[item.id]?.negative_marks ?? 0}
                              disabled={!checked}
                              onChange={(event) => updateQuestionNegativeMarks(item.id, Number(event.target.value))}
                            />
                          </td>
                        </tr>
                      );
                    })}
                    {createQuestionPool.length === 0 ? (
                      <tr>
                        <td colSpan={5} className={styles.emptyRow}>No active questions available for selected class/subject.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className={styles.buttonRow}>
                <button
                  type="submit"
                  className={styles.btnPrimary}
                  disabled={creatingTest || selectedQuestionCount === 0}
                >
                  {creatingTest ? 'Creating...' : 'Create Test'}
                </button>
              </div>
            </form>
          </div>
        </>
      ) : null}

      {!loading && section === 'assign' ? (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Assign Test Schedule</h3>
            <p className={styles.cardSubtle}>Choose test, audience, and schedule window. Students get test notifications automatically.</p>

            <form onSubmit={handleAssignTest}>
              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Test</span>
                  <select
                    className={styles.select}
                    value={selectedAssessmentId}
                    onChange={(event) => setSelectedAssessmentId(event.target.value)}
                    required
                  >
                    <option value="">Select test</option>
                    {assessments.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title} ({item.status})
                      </option>
                    ))}
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Audience</span>
                  <select
                    className={styles.select}
                    value={selectedAudience}
                    onChange={(event) => setSelectedAudience(event.target.value as (typeof AUDIENCE_OPTIONS)[number]['value'])}
                  >
                    {AUDIENCE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Starts At</span>
                  <input
                    className={styles.input}
                    type="datetime-local"
                    value={assignStartsAt}
                    onChange={(event) => setAssignStartsAt(event.target.value)}
                    required
                  />
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Ends At</span>
                  <input
                    className={styles.input}
                    type="datetime-local"
                    value={assignEndsAt}
                    onChange={(event) => setAssignEndsAt(event.target.value)}
                    required
                  />
                </label>
              </div>

              <div className={styles.checkboxRow}>
                <label>
                  <input type="checkbox" checked={publishNow} onChange={(event) => setPublishNow(event.target.checked)} />
                  Publish immediately
                </label>
                <label>
                  <input type="checkbox" checked={sendNotification} onChange={(event) => setSendNotification(event.target.checked)} />
                  Send notifications to students
                </label>
              </div>

              <div className={styles.buttonRow}>
                <button className={styles.btnPrimary} type="submit" disabled={assigningTest || !selectedAssessmentId}>
                  {assigningTest ? 'Assigning...' : 'Assign Test'}
                </button>
              </div>
            </form>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Selected Test Paper</h3>
            {paper ? (
              <>
                <div className={styles.paperMeta}>
                  <span><strong>Title:</strong> {paper.assessment.title}</span>
                  <span><strong>Class:</strong> {paper.assessment.class_level ?? '-'} {paper.assessment.stream ?? ''}</span>
                  <span><strong>Subject:</strong> {subjectName(subjects, paper.assessment.subject_id)}</span>
                  <span><strong>Topic:</strong> {paper.assessment.topic || '-'}</span>
                  <span><strong>Total:</strong> {paper.assessment.total_marks}</span>
                  <span><strong>Passing:</strong> {paper.assessment.passing_marks}</span>
                </div>

                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Prompt</th>
                        <th>Marks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paper.items.map((item) => (
                        <tr key={item.question_id}>
                          <td>{item.seq_no}</td>
                          <td className={styles.promptCell}>{item.prompt}</td>
                          <td>{item.marks}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className={styles.emptyRow}>Choose a test to view question paper.</p>
            )}
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Assessment Registry</h3>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Window</th>
                  </tr>
                </thead>
                <tbody>
                  {assessments.map((item) => (
                    <tr key={item.id}>
                      <td>{item.title}</td>
                      <td>{item.assessment_type}</td>
                      <td>
                        <span className={cls(styles.badge, item.status === 'published' ? styles.badgeSuccess : styles.badgeMuted)}>
                          {item.status}
                        </span>
                      </td>
                      <td>{Math.round(item.duration_sec / 60)} min</td>
                      <td>{toDisplayDate(item.starts_at)} - {toDisplayDate(item.ends_at)}</td>
                    </tr>
                  ))}
                  {assessments.length === 0 ? (
                    <tr>
                      <td colSpan={5} className={styles.emptyRow}>No test papers created yet.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
