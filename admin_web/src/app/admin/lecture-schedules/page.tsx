'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './lecture-schedules.module.css';

type ScheduleStatus = 'scheduled' | 'done' | 'canceled';
type StreamValue = 'science' | 'commerce' | '';
type TrackerMode = 'all' | 'date' | 'week' | 'month';

type Subject = {
  id: string;
  code: string;
  name: string;
  scopes?: Array<{
    class_level: number;
    stream: 'science' | 'commerce' | null;
  }>;
};

type Teacher = {
  teacher_id: string;
  full_name: string;
  phone: string | null;
  assignment_count: number;
};

type Student = {
  student_id: string;
  full_name: string;
  phone: string | null;
  class_name: string | null;
  stream: string | null;
  status: string;
};

type LectureScheduleItem = {
  id: string;
  class_level: number;
  stream: string;
  subject_id: string;
  subject_name: string;
  teacher_id: string;
  teacher_name: string;
  topic: string;
  lecture_notes: string | null;
  scheduled_at: string;
  status: ScheduleStatus;
  all_students_in_scope: boolean;
  selected_students_count: number;
  completed_at: string | null;
  created_at: string;
};

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

function toInputDateTime(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hour = String(value.getHours()).padStart(2, '0');
  const minute = String(value.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function toDateInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function calculateTrackerRange(mode: TrackerMode, anchorDate: string): { from: string; to: string } | null {
  if (mode === 'all' || !anchorDate) {
    return null;
  }

  const anchor = new Date(`${anchorDate}T00:00:00`);
  if (Number.isNaN(anchor.getTime())) {
    return null;
  }

  if (mode === 'date') {
    const single = toDateInputValue(anchor);
    return { from: single, to: single };
  }

  if (mode === 'week') {
    const weekday = anchor.getDay();
    const mondayDelta = (weekday + 6) % 7;
    const start = new Date(anchor);
    start.setDate(anchor.getDate() - mondayDelta);

    const end = new Date(start);
    end.setDate(start.getDate() + 6);

    return { from: toDateInputValue(start), to: toDateInputValue(end) };
  }

  const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const monthEnd = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);
  return { from: toDateInputValue(monthStart), to: toDateInputValue(monthEnd) };
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

function classLabel(classLevel: number, stream: string): string {
  if (classLevel === 10) {
    return '10th';
  }
  return `${classLevel}th ${stream === 'science' ? 'Science' : 'Commerce'}`;
}

function statusBadgeClass(status: ScheduleStatus): string {
  if (status === 'done') return `${styles.badge} ${styles.badgeDone}`;
  if (status === 'canceled') return `${styles.badge} ${styles.badgeCanceled}`;
  return `${styles.badge} ${styles.badgeScheduled}`;
}

export default function AdminLectureSchedulesPage() {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [filterTeachers, setFilterTeachers] = useState<Teacher[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [schedules, setSchedules] = useState<LectureScheduleItem[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [creating, setCreating] = useState(false);
  const [statusUpdatingId, setStatusUpdatingId] = useState<string | null>(null);

  const [formClassLevel, setFormClassLevel] = useState('10');
  const [formStream, setFormStream] = useState<StreamValue>('');
  const [formSubjectId, setFormSubjectId] = useState('');
  const [formTeacherId, setFormTeacherId] = useState('');
  const [formTopic, setFormTopic] = useState('');
  const [formLectureNotes, setFormLectureNotes] = useState('');
  const [formScheduledAt, setFormScheduledAt] = useState(() => {
    const value = new Date();
    value.setMinutes(value.getMinutes() + 30);
    return toInputDateTime(value);
  });
  const [audienceMode, setAudienceMode] = useState<'all' | 'selected'>('all');
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([]);
  const [studentSearch, setStudentSearch] = useState('');

  const [filterClassLevel, setFilterClassLevel] = useState('');
  const [filterStream, setFilterStream] = useState<StreamValue>('');
  const [filterSubjectId, setFilterSubjectId] = useState('');
  const [filterTeacherId, setFilterTeacherId] = useState('');
  const [filterStatus, setFilterStatus] = useState<ScheduleStatus | ''>('');
  const [filterSearch, setFilterSearch] = useState('');
  const [trackerMode, setTrackerMode] = useState<TrackerMode>('all');
  const [trackerDate, setTrackerDate] = useState(() => toDateInputValue(new Date()));

  const classLevelValue = Number(formClassLevel);

  const scopedSubjects = useMemo(() => {
    return subjects.filter((item) => subjectMatchesScope(item, classLevelValue, formStream));
  }, [subjects, classLevelValue, formStream]);

  const scopedFilterSubjects = useMemo(() => {
    if (!filterClassLevel) {
      return subjects;
    }
    const classLevel = Number(filterClassLevel);
    return subjects.filter((item) => subjectMatchesScope(item, classLevel, filterStream));
  }, [subjects, filterClassLevel, filterStream]);

  const filteredStudents = useMemo(() => {
    const q = studentSearch.trim().toLowerCase();
    if (!q) {
      return students;
    }
    return students.filter((item) => {
      const name = item.full_name.toLowerCase();
      const phone = (item.phone ?? '').toLowerCase();
      return name.includes(q) || phone.includes(q);
    });
  }, [studentSearch, students]);

  const trackerRange = useMemo(() => calculateTrackerRange(trackerMode, trackerDate), [trackerMode, trackerDate]);

  const trackerRangeLabel = useMemo(() => {
    if (!trackerRange) {
      return 'All scheduled lectures';
    }
    return `${trackerRange.from} to ${trackerRange.to}`;
  }, [trackerRange]);

  const summary = useMemo(() => {
    let scheduled = 0;
    let done = 0;
    let canceled = 0;
    let dueToday = 0;

    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);

    for (const item of schedules) {
      if (item.status === 'scheduled') {
        scheduled += 1;
      } else if (item.status === 'done') {
        done += 1;
      } else if (item.status === 'canceled') {
        canceled += 1;
      }

      if (item.status === 'scheduled') {
        const at = new Date(item.scheduled_at);
        if (at >= start && at < end) {
          dueToday += 1;
        }
      }
    }

    return {
      total: schedules.length,
      scheduled,
      done,
      canceled,
      dueToday,
    };
  }, [schedules]);

  async function loadSubjects() {
    const response = await apiRequest<{ items: Subject[] }>('/api/v1/admin/subjects?limit=300&offset=0');
    setSubjects(response.items);
    return response.items;
  }

  async function loadFilterTeachers() {
    const response = await apiRequest<{ items: Teacher[] }>('/api/v1/admin/teachers?status=active&limit=100&offset=0');
    setFilterTeachers(response.items ?? []);
  }

  async function loadCandidateUsers(options?: { preserveTeacher?: boolean }) {
    const classLevel = Number(formClassLevel);
    const stream = streamRequired(classLevel) ? formStream : '';

    if (streamRequired(classLevel) && !stream) {
      setTeachers([]);
      setStudents([]);
      setSelectedStudentIds([]);
      return;
    }

    setLoadingCandidates(true);
    try {
      const teacherParams = new URLSearchParams({
        class_level: String(classLevel),
        limit: '100',
        offset: '0',
        status: 'active',
      });
      if (stream) {
        teacherParams.set('stream', stream);
      }
      if (formSubjectId) {
        teacherParams.set('subject_id', formSubjectId);
      }

      const studentParams = new URLSearchParams({
        class_level: String(classLevel),
        status: 'active',
        limit: '100',
        offset: '0',
      });
      if (stream) {
        studentParams.set('stream', stream);
      }

      const [teachersRes, studentsRes] = await Promise.all([
        apiRequest<{ items: Teacher[] }>(`/api/v1/admin/teachers?${teacherParams.toString()}`),
        apiRequest<{ items: Student[] }>(`/api/v1/admin/students?${studentParams.toString()}`),
      ]);

      setTeachers(teachersRes.items);
      setStudents(studentsRes.items);

      if (!options?.preserveTeacher) {
        if (teachersRes.items.length > 0) {
          const first = teachersRes.items[0].teacher_id;
          setFormTeacherId((prev) => (teachersRes.items.some((item) => item.teacher_id === prev) ? prev : first));
        } else {
          setFormTeacherId('');
        }
      } else if (!teachersRes.items.some((item) => item.teacher_id === formTeacherId)) {
        setFormTeacherId(teachersRes.items[0]?.teacher_id ?? '');
      }

      setSelectedStudentIds((current) =>
        current.filter((studentId) => studentsRes.items.some((item) => item.student_id === studentId)),
      );
    } finally {
      setLoadingCandidates(false);
    }
  }

  async function loadSchedules() {
    setLoadingSchedules(true);
    const params = new URLSearchParams({ limit: '100', offset: '0' });

    if (filterClassLevel) {
      params.set('class_level', filterClassLevel);
    }
    if (filterStream) {
      params.set('stream', filterStream);
    }
    if (filterSubjectId) {
      params.set('subject_id', filterSubjectId);
    }
    if (filterTeacherId) {
      params.set('teacher_id', filterTeacherId);
    }
    if (filterStatus) {
      params.set('status', filterStatus);
    }
    if (filterSearch.trim()) {
      params.set('search', filterSearch.trim());
    }
    if (trackerRange) {
      params.set('scheduled_from', trackerRange.from);
      params.set('scheduled_to', trackerRange.to);
    }

    try {
      const response = await apiRequest<{ items: LectureScheduleItem[] }>(
        `/api/v1/admin/lecture-schedules?${params.toString()}`,
      );
      setSchedules(response.items);
    } finally {
      setLoadingSchedules(false);
    }
  }

  async function bootstrap() {
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const loadedSubjects = await loadSubjects();
      if (loadedSubjects.length > 0) {
        const matching = loadedSubjects.find((item) => subjectMatchesScope(item, classLevelValue, formStream));
        if (matching) {
          setFormSubjectId(matching.id);
        }
      }
      await loadFilterTeachers();
      await loadSchedules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lecture schedule module');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (streamRequired(classLevelValue) && !formStream) {
      setTeachers([]);
      setStudents([]);
      setFormTeacherId('');
      setSelectedStudentIds([]);
      return;
    }

    void loadCandidateUsers({ preserveTeacher: true }).catch((err) => {
      setError(err instanceof Error ? err.message : 'Failed to load teacher/student candidates');
      setLoadingCandidates(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formClassLevel, formStream, formSubjectId]);

  useEffect(() => {
    if (!scopedSubjects.some((item) => item.id === formSubjectId)) {
      setFormSubjectId(scopedSubjects[0]?.id ?? '');
    }
  }, [formSubjectId, scopedSubjects]);

  useEffect(() => {
    if (streamRequired(classLevelValue)) {
      return;
    }
    if (formStream !== '') {
      setFormStream('');
    }
  }, [classLevelValue, formStream]);

  async function onCreateSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const classLevel = Number(formClassLevel);
    const stream = streamRequired(classLevel) ? formStream : '';

    if (streamRequired(classLevel) && !stream) {
      setError('Please select stream for class 11/12');
      return;
    }
    if (!formSubjectId) {
      setError('Please select a subject');
      return;
    }
    if (!formTeacherId) {
      setError('Please select a teacher');
      return;
    }
    if (!formTopic.trim()) {
      setError('Lecture topic is required');
      return;
    }
    if (!formScheduledAt) {
      setError('Please set lecture date and time');
      return;
    }
    if (audienceMode === 'selected' && selectedStudentIds.length === 0) {
      setError('Select at least one student for selected audience mode');
      return;
    }

    setCreating(true);
    try {
      await apiRequest('/api/v1/admin/lecture-schedules', {
        method: 'POST',
        body: JSON.stringify({
          class_level: classLevel,
          stream: streamRequired(classLevel) ? stream : null,
          subject_id: formSubjectId,
          teacher_id: formTeacherId,
          topic: formTopic.trim(),
          lecture_notes: formLectureNotes.trim() || null,
          scheduled_at: new Date(formScheduledAt).toISOString(),
          all_students_in_scope: audienceMode === 'all',
          student_ids: audienceMode === 'selected' ? selectedStudentIds : [],
        }),
      });

      setSuccess('Lecture scheduled successfully. Students and teachers will now see this in their upcoming lectures.');
      setFormTopic('');
      setFormLectureNotes('');
      setAudienceMode('all');
      setSelectedStudentIds([]);
      await loadSchedules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create lecture schedule');
    } finally {
      setCreating(false);
    }
  }

  async function updateScheduleStatus(scheduleId: string, status: ScheduleStatus) {
    setError(null);
    setSuccess(null);
    setStatusUpdatingId(scheduleId);
    try {
      await apiRequest(`/api/v1/admin/lecture-schedules/${scheduleId}/status`, {
        method: 'POST',
        body: JSON.stringify({ status }),
      });

      if (status === 'done') {
        setSuccess('Lecture marked done. It is now visible in student done-lectures flow for doubt raise.');
      } else if (status === 'canceled') {
        setSuccess('Lecture marked canceled.');
      } else {
        setSuccess('Lecture status updated.');
      }

      await loadSchedules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update lecture status');
    } finally {
      setStatusUpdatingId(null);
    }
  }

  function toggleStudentSelection(studentId: string) {
    setSelectedStudentIds((current) => {
      if (current.includes(studentId)) {
        return current.filter((id) => id !== studentId);
      }
      return [...current, studentId];
    });
  }

  if (loading) {
    return <div className="page">Loading lecture schedule module...</div>;
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Lecture Schedule</h1>
          <p className={styles.subtitle}>
            Plan class + stream + subject lectures, assign teachers, scope students, and mark lectures done.
          </p>
        </div>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {success ? <p className={styles.success}>{success}</p> : null}

      <div className={styles.summaryGrid}>
        <article className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Total Schedules</div>
          <div className={styles.summaryValue}>{summary.total}</div>
        </article>
        <article className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Scheduled</div>
          <div className={styles.summaryValue}>{summary.scheduled}</div>
        </article>
        <article className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Done</div>
          <div className={styles.summaryValue}>{summary.done}</div>
        </article>
        <article className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Canceled</div>
          <div className={styles.summaryValue}>{summary.canceled}</div>
        </article>
        <article className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Due Today</div>
          <div className={styles.summaryValue}>{summary.dueToday}</div>
        </article>
      </div>

      <div className={styles.workspace}>
        <article className={styles.card}>
          <h2 className={styles.cardTitle}>Create Lecture Schedule</h2>
          <form onSubmit={onCreateSchedule}>
            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Class</span>
                <select
                  className={styles.select}
                  value={formClassLevel}
                  onChange={(event) => setFormClassLevel(event.target.value)}
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
                  value={formStream}
                  onChange={(event) => setFormStream(event.target.value as StreamValue)}
                  disabled={!streamRequired(classLevelValue)}
                >
                  <option value="">{streamRequired(classLevelValue) ? 'Select stream' : 'Not required for class 10'}</option>
                  <option value="science">Science</option>
                  <option value="commerce">Commerce</option>
                </select>
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Subject</span>
                <select
                  className={styles.select}
                  value={formSubjectId}
                  onChange={(event) => setFormSubjectId(event.target.value)}
                >
                  <option value="">Select subject</option>
                  {scopedSubjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>
                      {subject.code} - {subject.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Teacher</span>
                <select
                  className={styles.select}
                  value={formTeacherId}
                  onChange={(event) => setFormTeacherId(event.target.value)}
                  disabled={loadingCandidates}
                >
                  <option value="">Select teacher</option>
                  {teachers.map((teacher) => (
                    <option key={teacher.teacher_id} value={teacher.teacher_id}>
                      {teacher.full_name} ({teacher.assignment_count} assignments)
                    </option>
                  ))}
                </select>
              </label>

              <label className={`${styles.field} ${styles.fieldFull}`}>
                <span className={styles.fieldLabel}>Lecture Topic</span>
                <input
                  className={styles.input}
                  value={formTopic}
                  onChange={(event) => setFormTopic(event.target.value)}
                  placeholder="Enter lecture topic"
                  maxLength={255}
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Lecture Timing</span>
                <input
                  className={styles.input}
                  type="datetime-local"
                  value={formScheduledAt}
                  onChange={(event) => setFormScheduledAt(event.target.value)}
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Audience</span>
                <div className={styles.inlineRow}>
                  <label className={styles.radioChip}>
                    <input
                      type="radio"
                      name="audience"
                      checked={audienceMode === 'all'}
                      onChange={() => setAudienceMode('all')}
                    />
                    All students in selected scope
                  </label>
                  <label className={styles.radioChip}>
                    <input
                      type="radio"
                      name="audience"
                      checked={audienceMode === 'selected'}
                      onChange={() => setAudienceMode('selected')}
                    />
                    Selected students only
                  </label>
                </div>
              </label>

              <label className={`${styles.field} ${styles.fieldFull}`}>
                <span className={styles.fieldLabel}>Lecture Notes (optional)</span>
                <textarea
                  className={styles.textarea}
                  value={formLectureNotes}
                  onChange={(event) => setFormLectureNotes(event.target.value)}
                  placeholder="Notes/instructions for students and teacher"
                  maxLength={5000}
                />
              </label>

              {audienceMode === 'selected' ? (
                <div className={`${styles.field} ${styles.fieldFull}`}>
                  <span className={styles.fieldLabel}>Select Students</span>
                  <div className={styles.studentsPanel}>
                    <input
                      className={styles.searchInput}
                      value={studentSearch}
                      onChange={(event) => setStudentSearch(event.target.value)}
                      placeholder="Search by student name or phone"
                    />
                    <div className={styles.studentList}>
                      {filteredStudents.length === 0 ? (
                        <div className={styles.muted}>No students found in selected scope.</div>
                      ) : (
                        filteredStudents.map((student) => (
                          <label key={student.student_id} className={styles.studentRow}>
                            <input
                              type="checkbox"
                              checked={selectedStudentIds.includes(student.student_id)}
                              onChange={() => toggleStudentSelection(student.student_id)}
                            />
                            <div>
                              <div>{student.full_name}</div>
                              <div className={styles.studentMeta}>
                                {student.phone || '-'} • {student.class_name || '-'} {student.stream || ''}
                              </div>
                            </div>
                          </label>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            <div className={styles.actionsRow}>
              <button className={styles.btn} type="submit" disabled={creating || loadingCandidates}>
                {creating ? 'Scheduling...' : 'Schedule Lecture'}
              </button>
              <button
                className={styles.btnSecondary}
                type="button"
                onClick={() => {
                  setFormTopic('');
                  setFormLectureNotes('');
                  setAudienceMode('all');
                  setSelectedStudentIds([]);
                }}
              >
                Reset Inputs
              </button>
            </div>
          </form>
        </article>

        <article className={styles.card}>
          <h2 className={styles.cardTitle}>Filter Lecture Schedules</h2>
          <div className={styles.formGrid}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Class</span>
              <select
                className={styles.select}
                value={filterClassLevel}
                onChange={(event) => setFilterClassLevel(event.target.value)}
              >
                <option value="">All classes</option>
                <option value="10">10th</option>
                <option value="11">11th</option>
                <option value="12">12th</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Stream</span>
              <select
                className={styles.select}
                value={filterStream}
                onChange={(event) => setFilterStream(event.target.value as StreamValue)}
                disabled={!filterClassLevel || Number(filterClassLevel) === 10}
              >
                <option value="">All streams</option>
                <option value="science">Science</option>
                <option value="commerce">Commerce</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Subject</span>
              <select
                className={styles.select}
                value={filterSubjectId}
                onChange={(event) => setFilterSubjectId(event.target.value)}
              >
                <option value="">All subjects</option>
                {scopedFilterSubjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.code} - {subject.name}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Teacher</span>
              <select
                className={styles.select}
                value={filterTeacherId}
                onChange={(event) => setFilterTeacherId(event.target.value)}
              >
                <option value="">All teachers</option>
                {filterTeachers.map((teacher) => (
                  <option key={teacher.teacher_id} value={teacher.teacher_id}>
                    {teacher.full_name}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Status</span>
              <select
                className={styles.select}
                value={filterStatus}
                onChange={(event) => setFilterStatus(event.target.value as ScheduleStatus | '')}
              >
                <option value="">All statuses</option>
                <option value="scheduled">Scheduled</option>
                <option value="done">Done</option>
                <option value="canceled">Canceled</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Tracker</span>
              <select
                className={styles.select}
                value={trackerMode}
                onChange={(event) => setTrackerMode(event.target.value as TrackerMode)}
              >
                <option value="all">All schedules</option>
                <option value="date">Date-wise</option>
                <option value="week">Week-wise</option>
                <option value="month">Month-wise</option>
              </select>
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Tracker Date</span>
              <input
                className={styles.input}
                type="date"
                value={trackerDate}
                onChange={(event) => setTrackerDate(event.target.value)}
                disabled={trackerMode === 'all'}
              />
            </label>

            <label className={`${styles.field} ${styles.fieldFull}`}>
              <span className={styles.fieldLabel}>Search</span>
              <input
                className={styles.input}
                value={filterSearch}
                onChange={(event) => setFilterSearch(event.target.value)}
                placeholder="Search by topic, subject, or teacher"
              />
            </label>
          </div>

          <div className={styles.actionsRow}>
            <button className={styles.btn} type="button" onClick={() => void loadSchedules()} disabled={loadingSchedules}>
              {loadingSchedules ? 'Applying...' : 'Apply Filters'}
            </button>
            <button
              className={styles.btnSecondary}
              type="button"
              onClick={() => {
                setFilterClassLevel('');
                setFilterStream('');
                setFilterSubjectId('');
                setFilterTeacherId('');
                setFilterStatus('');
                setFilterSearch('');
                setTrackerMode('all');
                setTrackerDate(toDateInputValue(new Date()));
                window.setTimeout(() => {
                  void loadSchedules();
                }, 0);
              }}
            >
              Reset Filters
            </button>
          </div>
          <div className={styles.muted}>Tracking Window: {trackerRangeLabel}</div>
        </article>
      </div>

      <article className={styles.card}>
        <h2 className={styles.cardTitle}>Scheduled Lectures</h2>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Topic</th>
                <th>Class Scope</th>
                <th>Subject</th>
                <th>Teacher</th>
                <th>Timing</th>
                <th>Audience</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.length === 0 ? (
                <tr>
                  <td colSpan={8} className={styles.muted}>
                    No lecture schedules found for selected filters.
                  </td>
                </tr>
              ) : (
                schedules.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className={styles.topicCell}>{item.topic}</div>
                      {item.lecture_notes ? <div className={styles.muted}>{item.lecture_notes}</div> : null}
                    </td>
                    <td>{classLabel(item.class_level, item.stream)}</td>
                    <td>{item.subject_name}</td>
                    <td>{item.teacher_name}</td>
                    <td>{toDisplayDate(item.scheduled_at)}</td>
                    <td>
                      {item.all_students_in_scope
                        ? 'All students in scope'
                        : `${item.selected_students_count} selected student${item.selected_students_count === 1 ? '' : 's'}`}
                    </td>
                    <td>
                      <span className={statusBadgeClass(item.status)}>{item.status}</span>
                      {item.status === 'done' && item.completed_at ? (
                        <div className={styles.muted}>Done: {toDisplayDate(item.completed_at)}</div>
                      ) : null}
                    </td>
                    <td>
                      <div className={styles.inlineRow}>
                        {item.status === 'scheduled' ? (
                          <>
                            <button
                              className={styles.btnSuccess}
                              type="button"
                              disabled={statusUpdatingId === item.id}
                              onClick={() => void updateScheduleStatus(item.id, 'done')}
                            >
                              Mark Done
                            </button>
                            <button
                              className={styles.btnWarning}
                              type="button"
                              disabled={statusUpdatingId === item.id}
                              onClick={() => void updateScheduleStatus(item.id, 'canceled')}
                            >
                              Cancel
                            </button>
                          </>
                        ) : item.status === 'canceled' ? (
                          <button
                            className={styles.btnGhost}
                            type="button"
                            disabled={statusUpdatingId === item.id}
                            onClick={() => void updateScheduleStatus(item.id, 'scheduled')}
                          >
                            Restore Scheduled
                          </button>
                        ) : (
                          <span className={styles.muted}>Completed</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
