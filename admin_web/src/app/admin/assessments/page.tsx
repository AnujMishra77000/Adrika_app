'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Assessment = {
  id: string;
  title: string;
  assessment_type: string;
  status: string;
  starts_at: string | null;
  duration_sec: number;
};

type Subject = { id: string; code: string; name: string };

export default function AdminAssessmentsPage() {
  const [items, setItems] = useState<Assessment[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [assessmentType, setAssessmentType] = useState('daily_practice');
  const [durationSec, setDurationSec] = useState('1800');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [attemptLimit, setAttemptLimit] = useState('1');
  const [totalMarks, setTotalMarks] = useState('20');
  const [targetsJson, setTargetsJson] = useState('[{"target_type":"all","target_id":"all"}]');

  async function load() {
    try {
      const [assessmentRes, subjectRes] = await Promise.all([
        apiRequest<{ items: Assessment[] }>('/api/v1/admin/assessments?limit=50&offset=0'),
        apiRequest<{ items: Subject[] }>('/api/v1/admin/subjects?limit=200&offset=0'),
      ]);
      setItems(assessmentRes.items);
      setSubjects(subjectRes.items);
      if (!subjectId && subjectRes.items.length > 0) {
        setSubjectId(subjectRes.items[0].id);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessments');
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const targets = JSON.parse(targetsJson);
      await apiRequest('/api/v1/admin/assessments', {
        method: 'POST',
        body: JSON.stringify({
          title,
          subject_id: subjectId,
          assessment_type: assessmentType,
          starts_at: startsAt ? new Date(startsAt).toISOString() : null,
          ends_at: endsAt ? new Date(endsAt).toISOString() : null,
          duration_sec: Number(durationSec),
          attempt_limit: Number(attemptLimit),
          total_marks: Number(totalMarks),
          targets,
        }),
      });
      setTitle('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create assessment');
    }
  }

  async function publishAssessment(assessmentId: string) {
    try {
      await apiRequest(`/api/v1/admin/assessments/${assessmentId}/publish`, { method: 'POST' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish assessment');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Assessments</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create Assessment</h3>
        <form onSubmit={createAssessment}>
          <div className="grid">
            <label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} required /></label>
            <label className="field">
              <span>Subject</span>
              <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} required>
                <option value="">Select</option>
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>{subject.code} - {subject.name}</option>
                ))}
              </select>
            </label>
            <label className="field"><span>Type</span>
              <select value={assessmentType} onChange={(e) => setAssessmentType(e.target.value)}>
                <option value="daily_practice">Daily Practice</option>
                <option value="subject_practice">Subject Practice</option>
                <option value="scheduled">Scheduled</option>
              </select>
            </label>
            <label className="field"><span>Duration (sec)</span><input value={durationSec} onChange={(e) => setDurationSec(e.target.value)} /></label>
            <label className="field"><span>Attempt Limit</span><input value={attemptLimit} onChange={(e) => setAttemptLimit(e.target.value)} /></label>
            <label className="field"><span>Total Marks</span><input value={totalMarks} onChange={(e) => setTotalMarks(e.target.value)} /></label>
            <label className="field"><span>Starts At</span><input type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} /></label>
            <label className="field"><span>Ends At</span><input type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} /></label>
          </div>
          <label className="field"><span>Targets (JSON)</span><textarea rows={3} value={targetsJson} onChange={(e) => setTargetsJson(e.target.value)} /></label>
          <button className="btn" type="submit">Create Assessment</button>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Assessment List</h3>
        <table className="table">
          <thead><tr><th>Title</th><th>Type</th><th>Status</th><th>Duration</th><th>Action</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.title}</td>
                <td>{item.assessment_type}</td>
                <td><span className="badge">{item.status}</span></td>
                <td>{item.duration_sec}</td>
                <td><button className="btn" style={{ background: '#16a34a' }} onClick={() => publishAssessment(item.id)}>Publish</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
