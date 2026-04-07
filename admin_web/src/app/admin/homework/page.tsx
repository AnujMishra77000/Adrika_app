'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Homework = { id: string; title: string; subject_id: string; due_date: string; status: string };
type Subject = { id: string; code: string; name: string };

export default function AdminHomeworkPage() {
  const [items, setItems] = useState<Homework[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [targetsJson, setTargetsJson] = useState('[{"target_type":"all","target_id":"all"}]');

  async function load() {
    try {
      const [homeworkRes, subjectRes] = await Promise.all([
        apiRequest<{ items: Homework[] }>('/api/v1/admin/homework?limit=50&offset=0'),
        apiRequest<{ items: Subject[] }>('/api/v1/admin/subjects?limit=200&offset=0'),
      ]);
      setItems(homeworkRes.items);
      setSubjects(subjectRes.items);
      if (!subjectId && subjectRes.items.length > 0) {
        setSubjectId(subjectRes.items[0].id);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load homework');
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createHomework(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const targets = JSON.parse(targetsJson);
      await apiRequest('/api/v1/admin/homework', {
        method: 'POST',
        body: JSON.stringify({
          title,
          description,
          subject_id: subjectId,
          due_date: dueDate,
          targets,
        }),
      });
      setTitle('');
      setDescription('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create homework');
    }
  }

  async function publishHomework(homeworkId: string) {
    try {
      await apiRequest(`/api/v1/admin/homework/${homeworkId}/publish`, { method: 'POST' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish homework');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Homework</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Create Homework</h3>
        <form onSubmit={createHomework}>
          <label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} required /></label>
          <label className="field"><span>Description</span><textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} required /></label>
          <label className="field">
            <span>Subject</span>
            <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} required>
              <option value="">Select</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>{subject.code} - {subject.name}</option>
              ))}
            </select>
          </label>
          <label className="field"><span>Due Date</span><input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required /></label>
          <label className="field"><span>Targets (JSON)</span><textarea rows={3} value={targetsJson} onChange={(e) => setTargetsJson(e.target.value)} /></label>
          <button className="btn" type="submit">Create Homework</button>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Homework List</h3>
        <table className="table">
          <thead><tr><th>Title</th><th>Subject</th><th>Due Date</th><th>Status</th><th>Action</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.title}</td>
                <td>{item.subject_id}</td>
                <td>{item.due_date}</td>
                <td><span className="badge">{item.status}</span></td>
                <td><button className="btn" style={{ background: '#16a34a' }} onClick={() => publishHomework(item.id)}>Publish</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
