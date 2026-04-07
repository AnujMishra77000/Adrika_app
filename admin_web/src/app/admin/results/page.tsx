'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type ResultItem = {
  id: string;
  assessment: { id: string; title: string };
  student: { id: string; name: string; admission_no: string; roll_no: string; batch_id: string | null };
  score: number;
  total_marks: number;
  rank: number | null;
  published_at: string;
};

export default function AdminResultsPage() {
  const [items, setItems] = useState<ResultItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [assessmentId, setAssessmentId] = useState('');
  const [studentId, setStudentId] = useState('');
  const [score, setScore] = useState('');
  const [totalMarks, setTotalMarks] = useState('');
  const [rank, setRank] = useState('');

  async function load() {
    try {
      const response = await apiRequest<{ items: ResultItem[] }>('/api/v1/admin/results?limit=100&offset=0');
      setItems(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load results');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function publishResult(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest('/api/v1/admin/results/publish', {
        method: 'POST',
        body: JSON.stringify({
          assessment_id: assessmentId,
          student_id: studentId,
          score: Number(score),
          total_marks: Number(totalMarks),
          rank: rank ? Number(rank) : null,
        }),
      });
      setAssessmentId('');
      setStudentId('');
      setScore('');
      setTotalMarks('');
      setRank('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish result');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Results</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Publish / Update Result</h3>
        <form onSubmit={publishResult}>
          <div className="grid">
            <label className="field">
              <span>Assessment ID</span>
              <input value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)} required />
            </label>
            <label className="field">
              <span>Student ID</span>
              <input value={studentId} onChange={(e) => setStudentId(e.target.value)} required />
            </label>
            <label className="field">
              <span>Score</span>
              <input value={score} onChange={(e) => setScore(e.target.value)} required />
            </label>
            <label className="field">
              <span>Total Marks</span>
              <input value={totalMarks} onChange={(e) => setTotalMarks(e.target.value)} required />
            </label>
            <label className="field">
              <span>Rank (optional)</span>
              <input value={rank} onChange={(e) => setRank(e.target.value)} />
            </label>
          </div>
          <button className="btn" type="submit">Publish Result</button>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Result List</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Assessment</th>
              <th>Student</th>
              <th>Score</th>
              <th>Rank</th>
              <th>Published</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.assessment.title}</td>
                <td>{item.student.name}</td>
                <td>{item.score}/{item.total_marks}</td>
                <td>{item.rank ?? '-'}</td>
                <td>{new Date(item.published_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
